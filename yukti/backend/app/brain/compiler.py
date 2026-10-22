"""QuerySpec compiler (B2.3): certified template match -> generated SQL -> dry-run -> async execute.

SQL is generated **deterministically** from the semantic model (no LLM writes SQL on this
path). Every statement is checked by the SQL safety validator and a BigQuery dry-run
before it runs; execution happens in a worker thread so the event loop never blocks.
"""

from __future__ import annotations

import asyncio
import datetime
from dataclasses import dataclass, field
from decimal import Decimal
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from google.cloud import bigquery

from app.brain.query_spec import Filter, Period, QuerySpec
from app.brain.semantic_model import FieldDef, SemanticModel, SubjectDef, TemplateDef, get_semantic_model
from app.config import GCP_PROJECT, JOB_LABELS, MAX_BYTES_BILLED
from app.semantic.entities import get_entities
from app.semantic.normalize import (
    ANCHOR_DATE,
    categorical_values,
    current_fy,
    fiscal_years_for_sql,
    last_complete_fy,
    load_catalog,
)

logger = logging.getLogger("yukti.brain.compiler")

ROW_LIMIT_DEFAULT = 2000
# Work-centre attributes (entities.json) usable as filters on any subject keyed by wc/asset.
WC_ATTRIBUTE_FIELDS = {"sector": "sector", "state": "state", "hard_station_cat": "hard_station_cat",
                       "onshore_offshore": "onshore_offshore", "wc_type": "type", "city": "city"}
_OPS_SQL = {"=": "=", "!=": "!=", ">": ">", ">=": ">=", "<": "<", "<=": "<="}


class CompileError(ValueError):
    """The spec cannot be expressed on the semantic model (caller falls back to the legacy path)."""


@dataclass
class CompiledQuery:
    sql: str
    subject: Optional[str]
    metric: str
    metric_label: str
    unit: str
    source: str                                  # "generated" | "certified:<id>" | "template:<name>"
    tables: List[str]
    dims: List[Tuple[str, str]] = field(default_factory=list)   # (logical field, output column)
    entity_columns: Dict[str, str] = field(default_factory=dict)  # output column -> entity type
    value_columns: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    dropped: List[str] = field(default_factory=list)
    effective_period: Dict[str, Any] = field(default_factory=dict)
    grain: str = "aggregate"
    data_classes: List[str] = field(default_factory=list)
    aggregation: str = "count"          # metric aggregation: only count/sum results may be added up


@dataclass
class QueryResult:
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_bytes: int = 0
    latency_ms: float = 0.0
    dry_run_bytes: int = 0


def _q(table: str) -> str:
    return f"`{GCP_PROJECT}.{table}`"


def _lit(v: Any) -> str:
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return repr(v)
    s = str(v).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{s}'"


def _fy_end(fy: str) -> datetime.date:
    return datetime.date(2000 + int(fy[2:]), 3, 31)


class Compiler:
    def __init__(self, model: Optional[SemanticModel] = None):
        self.model = model or get_semantic_model()
        self.ents = get_entities()
        self._client: Optional[bigquery.Client] = None

    # ------------------------------------------------------------ values
    def _grade_set(self, op: str, value: Any) -> List[str]:
        grades = self.ents.grades
        execs = [g for g in grades if re.fullmatch(r"E\d", g)]
        order = {g: int(grades[g].get("level_order", 0)) for g in execs}
        v = str(value).upper()
        if v not in order:
            raise CompileError(f"unknown grade {value}")
        lv = order[v]
        cmp = {">=": lambda x: x >= lv, ">": lambda x: x > lv, "<=": lambda x: x <= lv, "<": lambda x: x < lv}[op]
        return [g for g in execs if cmp(order[g])]

    def _entity_code(self, etype: str, value: Any) -> str:
        v = str(value).strip()
        table = {"wc": self.ents.work_centres, "discipline": self.ents.disciplines,
                 "field": self.ents.fields, "grade": self.ents.grades}[etype]
        if v in table:
            return v
        if v.upper() in table:
            return v.upper()
        resolver = {"wc": self.ents.resolve_wc, "discipline": self.ents.resolve_discipline,
                    "field": self.ents.resolve_field}.get(etype)
        code = resolver(v) if resolver else None
        if not code and etype == "grade":
            gs = self.ents.resolve_grades(v)
            code = gs[0] if gs else None
        if not code:
            raise CompileError(f"unknown {etype} '{value}'")
        return code

    def _categorical(self, subject: SubjectDef, fd: FieldDef, value: Any) -> str:
        vals = categorical_values([subject.table]).get(fd.column.lower())
        v = str(value)
        if not vals:
            return v
        for cand in vals:
            if cand.lower() == v.lower():
                return cand
        # tolerant match on separators ("non executive" -> "non_executive")
        key = re.sub(r"[\s_-]+", "", v.lower())
        for cand in vals:
            if re.sub(r"[\s_-]+", "", cand.lower()) == key:
                return cand
        raise CompileError(f"value '{value}' not found for {fd.name} (allowed: {sorted(vals)[:12]})")

    def _filter_sql(self, subject: SubjectDef, f: Filter, col_override: Optional[Dict[str, str]] = None) -> str:
        fd = subject.fields.get(f.field)
        if fd is None:
            raise CompileError(f"field {f.field} not in subject {subject.name}")
        col = (col_override or {}).get(f.field, fd.column)
        vals = f.value if isinstance(f.value, list) else [f.value]
        ent = fd.entity
        if ent == "grade" and f.op in (">=", ">", "<=", "<"):
            return f"{col} IN ({', '.join(_lit(g) for g in self._grade_set(f.op, vals[0]))})"
        if ent:
            vals = [self._entity_code(ent, v) for v in vals]
        elif fd.kind == "categorical":
            vals = [self._categorical(subject, fd, v) for v in vals]
        elif fd.kind == "number":
            try:
                vals = [float(v) for v in vals]
            except (TypeError, ValueError):
                raise CompileError(f"numeric value expected for {f.field}: {f.value}")
        elif fd.kind == "bool":
            vals = [str(v).lower() in ("true", "1", "yes", "y") for v in vals]
        if f.op in ("in", "not_in"):
            neg = "NOT " if f.op == "not_in" else ""
            return f"{col} {neg}IN ({', '.join(_lit(v) for v in vals)})"
        if f.op == "between":
            return f"{col} BETWEEN {_lit(vals[0])} AND {_lit(vals[1])}"
        if f.op == "like":
            return f"LOWER({col}) LIKE {_lit('%' + str(vals[0]).lower() + '%')}"
        if fd.kind == "bool" and f.op in ("=", "!="):
            return f"{col} = {_lit(vals[0] if f.op == '=' else not vals[0])}"
        return f"{col} {_OPS_SQL[f.op]} {_lit(vals[0])}"

    def _expand_regions(self, subject: SubjectDef, filters: List[Filter], notes: List[str]) -> List[Filter]:
        out: List[Filter] = []
        wc_field = "wc" if "wc" in subject.fields else ("asset" if "asset" in subject.fields else None)
        for f in filters:
            attr = WC_ATTRIBUTE_FIELDS.get(f.field)
            if attr and f.field not in subject.fields and wc_field:
                # e.g. sector = 'NE' on a table without a sector column -> wc_id IN (NE work centres)
                wanted = {str(v).lower() for v in (f.value if isinstance(f.value, list) else [f.value])}
                codes = [c for c, a in self.ents.work_centres.items() if str(a.get(attr, "")).lower() in wanted]
                if not codes:
                    raise CompileError(f"no work centre has {f.field} in {sorted(wanted)}")
                out.append(Filter(field=wc_field, op="not_in" if f.op in ("!=", "not_in") else "in", value=codes))
                notes.append(f"{f.field} {', '.join(sorted(wanted))} = {len(codes)} work centres")
                continue
            if f.field == "region":
                names = f.value if isinstance(f.value, list) else [f.value]
                codes: List[str] = []
                for n in names:
                    codes += [c for c in self.ents.region_wcs(str(n)) if c not in codes]
                if not codes or not wc_field:
                    raise CompileError(f"region {f.value} not applicable to {subject.name}")
                out.append(Filter(field=wc_field, op="in", value=codes))
                notes.append(f"Region {', '.join(map(str, names))} = {len(codes)} work centres")
            else:
                out.append(f)
        return out

    # ------------------------------------------------------------ compile
    def compile(self, spec: QuerySpec) -> CompiledQuery:
        subject, metric, template = self.model.resolve_metric(spec.metric)
        if template:
            return self._compile_template(template, spec)
        if not subject or not metric:
            raise CompileError(f"unknown metric {spec.metric}")
        notes: List[str] = []
        dropped: List[str] = []

        # Map fields that do not exist on this subject via declared fallbacks (field -> asset ...).
        def map_field(name: str) -> Optional[str]:
            if name in subject.fields or name == "region":
                return name
            if name in WC_ATTRIBUTE_FIELDS and ("wc" in subject.fields or "asset" in subject.fields):
                return name  # expanded to a work-centre list by _expand_regions
            fb = subject.dimension_fallbacks.get(name)
            return fb if fb in subject.fields else None

        filters: List[Filter] = []
        for f in spec.filters:
            mf = map_field(f.field)
            if f.field == "fy":
                continue  # periods are expressed through spec.period
            if mf is None:
                # Answering without a requested filter would answer a different question (G4 B2 F-5).
                raise CompileError(f"filter {f.field} is not available on {subject.name}")
            if mf != f.field:
                notes.append(f"{f.field} shown at {mf} level")
            filters.append(Filter(field=mf, op=f.op, value=f.value))
        filters = self._expand_regions(subject, filters, notes)

        dims: List[str] = []
        for d in spec.dimensions:
            md = map_field(d)
            if md is None or md == "region" or (md in WC_ATTRIBUTE_FIELDS and md not in subject.fields):
                dropped.append(f"dimension {d}")
                continue
            if md != d:
                notes.append(f"{d} shown at {md} level")
            if md not in dims:
                dims.append(md)

        period = spec.period or Period()
        eff_period: Dict[str, Any] = {}
        where: List[str] = [subject.base_filter] if subject.base_filter else []
        table = subject.table
        col_override: Dict[str, str] = {}
        grain = "row" if (spec.grain == "row" or subject.row_only) else "aggregate"

        # ---- period handling
        if subject.period == "fiscal_year":
            available = fiscal_years_for_sql(f"FROM {table}") or []
            if period.fy:
                fy = period.fy
                if available and fy not in available:
                    older = [a for a in available if a <= fy]
                    new_fy = older[-1] if older else available[-1]
                    notes.append(f"{fy} not in data; showing {new_fy}")
                    fy = new_fy
                where.append(f"fiscal_year = {_lit(fy)}")
                eff_period = {"fy": fy}
            elif period.from_ or period.to:
                lo = period.from_ or (available[0] if available else "FY17")
                hi = period.to or last_complete_fy()
                where.append(f"fiscal_year BETWEEN {_lit(lo)} AND {_lit(hi)}")
                eff_period = {"from": lo, "to": hi}
            elif "fy" not in dims:
                fy = subject.default_fy or last_complete_fy()
                if available and fy not in available:
                    fy = available[-1]
                where.append(f"fiscal_year = {_lit(fy)}")
                eff_period = {"fy": fy}
        elif subject.period == "fixed":
            eff_period = {"fy": subject.default_fy or last_complete_fy()}
            if period.fy and period.fy != eff_period["fy"]:
                notes.append(f"{subject.description.split(',')[0]} is available for {eff_period['fy']} only")
        elif subject.period == "snapshot":
            eff_period = {"as_of": ANCHOR_DATE.isoformat()}
            if period.fy and period.fy < current_fy() and grain == "row":
                raise CompileError("past-FY rosters are not available (current snapshot only)")
            if period.fy and period.fy < current_fy() and subject.asof:
                return self._compile_asof(subject, spec, filters, dims, period.fy, notes, dropped)
            if period.fy and period.fy < current_fy():
                notes.append("Workforce data is a current snapshot (19-Oct-2026)")

        for f in filters:
            where.append(self._filter_sql(subject, f, col_override))

        ents_cols: Dict[str, str] = {}
        data_classes = {metric.data_class}
        if grain == "row":
            cols = []
            for rc in subject.row_columns:
                cols.append(f"{rc['expr']} AS {rc['as']}")
                data_classes.add(rc.get("data_class", "general"))
            row_aliases = {rc["as"] for rc in subject.row_columns}
            sort = spec.sort.model_dump() if (spec.sort and spec.sort.by in row_aliases) else (subject.row_sort or None)
            order = f" ORDER BY {sort['by']} {sort.get('dir', 'desc').upper()}" if sort else ""
            limit = min(spec.limit or ROW_LIMIT_DEFAULT, ROW_LIMIT_DEFAULT)  # bounded (G4 B2 F-12)
            cols.append("COUNT(*) OVER () AS _total_rows")  # exact match count even when rows are capped
            sql = (f"SELECT {', '.join(cols)} FROM {_q(table)}"
                   + (f" WHERE {' AND '.join(where)}" if where else "") + order + f" LIMIT {int(limit)}")
            return CompiledQuery(sql=sql, subject=subject.name, metric=metric.name, metric_label=metric.label,
                                 unit=metric.unit, source="generated", tables=[table], notes=notes, dropped=dropped,
                                 effective_period=eff_period, grain="row", value_columns=[],
                                 data_classes=sorted(data_classes), aggregation=metric.aggregation)

        select: List[str] = []
        group: List[str] = []
        dim_out: List[Tuple[str, str]] = []
        for d in dims:
            fd = subject.fields[d]
            alias = fd.label or d
            select.append(f"{fd.column} AS {alias}")
            group.append(fd.column)
            dim_out.append((d, alias))
            if fd.entity:
                ents_cols[alias] = fd.entity
        metrics = [metric.name]
        if subject.companions and metric.name in subject.companions:
            metrics = [metric.name] + [m for m in subject.companions if m != metric.name]
        for mn in metrics:
            select.append(f"{subject.metrics[mn].expr} AS {mn}")
            data_classes.add(subject.metrics[mn].data_class)
        sql = f"SELECT {', '.join(select)} FROM {_q(table)}"
        if where:
            sql += f" WHERE {' AND '.join(where)}"
        if group:
            sql += f" GROUP BY {', '.join(group)}"
            if metric.aggregation in ("ratio", "avg"):
                sql += f" HAVING {metric.name} IS NOT NULL"  # no 'None' rows for units without data
            out_cols = [alias for _, alias in dim_out] + metrics
            if spec.sort and spec.sort.by in out_cols:
                sql += f" ORDER BY {spec.sort.by} {spec.sort.dir.upper()}"
            elif dims and dims[0] == "fy":
                sql += " ORDER BY fiscal_year ASC"
            else:
                sql += f" ORDER BY {metric.name} DESC"
            sql += f" LIMIT {int(min(spec.limit or 1000, 1000))}"
        return CompiledQuery(sql=sql, subject=subject.name, metric=metric.name, metric_label=metric.label,
                             unit=metric.unit, source="generated", tables=[table], dims=dim_out,
                             entity_columns=ents_cols, value_columns=metrics, notes=notes, dropped=dropped,
                             effective_period=eff_period, grain="aggregate", data_classes=sorted(data_classes),
                             aggregation=metric.aggregation)

    def _compile_asof(self, subject: SubjectDef, spec: QuerySpec, filters: List[Filter], dims: List[str],
                      fy: str, notes: List[str], dropped: List[str]) -> CompiledQuery:
        """Station-tenure headcount as of 31-Mar of a past FY (continuous stays from v_continuous_stay)."""
        a = subject.asof or {}
        asof = _fy_end(fy)
        tenure = next((f for f in filters if f.field == "station_tenure_years" and f.op in (">=", ">")), None)
        if spec.metric != "headcount" or tenure is None:
            raise CompileError("past-FY workforce questions are supported for station-tenure headcount only")
        months = int(round(float(tenure.value if not isinstance(tenure.value, list) else tenure.value[0]) * 12))
        where = [a.get("base_filter") or "TRUE",
                 f"{a['tenure_from_column']} <= DATE_SUB(DATE '{asof.isoformat()}', INTERVAL {months} MONTH)",
                 f"({a['tenure_to_column']} IS NULL OR {a['tenure_to_column']} >= DATE '{asof.isoformat()}')"]
        colmap: Dict[str, str] = a.get("fields") or {}
        for f in filters:
            if f.field == "station_tenure_years":
                continue
            if f.field == "cadre":
                if str(f.value).lower() == "executive" and f.op in ("=", "in"):
                    continue  # the as-of view holds executive stays only
                raise CompileError("past-FY station tenure is available for executives only")
            if f.field not in colmap:
                raise CompileError(f"filter {f.field} is not available as of {fy}")
            where.append(self._filter_sql(subject, f, col_override=colmap))
        select, group, dim_out, ents_cols = [], [], [], {}
        for d in dims:
            if d not in colmap:
                dropped.append(f"dimension {d} (not available as of {fy})")
                continue
            fd = subject.fields[d]
            alias = fd.label or d
            select.append(f"{colmap[d]} AS {alias}")
            group.append(colmap[d])
            dim_out.append((d, alias))
            if fd.entity:
                ents_cols[alias] = fd.entity
        select.append(f"{a.get('count_expr', 'COUNT(*)')} AS headcount")
        sql = f"SELECT {', '.join(select)} FROM {_q(a['table'])} WHERE {' AND '.join(where)}"
        if group:
            sql += f" GROUP BY {', '.join(group)} ORDER BY headcount DESC"
        notes.append(f"As of 31-Mar-{asof.year} (end of {fy}), from continuous-stay history")
        m = subject.metrics["headcount"]
        return CompiledQuery(sql=sql, subject=subject.name, metric="headcount", metric_label=m.label, unit=m.unit,
                             source="generated:asof", tables=[a["table"]], dims=dim_out, entity_columns=ents_cols,
                             value_columns=["headcount"], notes=notes, dropped=dropped,
                             effective_period={"fy": fy, "as_of": asof.isoformat()}, grain="aggregate",
                             data_classes=["general"])

    def _compile_template(self, t: TemplateDef, spec: QuerySpec) -> CompiledQuery:
        if t.name == "headcount_change":
            return self._compile_headcount_change(t, spec)
        if t.name != "capex_vs_reserves":
            raise CompileError(f"template {t.name} has no compiler")
        p = spec.period or Period()
        lo = p.from_ or (p.fy if p.fy else t.default_from)
        hi = p.to or (p.fy if p.fy else t.default_to)
        if hi and hi > last_complete_fy():
            hi = last_complete_fy()
        res_years = [v for v in fiscal_years_for_sql("FROM hrfin_silver.reserves_annual")] or [last_complete_fy()]
        res_fy = max(v for v in res_years if v <= hi) if any(v <= hi for v in res_years) else res_years[-1]
        asset_filter = ""
        f = spec.filter_on("asset") or spec.filter_on("wc")
        if f:
            codes = [self._entity_code("wc", v) for v in (f.value if isinstance(f.value, list) else [f.value])]
            asset_filter = f" AND asset_wc_id IN ({', '.join(_lit(c) for c in codes)})"
        sql = f"""WITH capex AS (
  SELECT asset_wc_id, SUM(actual_spend_inr_cr) AS capex_cr
  FROM {_q('hrfin_silver.capex_budget')}
  WHERE fiscal_year BETWEEN {_lit(lo)} AND {_lit(hi)}{asset_filter}
  GROUP BY asset_wc_id),
res AS (
  SELECT asset_wc_id, SUM(reserves_2p_total_mmtoe) AS reserves_2p_mmtoe
  FROM {_q('hrfin_silver.reserves_annual')}
  WHERE fiscal_year = {_lit(res_fy)}
  GROUP BY asset_wc_id),
j AS (SELECT c.asset_wc_id, c.capex_cr, r.reserves_2p_mmtoe FROM capex c LEFT JOIN res r USING (asset_wc_id)),
a AS (SELECT SUM(capex_cr) / NULLIF(SUM(reserves_2p_mmtoe), 0) AS avg_cr_per_mmtoe FROM j WHERE reserves_2p_mmtoe > 0)
SELECT j.asset_wc_id AS asset,
  ROUND(j.capex_cr, 0) AS capex_cr,
  ROUND(j.capex_cr * 100.0 / SUM(j.capex_cr) OVER (), 1) AS pct_of_capex,
  ROUND(j.reserves_2p_mmtoe, 1) AS reserves_2p_mmtoe,
  ROUND(j.capex_cr / NULLIF(j.reserves_2p_mmtoe, 0), 1) AS capex_cr_per_mmtoe,
  ROUND(a.avg_cr_per_mmtoe, 1) AS avg_capex_cr_per_mmtoe,
  (j.reserves_2p_mmtoe > 0 AND j.capex_cr / j.reserves_2p_mmtoe < 0.5 * a.avg_cr_per_mmtoe) AS under_invested
FROM j CROSS JOIN a
ORDER BY j.capex_cr DESC"""
        return CompiledQuery(sql=sql, subject=None, metric=t.name, metric_label=t.label, unit="inr_cr",
                             source=f"template:{t.name}" + (f" (mirrors certified {t.certified_id})" if t.certified_id else ""),
                             tables=["hrfin_silver.capex_budget", "hrfin_silver.reserves_annual"],
                             dims=[("asset", "asset")], entity_columns={"asset": "wc"},
                             value_columns=["capex_cr", "reserves_2p_mmtoe", "capex_cr_per_mmtoe"],
                             notes=[f"Capex {lo}–{hi} vs {res_fy} 2P reserves; capex is recorded by asset, not field"],
                             effective_period={"from": lo, "to": hi}, grain="aggregate", data_classes=["general"])

    def _compile_headcount_change(self, t: TemplateDef, spec: QuerySpec) -> CompiledQuery:
        p = spec.period or Period()
        lo = p.from_ or t.default_from
        hi = p.to or (p.fy if p.fy else t.default_to)
        if hi > last_complete_fy():
            hi = last_complete_fy()
        m0 = f"{2000 + int(lo[2:]) - 1}-03"   # 31-Mar before the start FY
        m1 = f"{2000 + int(hi[2:])}-03"       # 31-Mar at the end FY
        where = [f"month IN ({_lit(m0)}, {_lit(m1)})"]
        f = spec.filter_on("wc")
        if f:
            codes = [self._entity_code("wc", v) for v in (f.value if isinstance(f.value, list) else [f.value])]
            where.append(f"wc_id IN ({', '.join(_lit(c) for c in codes)})")
        sql = f"""WITH hc AS (
  SELECT wc_id, SUM(CASE WHEN month = {_lit(m0)} THEN headcount END) AS hc_start,
         SUM(CASE WHEN month = {_lit(m1)} THEN headcount END) AS hc_end
  FROM {_q('hrfin_silver.headcount_snapshot')} WHERE {' AND '.join(where)} GROUP BY wc_id)
SELECT wc_id AS work_centre, hc_start, hc_end, hc_end - hc_start AS headcount_change,
  ROUND(100 * (hc_end - hc_start) / NULLIF(hc_start, 0), 1) AS change_pct
FROM hc ORDER BY headcount_change DESC"""
        return CompiledQuery(sql=sql, subject=None, metric=t.name, metric_label=t.label, unit="employees",
                             source=f"template:{t.name}", tables=["hrfin_silver.headcount_snapshot"],
                             dims=[("wc", "work_centre")], entity_columns={"work_centre": "wc"},
                             value_columns=["headcount_change", "change_pct", "hc_start", "hc_end"],
                             notes=[f"Headcount 31-Mar-{m0[:4]} vs 31-Mar-{m1[:4]} (monthly snapshots)"],
                             effective_period={"from": lo, "to": hi}, grain="aggregate", data_classes=["general"])

    # ------------------------------------------------------------ execute
    @property
    def client(self) -> bigquery.Client:
        if self._client is None:
            from app.config import BQ_LOCATION
            self._client = bigquery.Client(project=GCP_PROJECT, location=BQ_LOCATION)
        return self._client

    def _validate(self, sql: str) -> None:
        from app.tools.semantic_layer import SemanticLayer
        ok, err = SemanticLayer().validate_sql_safety(sql)
        if not ok:
            raise CompileError(f"unsafe SQL rejected: {err}")

    def dry_run(self, sql: str) -> int:
        self._validate(sql)
        cfg = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False, labels=JOB_LABELS)
        job = self.client.query(sql, job_config=cfg)
        b = job.total_bytes_processed or 0
        if b > MAX_BYTES_BILLED:
            raise CompileError(f"query would scan {b} bytes (cap {MAX_BYTES_BILLED})")
        return b

    def _run_sync(self, sql: str) -> QueryResult:
        t0 = time.perf_counter()
        dry = self.dry_run(sql)
        cfg = bigquery.QueryJobConfig(labels=JOB_LABELS, maximum_bytes_billed=MAX_BYTES_BILLED)
        job = self.client.query(sql, job_config=cfg)
        res = job.result()
        cols = [f.name for f in res.schema] if res.schema else []
        rows: List[Dict[str, Any]] = []
        for r in res:
            d = {}
            for k, v in dict(r).items():
                if isinstance(v, Decimal):
                    v = float(v)
                elif hasattr(v, "isoformat"):
                    v = v.isoformat()
                d[k] = v
            rows.append(d)
        return QueryResult(columns=cols, rows=rows, total_bytes=job.total_bytes_processed or 0,
                           latency_ms=round((time.perf_counter() - t0) * 1000, 1), dry_run_bytes=dry)

    async def execute(self, compiled: CompiledQuery) -> QueryResult:
        """Dry-run + execute off the event loop (asyncio.to_thread)."""
        return await asyncio.to_thread(self._run_sync, compiled.sql)


_COMPILER: Optional[Compiler] = None


def get_compiler() -> Compiler:
    global _COMPILER
    if _COMPILER is None:
        _COMPILER = Compiler()
    return _COMPILER
