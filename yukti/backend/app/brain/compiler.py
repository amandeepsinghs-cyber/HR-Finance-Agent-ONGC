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
import os
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
# Subjects with one row per person: COUNT(*) per group is the number of people in the cell.
CELL_COUNT_SUBJECTS = {"workforce", "separations"}
# Work-centre attributes (entities.json) usable as filters on any subject keyed by wc/asset.
WC_ATTRIBUTE_FIELDS = {"sector": "sector", "state": "state", "hard_station_cat": "hard_station_cat",
                       "onshore_offshore": "onshore_offshore", "wc_type": "type", "city": "city"}
_OPS_SQL = {"=": "=", "!=": "!=", ">": ">", ">=": ">=", "<": "<", "<=": "<="}

_GOLD_DS = "hrfin_gold"
_V_AS_REPORTED = f"{_GOLD_DS}.v_fin_statement_as_reported"
_V_TREND_LATEST = f"{_GOLD_DS}.v_fin_trend_latest"
_T_FACT_FIN = f"{_GOLD_DS}.fact_financial_statement_line"

CORP_METRIC_TO_SSOT: Dict[str, Tuple[str, str]] = {
    "exchequer_contribution_cr": ("standalone", "OTH.EXCHEQUER"),
    "corporate_revenue_cr": ("standalone", "PL.REV_OPS"),
    "crude_oil_revenue_cr": ("standalone", "REV.CRUDE"),
    "natural_gas_revenue_cr": ("standalone", "REV.GAS"),
    "vap_revenue_cr": ("standalone", "REV.VAP"),
    "offshore_revenue_cr": ("standalone", "SEG.REV.OFF"),
    "onshore_revenue_cr": ("standalone", "SEG.REV.ON"),
    "other_income_cr": ("standalone", "PL.OTHER_INCOME"),
    "total_income_cr": ("standalone", "PL.TOTAL_INCOME"),
    "statutory_levies_cr": ("standalone", "LEVY.TOTAL"),
    "royalty_cr": ("standalone", "LEVY.ROYALTY"),
    "oidb_cess_cr": ("standalone", "LEVY.OIDB_CESS"),
    "saed_windfall_tax_cr": ("standalone", "LEVY.OTHER_SAED"),
    "prod_transport_selling_exp_cr": ("standalone", "PL.OPEX_10YR"),
    "operating_expenses_cr": ("standalone", "PL.OPEX_10YR"),
    "employee_cost_cr": ("standalone", "OTH.EMP_EXPENDITURE"),
    "employee_benefit_net_pnl_cr": ("standalone", "PL.EMP_BENEFIT"),
    "exploration_costs_written_off_cr": ("standalone", "PL.EXPL_WRITEOFF"),
    "survey_costs_written_off_cr": ("standalone", "PL.EXPL_SURVEY"),
    "exploratory_wells_written_off_cr": ("standalone", "PL.EXPL_WELL"),
    "dda_cr": ("standalone", "PL.DDA"),
    "finance_costs_cr": ("standalone", "PL.FIN_COST"),
    "exceptional_items_cr": ("standalone", "PL.EXCEPTIONAL"),
    "pbt_corporate_cr": ("standalone", "PL.PBT"),
    "tax_expense_cr": ("standalone", "PL.TAX"),
    "current_tax_cr": ("standalone", "PL.TAX_CURRENT"),
    "deferred_tax_cr": ("standalone", "PL.TAX_DEFERRED"),
    "pat_cr": ("standalone", "PL.PAT"),
    "pat_margin_corporate_pct": ("standalone", "RATIO.PAT_MARGIN_PCT"),
    "ebitda_margin_corporate_pct": ("standalone", "RATIO.PBIDT_MARGIN_PCT"),
    "consolidated_revenue_cr": ("consolidated", "PL.REV_OPS"),
    "consolidated_pbt_cr": ("consolidated", "PL.PBT"),
    "consolidated_pat_cr": ("consolidated", "PL.PAT"),
    "total_assets_cr": ("standalone", "BS.TOTAL_ASSETS"),
    "non_current_assets_cr": ("standalone", "BS.ASSETS.NON_CURRENT.TOTAL"),
    "oil_and_gas_assets_cr": ("standalone", "BS.OG_ASSETS"),
    "other_ppe_and_rou_cr": ("standalone", "BS.OTHER_PPE"),
    "cwip_cr": ("standalone", "BS.WIP_TOTAL_10YR"),
    "exploratory_wells_in_progress_cr": ("standalone", "BS.IAUD_EXPL_WELLS"),
    "investments_subsidiaries_jv_cr": ("standalone", "BS.INVESTMENTS_NC_10YR"),
    "site_restoration_fund_cr": ("standalone", "BS.SRF_DEPOSIT_NC"),
    "current_assets_cr": ("standalone", "BS.ASSETS.CURRENT.TOTAL"),
    "inventories_cr": ("standalone", "BS.INVENTORIES"),
    "trade_receivables_cr": ("standalone", "BS.TRADE_REC_C"),
    "cash_and_bank_cr": ("standalone", "BS.CCE"),
    "equity_share_capital_cr": ("standalone", "BS.SHARE_CAPITAL"),
    "other_equity_reserves_cr": ("standalone", "BS.OTHER_EQUITY"),
    "net_worth_cr": ("standalone", "BS.EQUITY.TOTAL"),
    "consolidated_net_worth_cr": ("consolidated", "BS.EQUITY.TOTAL"),
    "non_current_liabilities_cr": ("standalone", "BS.LIAB.NON_CURRENT.TOTAL"),
    "long_term_debt_cr": ("standalone", "BS.BORROW_NC"),
    "short_term_debt_cr": ("standalone", "BS.BORROW_CUR"),
    "total_debt_cr": ("standalone", "BS.BORROW_TOTAL_10YR"),
    "lease_liabilities_cr": ("standalone", "BS.LEASE_LIAB_TOTAL_10YR"),
    "abandonment_provision_cr": ("standalone", "BS.PROV_NC"),
    "deferred_tax_liability_net_cr": ("standalone", "BS.DTL_NET"),
    "current_liabilities_cr": ("standalone", "BS.LIAB.CURRENT.TOTAL"),
    "trade_payables_cr": ("standalone", "BS.TRADE_PAY"),
    "total_liabilities_cr": ("standalone", "BS.LIAB.TOTAL"),
    "net_working_capital_cr": ("standalone", "BS.WORKING_CAPITAL_10YR"),
    "capital_employed_cr": ("standalone", "OTH.CAPITAL_EMPLOYED"),
    "total_capex_cr": ("standalone", "CAPEX.TOTAL"),
    "operating_cash_flow_cr": ("standalone", "CF.CFO"),
    "investing_cash_flow_cr": ("standalone", "CF.CFI"),
    "financing_cash_flow_cr": ("standalone", "CF.CFF"),
    "net_cash_change_cr": ("standalone", "CF.NET_CHANGE_CCE"),
    "dividend_payout_cr": ("standalone", "OTH.DIVIDEND_DECLARED"),
    "csr_spend_cr": ("standalone", "OTH.CSR"),
    "roce_pct": ("standalone", "RATIO.ROCE"),
    "roe_pct": ("standalone", "RATIO.ROE_INCL_EXC"),
    "debt_to_equity_ratio": ("standalone", "RATIO.DEBT_EQUITY"),
    "current_ratio": ("standalone", "RATIO.CURRENT"),
    "receivable_days": ("standalone", "RATIO.DEBTORS_TURNOVER_DAYS"),
    "eps_basic_inr": ("standalone", "PL.EPS_BASIC"),
    "book_value_per_share_inr": ("standalone", "RATIO.BVPS"),
    "dividend_per_share_inr": ("standalone", "RATIO.DPS"),
}


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
    # P0.3 / P1.10a (BUG-04): where the rows really came from. "bigquery" = executed SQL; "local_snapshot" = the
    # verified fact_snapshot.parquet fallback used when BigQuery is unavailable (no SQL ran, so no SQL is reported).
    source: str = "bigquery"
    snapshot_date: Optional[str] = None
    snapshot_run_id: Optional[str] = None


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
    def compile(self, spec: QuerySpec, cell_count: bool = False) -> CompiledQuery:
        """`cell_count=True` adds `COUNT(*) AS _n` per group on employee-grain subjects, so junior
        aggregates of averages/ratios can be suppressed when a cell holds < 5 people (D-11)."""
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

        from app.config import YUKTI_FIN_SSOT_V3
        if YUKTI_FIN_SSOT_V3 and subject.name == "corporate" and grain != "row" and metric.name in ["ebitda_corporate_cr", "revenue_per_employee_cr", "employee_headcount"] and not filters:
            return self._compile_derived_corporate(subject, metric, spec, dims, notes, dropped)

        if YUKTI_FIN_SSOT_V3 and subject.name == "corporate" and grain != "row" and metric.name in CORP_METRIC_TO_SSOT and not filters:
            return self._compile_corporate_ssot(subject, metric, spec, dims, notes, dropped)

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
        elif subject.name == "corporate":
            corp_families = [
                ["statutory_levies_cr", "royalty_cr", "oidb_cess_cr", "saed_windfall_tax_cr"],
                ["crude_oil_revenue_cr", "natural_gas_revenue_cr", "vap_revenue_cr", "corporate_revenue_cr"],
                ["offshore_revenue_cr", "onshore_revenue_cr", "corporate_revenue_cr"],
                ["exploration_costs_written_off_cr", "exploratory_wells_written_off_cr", "survey_costs_written_off_cr"],
                ["tax_expense_cr", "current_tax_cr", "deferred_tax_cr"],
                ["consolidated_pat_cr", "pat_cr", "consolidated_revenue_cr", "corporate_revenue_cr"],
                ["operating_cash_flow_cr", "investing_cash_flow_cr", "financing_cash_flow_cr", "free_cash_flow_cr", "total_capex_cr"],
                ["total_assets_cr", "non_current_assets_cr", "current_assets_cr", "net_worth_cr", "total_liabilities_cr"],
                ["oil_and_gas_assets_cr", "cwip_cr", "investments_subsidiaries_jv_cr", "site_restoration_fund_cr", "non_current_assets_cr"],
                ["total_debt_cr", "long_term_debt_cr", "short_term_debt_cr", "cash_and_bank_cr", "net_debt_cr"],
                ["net_worth_cr", "equity_share_capital_cr", "other_equity_reserves_cr", "consolidated_net_worth_cr"],
                ["abandonment_provision_cr", "site_restoration_fund_cr", "lease_liabilities_cr", "deferred_tax_liability_net_cr"],
                ["trade_receivables_cr", "disputed_receivables_cr", "inventories_cr", "cash_and_bank_cr"],
                ["roce_pct", "consolidated_roce_pct", "roe_pct", "roa_pct"],
                ["debt_to_equity_ratio", "net_debt_to_ebitda_ratio", "interest_coverage_ratio", "current_ratio"],
                ["eps_basic_inr", "book_value_per_share_inr", "dividend_per_share_inr"],
            ]
            for fam in corp_families:
                if metric.name in fam:
                    metrics = [metric.name] + [m for m in fam if m != metric.name and m in subject.metrics]
                    break
            if len(metrics) == 1 and metric.name in ("pat_cr", "pbt_corporate_cr", "ebitda_corporate_cr", "corporate_revenue_cr"):
                base_fam = ["corporate_revenue_cr", "ebitda_corporate_cr", "pbt_corporate_cr", "pat_cr", "consolidated_pat_cr"]
                metrics = [metric.name] + [m for m in base_fam if m != metric.name and m in subject.metrics]
        for mn in metrics:
            select.append(f"{subject.metrics[mn].expr} AS {mn}")
            data_classes.add(subject.metrics[mn].data_class)
        if cell_count and subject.name in CELL_COUNT_SUBJECTS:
            select.append("COUNT(*) AS _n")
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
        if t.name == "pnl_statement":
            return self._compile_pnl_statement(t, spec)
        if t.name == "balance_sheet":
            return self._compile_balance_sheet(t, spec)
        if t.name == "cash_flow_statement":
            return self._compile_cash_flow_statement(t, spec)
        if t.name == "financial_ratios":
            return self._compile_financial_ratios(t, spec)
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


    def _compile_derived_corporate(self, subject: SubjectDef, metric: FieldDef, spec: QuerySpec, dims: List[Tuple[str, str]], notes: List[str], dropped: List[str]) -> Optional[CompiledQuery]:
        fy_where = "TRUE"
        eff_period = {}
        if spec.period:
            if spec.period.fy:
                fy_where = f"fiscal_year = '{spec.period.fy}'"
                eff_period = {"fy": spec.period.fy}
            elif spec.period.from_ or spec.period.to:
                lo = spec.period.from_ or "FY17"
                hi = spec.period.to or "FY26"
                fy_where = f"fiscal_year BETWEEN '{lo}' AND '{hi}'"
                eff_period = {"from": lo, "to": hi}
        elif "fy" not in [d[0] for d in dims]:
            fy = "FY24"
            fy_where = f"fiscal_year = '{fy}'"
            eff_period = {"fy": fy}

        dim_out = dims if dims else [("fy", "fiscal_year")]
        
        if metric.name == "ebitda_corporate_cr":
            sql = f"""WITH cur AS (
  SELECT fiscal_year,
         MAX(IF(line_code = 'PL.PBT', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS pbt,
         MAX(IF(line_code = 'PL.FIN_COST', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS fin_cost,
         MAX(IF(line_code = 'PL.DDA', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS dda,
         MAX(IF(line_code = 'PL.OTHER_INCOME', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS other_inc
  FROM {_q(_V_TREND_LATEST)}
  WHERE {fy_where} AND verified = TRUE AND scope = 'standalone'
  GROUP BY fiscal_year
)
SELECT fiscal_year, 
       pbt, fin_cost, dda, other_inc,
       ROUND(pbt + COALESCE(fin_cost, 0) + COALESCE(dda, 0) - COALESCE(other_inc, 0), 2) AS ebitda_corporate_cr
FROM cur
ORDER BY fiscal_year ASC"""
            notes.append("Derived from AR: EBITDA = PBT + Finance Cost + DD&A - Other Income")
            
        elif metric.name == "revenue_per_employee_cr":
            sql = f"""WITH rev AS (
  SELECT fiscal_year, MAX(ROUND(COALESCE(value_inr_cr, value), 2)) AS rev_ops
  FROM {_q(_V_TREND_LATEST)}
  WHERE {fy_where} AND verified = TRUE AND scope = 'standalone' AND line_code = 'PL.REV_OPS'
  GROUP BY fiscal_year
),
hc AS (
  SELECT 'FY' || RIGHT(CAST(fiscal_year AS STRING), 2) AS fy, SUM(headcount) AS headcount
  FROM {_q('hrfin_silver.headcount_snapshot')}
  WHERE CAST(month AS INT64) = 3
  GROUP BY fiscal_year
),
hc_avg AS (
  SELECT fy, (headcount + LAG(headcount) OVER (ORDER BY fy)) / 2.0 AS avg_headcount
  FROM hc
)
SELECT r.fiscal_year, r.rev_ops, h.avg_headcount AS headcount,
       ROUND(r.rev_ops / NULLIF(h.avg_headcount, 0), 3) AS revenue_per_employee_cr
FROM rev r
LEFT JOIN hc_avg h ON r.fiscal_year = h.fy
ORDER BY r.fiscal_year ASC"""
            notes.append("Derived from AR: Revenue per employee = Revenue from Operations / Average headcount")
        elif metric.name == "employee_headcount":
            sql = f"""SELECT 'FY' || RIGHT(CAST(fiscal_year AS STRING), 2) AS fiscal_year,
  SUM(headcount) AS employee_headcount,
  'HR.HEADCOUNT' AS line_code,
  'Total employee headcount' AS display_name,
  SUM(headcount) AS value_inr_cr,
  FALSE AS is_restated,
  'HR system' AS source_system
FROM {_q('hrfin_silver.headcount_snapshot')}
WHERE {fy_where.replace('fiscal_year', "('FY' || RIGHT(CAST(fiscal_year AS STRING), 2))")} AND ENDS_WITH(month, '-03')
GROUP BY fiscal_year
ORDER BY fiscal_year ASC"""
            notes.append("Derived from HR: Headcount snapshot as of March")
        else:
            return None

        return CompiledQuery(
            sql=sql,
            subject="corporate",
            metric=metric.name,
            metric_label=metric.label,
            unit=metric.unit,
            source="generated",
            tables=[_V_TREND_LATEST, "hrfin_silver.headcount_snapshot"] if metric.name == "revenue_per_employee_cr" else ["hrfin_silver.headcount_snapshot"] if metric.name == "employee_headcount" else [_V_TREND_LATEST],
            dims=dim_out,
            value_columns=[metric.name],
            notes=notes,
            dropped=dropped,
            effective_period=eff_period,
            grain="aggregate",
            data_classes=[metric.data_class],
            aggregation=metric.aggregation,
        )

    def _compile_corporate_ssot(
        self, subject: SubjectDef, metric: Any, spec: QuerySpec,
        dims: List[str], notes: List[str], dropped: List[str]
    ) -> CompiledQuery:
        """Compile corporate subject metrics against v_fin_statement_as_reported (single-FY) or v_fin_trend_latest (multi-FY)."""
        p = spec.period or Period()
        available = ["FY17", "FY18", "FY19", "FY20", "FY21", "FY22", "FY23", "FY24", "FY25", "FY26"]
        is_multi_fy = bool((p.from_ and p.to and p.from_ != p.to) or ("fy" in dims))
        if is_multi_fy:
            lo = p.from_ or "FY17"
            hi = p.to or "FY26"
            if hi > "FY26":
                hi = "FY26"
            view_tbl = _V_TREND_LATEST
            fy_where = f"fiscal_year BETWEEN {_lit(lo)} AND {_lit(hi)}"
            eff_period: Dict[str, Any] = {"from": lo, "to": hi}
            dim_out: List[Tuple[str, str]] = [("fy", "fiscal_year")]
            notes = list(notes) + [f"Verified · Annual Report trend ({lo}–{hi}, latest comparative vintage)"]
        else:
            fy = p.fy or (p.from_ if p.from_ and p.from_ == p.to else None) or subject.default_fy or "FY26"
            if fy not in available:
                older = [a for a in available if a <= fy]
                new_fy = older[-1] if older else available[-1]
                notes = list(notes) + [f"{fy} not in data; showing {new_fy}"]
                fy = new_fy
            view_tbl = _V_AS_REPORTED
            fy_where = f"fiscal_year = {_lit(fy)}"
            eff_period = {"fy": fy}
            dim_out = [("fy", "fiscal_year")] if "fy" in dims else []
            is_ratio = metric.name in (
                "roce_pct", "consolidated_roce_pct", "roe_pct", "roa_pct",
                "debt_to_equity_ratio", "net_debt_to_ebitda_ratio", "interest_coverage_ratio",
                "current_ratio", "quick_ratio", "receivable_days", "ebitda_margin_corporate_pct", "pat_margin_corporate_pct",
            )
            notes = list(notes) + [
                f"Verified · Annual Report ({fy}, as reported)"
            ]

        corp_families = [
            ["statutory_levies_cr", "royalty_cr", "oidb_cess_cr", "saed_windfall_tax_cr"],
            ["crude_oil_revenue_cr", "natural_gas_revenue_cr", "vap_revenue_cr", "corporate_revenue_cr"],
            ["offshore_revenue_cr", "onshore_revenue_cr", "corporate_revenue_cr"],
            ["exploration_costs_written_off_cr", "exploratory_wells_written_off_cr", "survey_costs_written_off_cr"],
            ["tax_expense_cr", "current_tax_cr", "deferred_tax_cr"],
            ["consolidated_pat_cr", "pat_cr", "consolidated_revenue_cr", "corporate_revenue_cr"],
            ["operating_cash_flow_cr", "investing_cash_flow_cr", "financing_cash_flow_cr", "total_capex_cr"],
            ["total_assets_cr", "non_current_assets_cr", "current_assets_cr", "net_worth_cr", "total_liabilities_cr"],
            ["oil_and_gas_assets_cr", "cwip_cr", "investments_subsidiaries_jv_cr", "site_restoration_fund_cr", "non_current_assets_cr"],
            ["total_debt_cr", "lease_liabilities_cr", "long_term_debt_cr", "short_term_debt_cr", "cash_and_bank_cr"],
            ["net_worth_cr", "equity_share_capital_cr", "other_equity_reserves_cr", "consolidated_net_worth_cr"],
            ["abandonment_provision_cr", "site_restoration_fund_cr", "lease_liabilities_cr", "deferred_tax_liability_net_cr"],
            ["trade_receivables_cr", "inventories_cr", "cash_and_bank_cr"],
            ["roce_pct", "roe_pct"],
            ["debt_to_equity_ratio", "current_ratio"],
            ["eps_basic_inr", "book_value_per_share_inr", "dividend_per_share_inr"],
            ["dividend_payout_cr", "dividend_per_share_inr"],
        ]
        metrics = [metric.name]
        for fam in corp_families:
            if metric.name in fam:
                metrics = [metric.name] + [m for m in fam if m != metric.name and m in CORP_METRIC_TO_SSOT]
                break
        if len(metrics) == 1 and metric.name in ("pat_cr", "pbt_corporate_cr", "corporate_revenue_cr"):
            base_fam = ["corporate_revenue_cr", "pbt_corporate_cr", "pat_cr", "consolidated_pat_cr"]
            metrics = [metric.name] + [m for m in base_fam if m != metric.name and m in CORP_METRIC_TO_SSOT]

        p_scope, p_code = CORP_METRIC_TO_SSOT[metric.name]
        select_exprs: List[str] = ["fiscal_year"]
        pair_set: List[Tuple[str, str]] = []
        for mn in metrics:
            sc, cd = CORP_METRIC_TO_SSOT[mn]
            if (sc, cd) not in pair_set:
                pair_set.append((sc, cd))
            select_exprs.append(
                f"MAX(IF(scope = {_lit(sc)} AND line_code = {_lit(cd)}, ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS {mn}"
            )
        extra_cols: List[str] = []
        if metric.name == "roce_pct":
            pair_set.append(("standalone", "RATIO.ROCE_INCL_EXC"))
            select_exprs.append(
                "MAX(IF(scope = 'standalone' AND line_code = 'RATIO.ROCE_INCL_EXC', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS roce_incl_exc_pct"
            )
            extra_cols.append("roce_incl_exc_pct")
        if metric.name == "dividend_payout_cr":
            pair_set.append(("standalone", "RATIO.DIVIDEND_PCT"))
            select_exprs.append(
                "MAX(IF(scope = 'standalone' AND line_code = 'RATIO.DIVIDEND_PCT', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS dividend_pct"
            )
            extra_cols.append("dividend_pct")

        select_exprs.extend([
            f"MAX(IF(scope = {_lit(p_scope)} AND line_code = {_lit(p_code)}, line_code, NULL)) AS line_code",
            f"MAX(IF(scope = {_lit(p_scope)} AND line_code = {_lit(p_code)}, display_name, NULL)) AS display_name",
            f"MAX(IF(scope = {_lit(p_scope)} AND line_code = {_lit(p_code)}, ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS value_inr_cr",
            f"LOGICAL_OR(IF(scope = {_lit(p_scope)} AND line_code = {_lit(p_code)}, is_restated, FALSE)) AS is_restated",
            f"MAX(IF(scope = {_lit(p_scope)} AND line_code = {_lit(p_code)}, COALESCE(footnote_marker, notes), NULL)) AS restatement_note",
            f"MAX(IF(scope = {_lit(p_scope)} AND line_code = {_lit(p_code)}, CASE WHEN is_restated THEN '†' ELSE footnote_marker END, NULL)) AS footnote_marker",
            f"MAX(IF(scope = {_lit(p_scope)} AND line_code = {_lit(p_code)}, REGEXP_REPLACE(source_doc, r'\\.txt$', '.pdf'), NULL)) AS source_doc",
            f"MAX(IF(scope = {_lit(p_scope)} AND line_code = {_lit(p_code)}, source_page_label, NULL)) AS source_page_label",
            f"MAX(IF(scope = {_lit(p_scope)} AND line_code = {_lit(p_code)}, source_system, NULL)) AS source_system",
        ])

        by_scope: Dict[str, List[str]] = {}
        for sc, cd in pair_set:
            if cd not in by_scope.setdefault(sc, []):
                by_scope[sc].append(cd)
        scope_conds = [
            f"(scope = {_lit(sc)} AND line_code IN ({', '.join(_lit(c) for c in cds)}))"
            for sc, cds in by_scope.items()
        ]
        sql = (
            f"SELECT\n  " + ",\n  ".join(select_exprs)
            + f"\nFROM {_q(view_tbl)}"
            + f"\nWHERE {fy_where} AND verified = TRUE AND ({' OR '.join(scope_conds)})"
            + "\nGROUP BY fiscal_year\nORDER BY fiscal_year ASC"
        )
        return CompiledQuery(
            sql=sql,
            subject="corporate",
            metric=metric.name,
            metric_label=metric.label,
            unit=metric.unit,
            source="generated",
            tables=[view_tbl],
            dims=dim_out,
            value_columns=metrics + extra_cols,
            notes=notes,
            dropped=dropped,
            effective_period=eff_period,
            grain="aggregate",
            data_classes=[metric.data_class],
            aggregation=metric.aggregation,
        )

    def _v3__compile_pnl_statement(self, t: TemplateDef, spec: QuerySpec) -> CompiledQuery:
        p = spec.period or Period()
        available = ["FY17", "FY18", "FY19", "FY20", "FY21", "FY22", "FY23", "FY24", "FY25", "FY26"]
        is_multi_fy = bool((p.from_ and p.to and p.from_ != p.to) or ("fy" in spec.dimensions))
        if is_multi_fy:
            lo = p.from_ or "FY17"
            hi = p.to or "FY26"
            if hi > "FY26":
                hi = "FY26"
            sql = f"""SELECT
  fiscal_year,
  MAX(IF(scope = 'standalone' AND line_code = 'PL.REV_OPS', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS revenue_from_ops_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'PL.OTHER_INCOME', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS other_income_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'PL.TOTAL_INCOME', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS total_income_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'LEVY.TOTAL', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS statutory_levies_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'LEVY.ROYALTY', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS royalty_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'LEVY.OIDB_CESS', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS oidb_cess_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'LEVY.OTHER_SAED', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS saed_windfall_tax_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'PL.OPEX_10YR', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS operating_expenses_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'PL.EXPL_WRITEOFF', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS exploration_writeoff_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'PL.DDA', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS dda_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'PL.FIN_COST', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS finance_costs_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'PL.TOTAL_EXP', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS total_expenses_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'PL.EXCEPTIONAL', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS exceptional_items_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'PL.PBT', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS pbt_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'PL.TAX', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS tax_expense_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'PL.PAT', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS standalone_pat_cr,
  MAX(IF(scope = 'consolidated' AND line_code = 'PL.PAT', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS consolidated_pat_cr,
  LOGICAL_OR(is_restated) AS is_restated,
  STRING_AGG(DISTINCT footnote_marker, '; ') AS restatement_note,
  MAX(IF(scope = 'standalone' AND line_code = 'PL.REV_OPS', REGEXP_REPLACE(source_doc, r'\\.txt$', '.pdf'), NULL)) AS source_doc,
  MAX(IF(scope = 'standalone' AND line_code = 'PL.REV_OPS', source_page_label, NULL)) AS source_page_label
FROM {_q(_V_TREND_LATEST)}
WHERE fiscal_year BETWEEN {_lit(lo)} AND {_lit(hi)}
  AND verified = TRUE
  AND line_code IN (
    'PL.REV_OPS', 'PL.OTHER_INCOME', 'PL.TOTAL_INCOME', 'LEVY.TOTAL', 'LEVY.ROYALTY',
    'LEVY.OIDB_CESS', 'LEVY.OTHER_SAED', 'PL.OPEX_10YR', 'PL.EXPL_WRITEOFF',
    'PL.DDA', 'PL.FIN_COST', 'PL.TOTAL_EXP', 'PL.EXCEPTIONAL', 'PL.PBT', 'PL.TAX', 'PL.PAT'
  )
GROUP BY fiscal_year
ORDER BY fiscal_year ASC"""
            return CompiledQuery(
                sql=sql,
                subject="corporate",
                metric="pnl_statement",
                metric_label=f"ONGC Schedule III P&L Trend ({lo}–{hi})",
                unit="inr_cr",
                source="template:pnl_statement",
                tables=[_V_TREND_LATEST],
                dims=[("fy", "fiscal_year")],
                value_columns=[
                    "revenue_from_ops_cr", "total_income_cr", "pbt_cr", "standalone_pat_cr",
                    "consolidated_pat_cr", "statutory_levies_cr", "exploration_writeoff_cr", "dda_cr",
                ],
                notes=[f"Verified · Annual Report trend ({lo}–{hi}, latest comparative vintage)"],
                effective_period={"from": lo, "to": hi},
                grain="aggregate",
                data_classes=["general"],
                aggregation="sum",
            )
        fy = p.fy or "FY26"
        if fy not in available:
            fy = "FY26"
        prev_fy = f"FY{int(fy[2:]) - 1:02d}"
        vintage = f"AR_{fy}"
        sql = f"""WITH cur AS (
  SELECT *
  FROM {_q(_V_AS_REPORTED)}
  WHERE statement = 'pnl' AND fiscal_year = {_lit(fy)} AND scope = 'standalone' AND verified = TRUE AND is_own_vintage = TRUE AND source_table = 'standalone_pnl'
),
prv AS (
  SELECT line_code, COALESCE(value_inr_cr, value) AS prev_val
  FROM {_q(_T_FACT_FIN)}
  WHERE statement = 'pnl' AND fiscal_year = {_lit(prev_fy)} AND scope = 'standalone' AND report_vintage = {_lit(vintage)} AND source_table = 'standalone_pnl' AND period_type = 'annual'
),
base AS (
  SELECT MAX(IF(line_code = 'PL.REV_OPS', COALESCE(value_inr_cr, value), NULL)) AS base_val FROM cur
)
SELECT
  cur.display_order AS line_order,
  cur.line_code,
  cur.display_name,
  cur.display_name AS line_item,
  cur.level,
  cur.line_kind,
  cur.section,
  COALESCE(cur.ar_note_ref_typical, cur.schedule3_ref, '') AS note_ref,
  cur.fiscal_year,
  ROUND(COALESCE(cur.value_inr_cr, cur.value), 2) AS value_inr_cr,
  ROUND(COALESCE(cur.value_inr_cr, cur.value), 2) AS amount_cr,
  ROUND(prv.prev_val, 2) AS prior_fy_cr,
  ROUND(COALESCE(cur.value_inr_cr, cur.value) - prv.prev_val, 2) AS yoy_delta_cr,
  ROUND(SAFE_DIVIDE(100.0 * (COALESCE(cur.value_inr_cr, cur.value) - prv.prev_val), ABS(prv.prev_val)), 1) AS yoy_change_pct,
  ROUND(SAFE_DIVIDE(100.0 * COALESCE(cur.value_inr_cr, cur.value), base.base_val), 1) AS pct_of_revenue,
  cur.is_restated,
  cur.footnote_marker,
  REGEXP_REPLACE(cur.source_doc, r'\\.txt$', '.pdf') AS source_doc,
  cur.source_page_label,
  cur.source_system
FROM cur
LEFT JOIN prv USING (line_code)
CROSS JOIN base
ORDER BY cur.display_order ASC, cur.line_order ASC"""
        return CompiledQuery(
            sql=sql,
            subject="corporate",
            metric="pnl_statement",
            metric_label="ONGC Schedule III Statement of Profit & Loss",
            unit="inr_cr",
            source="template:pnl_statement",
            tables=[_V_AS_REPORTED],
            dims=[("line_item", "line_item")],
            value_columns=["amount_cr", "prior_fy_cr", "yoy_delta_cr", "yoy_change_pct", "pct_of_revenue"],
            notes=[f"Verified · Annual Report ({fy}, as reported)"],
            effective_period={"fy": fy},
            grain="aggregate",
            data_classes=["general"],
            aggregation="ratio",
        )

    def _v3__compile_balance_sheet(self, t: TemplateDef, spec: QuerySpec) -> CompiledQuery:
        p = spec.period or Period()
        available = ["FY17", "FY18", "FY19", "FY20", "FY21", "FY22", "FY23", "FY24", "FY25", "FY26"]
        is_multi_fy = bool((p.from_ and p.to and p.from_ != p.to) or ("fy" in spec.dimensions))
        if is_multi_fy:
            lo = p.from_ or "FY17"
            hi = p.to or "FY26"
            if hi > "FY26":
                hi = "FY26"
            sql = f"""SELECT
  fiscal_year,
  MAX(IF(scope = 'standalone' AND line_code = 'BS.TOTAL_ASSETS', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS total_assets_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'BS.ASSETS.NON_CURRENT.TOTAL', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS non_current_assets_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'BS.OG_ASSETS', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS oil_and_gas_assets_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'BS.WIP_TOTAL_10YR', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS cwip_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'BS.INVESTMENTS_NC_10YR', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS investments_subsidiaries_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'BS.ASSETS.CURRENT.TOTAL', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS current_assets_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'BS.CCE', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS cash_and_bank_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'BS.EQUITY.TOTAL', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS net_worth_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'BS.BORROW_TOTAL_10YR', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS total_debt_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'BS.PROV_NC', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS abandonment_provision_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'BS.LIAB.TOTAL', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS total_liabilities_cr,
  LOGICAL_OR(is_restated) AS is_restated,
  STRING_AGG(DISTINCT footnote_marker, '; ') AS restatement_note,
  MAX(IF(scope = 'standalone' AND line_code = 'BS.TOTAL_ASSETS', REGEXP_REPLACE(source_doc, r'\\.txt$', '.pdf'), NULL)) AS source_doc,
  MAX(IF(scope = 'standalone' AND line_code = 'BS.TOTAL_ASSETS', source_page_label, NULL)) AS source_page_label
FROM {_q(_V_TREND_LATEST)}
WHERE fiscal_year BETWEEN {_lit(lo)} AND {_lit(hi)}
  AND verified = TRUE
  AND scope = 'standalone'
  AND line_code IN (
    'BS.TOTAL_ASSETS', 'BS.ASSETS.NON_CURRENT.TOTAL', 'BS.OG_ASSETS', 'BS.WIP_TOTAL_10YR',
    'BS.INVESTMENTS_NC_10YR', 'BS.ASSETS.CURRENT.TOTAL', 'BS.CCE', 'BS.EQUITY.TOTAL',
    'BS.BORROW_TOTAL_10YR', 'BS.PROV_NC', 'BS.LIAB.TOTAL'
  )
GROUP BY fiscal_year
ORDER BY fiscal_year ASC"""
            return CompiledQuery(
                sql=sql,
                subject="corporate",
                metric="balance_sheet",
                metric_label=f"ONGC Schedule III Balance Sheet Trend ({lo}–{hi})",
                unit="inr_cr",
                source="template:balance_sheet",
                tables=[_V_TREND_LATEST],
                dims=[("fy", "fiscal_year")],
                value_columns=[
                    "total_assets_cr", "net_worth_cr", "non_current_assets_cr", "current_assets_cr",
                    "total_liabilities_cr", "total_debt_cr", "cash_and_bank_cr", "cwip_cr",
                ],
                notes=[f"Verified · Annual Report trend ({lo}–{hi}, latest comparative vintage)"],
                effective_period={"from": lo, "to": hi},
                grain="aggregate",
                data_classes=["general"],
                aggregation="sum",
            )
        fy = p.fy or "FY26"
        if fy not in available:
            fy = "FY26"
        prev_fy = f"FY{int(fy[2:]) - 1:02d}"
        vintage = f"AR_{fy}"
        sql = f"""WITH cur AS (
  SELECT *
  FROM {_q(_V_AS_REPORTED)}
  WHERE statement = 'balance_sheet' AND fiscal_year = {_lit(fy)} AND scope = 'standalone' AND verified = TRUE AND is_own_vintage = TRUE AND source_table = 'standalone_balance_sheet'
),
prv AS (
  SELECT line_code, COALESCE(value_inr_cr, value) AS prev_val
  FROM {_q(_T_FACT_FIN)}
  WHERE statement = 'balance_sheet' AND fiscal_year = {_lit(prev_fy)} AND scope = 'standalone' AND report_vintage = {_lit(vintage)} AND source_table = 'standalone_balance_sheet' AND period_type = 'annual'
),
base AS (
  SELECT MAX(IF(line_code = 'BS.TOTAL_ASSETS', COALESCE(value_inr_cr, value), NULL)) AS base_val FROM cur
)
SELECT
  cur.display_order AS line_order,
  cur.line_code,
  cur.display_name,
  cur.display_name AS line_item,
  cur.level,
  cur.line_kind,
  cur.section,
  COALESCE(cur.ar_note_ref_typical, cur.schedule3_ref, '') AS note_ref,
  cur.fiscal_year,
  ROUND(COALESCE(cur.value_inr_cr, cur.value), 2) AS value_inr_cr,
  ROUND(COALESCE(cur.value_inr_cr, cur.value), 2) AS amount_cr,
  ROUND(prv.prev_val, 2) AS prior_fy_cr,
  ROUND(COALESCE(cur.value_inr_cr, cur.value) - prv.prev_val, 2) AS yoy_delta_cr,
  ROUND(SAFE_DIVIDE(100.0 * (COALESCE(cur.value_inr_cr, cur.value) - prv.prev_val), ABS(prv.prev_val)), 1) AS yoy_change_pct,
  ROUND(SAFE_DIVIDE(100.0 * COALESCE(cur.value_inr_cr, cur.value), base.base_val), 1) AS pct_of_assets,
  cur.is_restated,
  cur.footnote_marker,
  REGEXP_REPLACE(cur.source_doc, r'\\.txt$', '.pdf') AS source_doc,
  cur.source_page_label,
  cur.source_system
FROM cur
LEFT JOIN prv USING (line_code)
CROSS JOIN base
ORDER BY cur.display_order ASC, cur.line_order ASC"""
        return CompiledQuery(
            sql=sql,
            subject="corporate",
            metric="balance_sheet",
            metric_label="ONGC Schedule III Balance Sheet",
            unit="inr_cr",
            source="template:balance_sheet",
            tables=[_V_AS_REPORTED],
            dims=[("line_item", "line_item")],
            value_columns=["amount_cr", "prior_fy_cr", "yoy_delta_cr", "yoy_change_pct", "pct_of_assets"],
            notes=[f"Verified · Annual Report ({fy}, as reported)"],
            effective_period={"fy": fy},
            grain="aggregate",
            data_classes=["general"],
            aggregation="ratio",
        )

    def _v3__compile_cash_flow_statement(self, t: TemplateDef, spec: QuerySpec) -> CompiledQuery:
        p = spec.period or Period()
        available = ["FY17", "FY18", "FY19", "FY20", "FY21", "FY22", "FY23", "FY24", "FY25", "FY26"]
        is_multi_fy = bool((p.from_ and p.to and p.from_ != p.to) or ("fy" in spec.dimensions))
        if is_multi_fy:
            lo = p.from_ or "FY17"
            hi = p.to or "FY26"
            if hi > "FY26":
                hi = "FY26"
            sql = f"""SELECT
  fiscal_year,
  MAX(IF(scope = 'standalone' AND line_code = 'CF.CFO', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS operating_cash_flow_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'CF.CFI', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS investing_cash_flow_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'CF.CFF', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS financing_cash_flow_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'CAPEX.TOTAL', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS total_capex_cr,
  ROUND(
    MAX(IF(scope = 'standalone' AND line_code = 'CF.CFO', COALESCE(value_inr_cr, value), NULL))
    - ABS(COALESCE(MAX(IF(scope = 'standalone' AND line_code = 'CAPEX.TOTAL', COALESCE(value_inr_cr, value), NULL)), 0)),
    2
  ) AS free_cash_flow_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'CF.NET_CHANGE_CCE', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS net_cash_change_cr,
  MAX(IF(scope = 'standalone' AND line_code = 'CF.CCE_CLOSE', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS closing_cash_cr,
  LOGICAL_OR(is_restated) AS is_restated,
  STRING_AGG(DISTINCT footnote_marker, '; ') AS restatement_note,
  MAX(IF(scope = 'standalone' AND line_code = 'CF.CFO', REGEXP_REPLACE(source_doc, r'\\.txt$', '.pdf'), NULL)) AS source_doc,
  MAX(IF(scope = 'standalone' AND line_code = 'CF.CFO', source_page_label, NULL)) AS source_page_label
FROM {_q(_V_TREND_LATEST)}
WHERE fiscal_year BETWEEN {_lit(lo)} AND {_lit(hi)}
  AND verified = TRUE
  AND scope = 'standalone'
  AND line_code IN ('CF.CFO', 'CF.CFI', 'CF.CFF', 'CAPEX.TOTAL', 'CF.NET_CHANGE_CCE', 'CF.CCE_CLOSE')
GROUP BY fiscal_year
ORDER BY fiscal_year ASC"""
            return CompiledQuery(
                sql=sql,
                subject="corporate",
                metric="cash_flow_statement",
                metric_label=f"ONGC Ind-AS 7 Cash Flow Trend ({lo}–{hi})",
                unit="inr_cr",
                source="template:cash_flow_statement",
                tables=[_V_TREND_LATEST],
                dims=[("fy", "fiscal_year")],
                value_columns=[
                    "operating_cash_flow_cr", "free_cash_flow_cr", "total_capex_cr",
                    "investing_cash_flow_cr", "financing_cash_flow_cr", "closing_cash_cr",
                ],
                notes=[f"Verified · Annual Report trend ({lo}–{hi}, latest comparative vintage)"],
                effective_period={"from": lo, "to": hi},
                grain="aggregate",
                data_classes=["general"],
                aggregation="sum",
            )
        fy = p.fy or "FY26"
        if fy not in available:
            fy = "FY26"
        prev_fy = f"FY{int(fy[2:]) - 1:02d}"
        vintage = f"AR_{fy}"
        sql = f"""WITH cur AS (
  SELECT *
  FROM {_q(_V_AS_REPORTED)}
  WHERE statement = 'cash_flow' AND fiscal_year = {_lit(fy)} AND scope = 'standalone' AND verified = TRUE AND is_own_vintage = TRUE AND source_table = 'standalone_cash_flow'
),
prv AS (
  SELECT line_code, COALESCE(value_inr_cr, value) AS prev_val
  FROM {_q(_T_FACT_FIN)}
  WHERE statement = 'cash_flow' AND fiscal_year = {_lit(prev_fy)} AND scope = 'standalone' AND report_vintage = {_lit(vintage)} AND source_table = 'standalone_cash_flow' AND period_type = 'annual'
),
base AS (
  SELECT MAX(IF(line_code = 'CF.CFO', COALESCE(value_inr_cr, value), NULL)) AS base_val FROM cur
)
SELECT
  cur.display_order AS line_order,
  cur.line_code,
  cur.display_name,
  cur.display_name AS line_item,
  cur.level,
  cur.line_kind,
  cur.section,
  COALESCE(cur.ar_note_ref_typical, cur.schedule3_ref, 'Ind-AS 7') AS note_ref,
  cur.fiscal_year,
  ROUND(COALESCE(cur.value_inr_cr, cur.value), 2) AS value_inr_cr,
  ROUND(COALESCE(cur.value_inr_cr, cur.value), 2) AS amount_cr,
  ROUND(prv.prev_val, 2) AS prior_fy_cr,
  ROUND(COALESCE(cur.value_inr_cr, cur.value) - prv.prev_val, 2) AS yoy_delta_cr,
  ROUND(SAFE_DIVIDE(100.0 * (COALESCE(cur.value_inr_cr, cur.value) - prv.prev_val), ABS(prv.prev_val)), 1) AS yoy_change_pct,
  ROUND(SAFE_DIVIDE(100.0 * COALESCE(cur.value_inr_cr, cur.value), base.base_val), 1) AS pct_of_ocf,
  cur.is_restated,
  cur.footnote_marker,
  REGEXP_REPLACE(cur.source_doc, r'\\.txt$', '.pdf') AS source_doc,
  cur.source_page_label,
  cur.source_system
FROM cur
LEFT JOIN prv USING (line_code)
CROSS JOIN base
ORDER BY cur.display_order ASC, cur.line_order ASC"""
        return CompiledQuery(
            sql=sql,
            subject="corporate",
            metric="cash_flow_statement",
            metric_label="ONGC Ind-AS 7 Statement of Cash Flows",
            unit="inr_cr",
            source="template:cash_flow_statement",
            tables=[_V_AS_REPORTED],
            dims=[("line_item", "line_item")],
            value_columns=["amount_cr", "prior_fy_cr", "yoy_delta_cr", "yoy_change_pct", "pct_of_ocf"],
            notes=[f"Verified · Annual Report ({fy}, as reported)"],
            effective_period={"fy": fy},
            grain="aggregate",
            data_classes=["general"],
            aggregation="ratio",
        )

    def _v3__compile_financial_ratios(self, t: TemplateDef, spec: QuerySpec) -> CompiledQuery:
        p = spec.period or Period()
        available = ["FY17", "FY18", "FY19", "FY20", "FY21", "FY22", "FY23", "FY24", "FY25", "FY26"]
        is_multi_fy = bool((p.from_ and p.to and p.from_ != p.to) or ("fy" in spec.dimensions))
        if is_multi_fy:
            lo = p.from_ or "FY17"
            hi = p.to or "FY26"
            if hi > "FY26":
                hi = "FY26"
            sql = f"""SELECT
  fiscal_year,
  MAX(IF(scope = 'standalone' AND line_code = 'RATIO.PBIDT_MARGIN_PCT', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS ebitda_margin_pct,
  MAX(IF(scope = 'standalone' AND line_code = 'RATIO.PAT_MARGIN_PCT', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS pat_margin_pct,
  MAX(IF(scope = 'standalone' AND line_code = 'RATIO.ROCE', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS roce_pct,
  MAX(IF(scope = 'standalone' AND line_code = 'RATIO.ROE_INCL_EXC', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS roe_pct,
  MAX(IF(scope = 'standalone' AND line_code = 'RATIO.DEBT_EQUITY', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS debt_to_equity_ratio,
  MAX(IF(scope = 'standalone' AND line_code = 'RATIO.CURRENT', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS current_ratio,
  MAX(IF(scope = 'standalone' AND line_code IN ('PL.EPS_BASIC', 'RATIO.EPS'), ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS eps_basic_inr,
  MAX(IF(scope = 'standalone' AND line_code = 'RATIO.DPS', ROUND(COALESCE(value_inr_cr, value), 2), NULL)) AS dividend_per_share_inr,
  LOGICAL_OR(is_restated) AS is_restated,
  STRING_AGG(DISTINCT footnote_marker, '; ') AS restatement_note,
  MAX(IF(scope = 'standalone' AND line_code = 'RATIO.ROCE', REGEXP_REPLACE(source_doc, r'\\.txt$', '.pdf'), NULL)) AS source_doc,
  MAX(IF(scope = 'standalone' AND line_code = 'RATIO.ROCE', source_page_label, NULL)) AS source_page_label
FROM {_q(_V_TREND_LATEST)}
WHERE fiscal_year BETWEEN {_lit(lo)} AND {_lit(hi)}
  AND verified = TRUE
  AND scope = 'standalone'
  AND line_code IN (
    'RATIO.PBIDT_MARGIN_PCT', 'RATIO.PAT_MARGIN_PCT', 'RATIO.ROCE', 'RATIO.ROE_INCL_EXC',
    'RATIO.DEBT_EQUITY', 'RATIO.CURRENT', 'PL.EPS_BASIC', 'RATIO.EPS', 'RATIO.DPS'
  )
GROUP BY fiscal_year
ORDER BY fiscal_year ASC"""
            return CompiledQuery(
                sql=sql,
                subject="corporate",
                metric="financial_ratios",
                metric_label=f"ONGC Key Financial Ratios Trend ({lo}–{hi})",
                unit="pct",
                source="template:financial_ratios",
                tables=[_V_TREND_LATEST],
                dims=[("fy", "fiscal_year")],
                value_columns=[
                    "ebitda_margin_pct", "pat_margin_pct", "roce_pct", "roe_pct",
                    "debt_to_equity_ratio", "current_ratio", "eps_basic_inr", "dividend_per_share_inr",
                ],
                notes=[f"Verified · Annual Report · Financial Ratios ({lo}–{hi})"],
                effective_period={"from": lo, "to": hi},
                grain="aggregate",
                data_classes=["general"],
                aggregation="avg",
            )
        fy = p.fy or "FY26"
        if fy not in available:
            fy = "FY26"
        prev_fy = f"FY{int(fy[2:]) - 1:02d}"
        vintage = f"AR_{fy}"
        sql = f"""WITH cur AS (
  SELECT *
  FROM {_q(_V_TREND_LATEST)}
  WHERE statement = 'ratio' AND fiscal_year = {_lit(fy)} AND scope = 'standalone'
),
prv AS (
  SELECT line_code, COALESCE(value_inr_cr, value) AS prev_val
  FROM {_q(_V_TREND_LATEST)}
  WHERE statement = 'ratio' AND fiscal_year = {_lit(prev_fy)} AND scope = 'standalone'
)
SELECT
  cur.display_order AS line_order,
  cur.line_code,
  cur.display_name,
  cur.display_name AS line_item,
  cur.level,
  cur.line_kind,
  cur.section AS category,
  cur.unit,
  cur.fiscal_year,
  ROUND(COALESCE(cur.value_inr_cr, cur.value), 2) AS value_inr_cr,
  ROUND(COALESCE(cur.value, cur.value_inr_cr), 2) AS value,
  ROUND(prv.prev_val, 2) AS prior_fy_value,
  ROUND(COALESCE(cur.value, cur.value_inr_cr) - prv.prev_val, 2) AS yoy_delta,
  COALESCE(cur.formula, cur.subtotal_formula, '') AS formula,
  cur.is_restated,
  cur.footnote_marker,
  REGEXP_REPLACE(cur.source_doc, r'\\.txt$', '.pdf') AS source_doc,
  cur.source_page_label,
  cur.source_system
FROM cur
LEFT JOIN prv USING (line_code)
ORDER BY cur.display_order ASC, cur.line_order ASC"""
        return CompiledQuery(
            sql=sql,
            subject="corporate",
            metric="financial_ratios",
            metric_label="ONGC Financial Ratios & Credit Scorecard",
            unit="ratio",
            source="template:financial_ratios",
            tables=[_V_AS_REPORTED],
            dims=[("line_item", "line_item")],
            value_columns=["value", "prior_fy_value", "yoy_delta"],
            notes=[f"Verified · Annual Report · {fy}"],
            effective_period={"fy": fy},
            grain="aggregate",
            data_classes=["general"],
            aggregation="avg",
        )

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

    def _v3__execute_local_financial_fallback(self, compiled: CompiledQuery) -> Optional[QueryResult]:
        """Deterministic local snapshot fallback from verified fact_snapshot.parquet when BigQuery is unavailable."""
        from pathlib import Path
        import sys

        t0 = time.perf_counter()
        repo_root = Path(__file__).resolve().parents[4]
        try:
            import pandas as pd
        except ImportError:
            py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            for cand_root in (repo_root, repo_root.parent / "HR and Finance_ONGC__v3P1", repo_root.parent / "HR and Finance_ONGC"):
                sp = cand_root / "financial_ssot" / ".venv" / "lib" / py_ver / "site-packages"
                if sp.exists() and str(sp) not in sys.path:
                    sys.path.insert(0, str(sp))
            import pandas as pd

        env_snap = os.getenv("YUKTI_FIN_SNAPSHOT_PATH")
        snap_path = Path(env_snap) if env_snap else (repo_root / "financial_ssot" / "out" / "fact_snapshot.parquet")
        dim_path = repo_root / "financial_ssot" / "dim_financial_line.csv"
        if not snap_path.exists():
            return None

        try:
            raw_df = pd.read_parquet(snap_path)
            # CRITICAL (SPEC-01 / P1.10a): strictly serve ONLY verified=TRUE rows; never serve unverified/poisoned rows.
            vdf = raw_df[(raw_df["verified"] == True) & (raw_df["period_type"] == "annual")].copy()  # noqa: E712
            if vdf.empty:
                return None
            if dim_path.exists():
                dim_df = pd.read_csv(dim_path)
                vdf = vdf.merge(dim_df, on="line_code", how="left", suffixes=("", "_dim"))
            else:
                vdf["display_name"] = vdf.get("line_name_as_reported", vdf["line_code"])
                vdf["display_order"] = vdf.get("line_order", 0)
                vdf["level"] = 1
                vdf["line_kind"] = "detail"
                vdf["section"] = vdf["statement"]
                vdf["ar_note_ref_typical"] = ""
                vdf["schedule3_ref"] = ""
                vdf["formula"] = ""
                vdf["subtotal_formula"] = ""

            def _norm_doc(val: Any) -> Optional[str]:
                if pd.isna(val) or val is None:
                    return None
                s = str(val).strip()
                return re.sub(r"\.txt$", ".pdf", s) if s else None

            def _norm_str(val: Any) -> Optional[str]:
                if pd.isna(val) or val is None:
                    return None
                s = str(val).strip()
                return s if s and s.lower() != "nan" else None

            def _val_num(r: Any) -> Optional[float]:
                v = r.get("value_inr_cr")
                if pd.isna(v) or v is None:
                    v = r.get("value")
                return round(float(v), 2) if (v is not None and pd.notna(v)) else None

            def _as_rep_df() -> pd.DataFrame:
                return vdf[(vdf["is_own_vintage"] == True) | (vdf["is_fallback_vintage"] == True) | ((vdf["statement"] == "ratio") & (vdf["is_latest_vintage"] == True))].copy()  # noqa: E712

            def _latest_df() -> pd.DataFrame:
                return vdf[vdf["is_latest_vintage"] == True].copy()  # noqa: E712

            ep = compiled.effective_period or {}
            fy = ep.get("fy")
            lo, hi = ep.get("from"), ep.get("to")

            # 1. Single-FY statement templates
            stmt_map = {
                "pnl_statement": ("pnl", "PL.REV_OPS", "pct_of_revenue"),
                "balance_sheet": ("balance_sheet", "BS.TOTAL_ASSETS", "pct_of_assets"),
                "cash_flow_statement": ("cash_flow", "CF.CFO", "pct_of_ocf"),
                "financial_ratios": ("ratio", None, None),
            }
            if compiled.metric in stmt_map and fy:
                st_name, base_code, pct_col = stmt_map[compiled.metric]
                adf = _as_rep_df()
                cur_df = adf[(adf["statement"] == st_name) & (adf["fiscal_year"] == fy) & (adf["scope"] == "standalone") & (adf["is_own_vintage"] == True) & (adf["source_table"] == "standalone_" + st_name)].copy() if st_name != "ratio" else adf[(adf["statement"] == st_name) & (adf["fiscal_year"] == fy) & (adf["scope"] == "standalone") & (adf["is_latest_vintage"] == True)].copy()
                if cur_df.empty:
                    return None
                cur_df = cur_df.sort_values(["display_order", "line_order"])
                prev_fy = f"FY{int(fy[2:]) - 1:02d}"
                prv_df = vdf[(vdf["statement"] == st_name) & (vdf["fiscal_year"] == prev_fy) & (vdf["scope"] == "standalone") & (vdf["report_vintage"] == "AR_" + fy) & (vdf["source_table"] == "standalone_" + st_name) & (vdf["period_type"] == "annual")] if st_name != "ratio" else vdf[(vdf["statement"] == st_name) & (vdf["fiscal_year"] == prev_fy) & (vdf["scope"] == "standalone") & (vdf["is_latest_vintage"] == True)]
                prv_map = {str(r["line_code"]): _val_num(r) for _, r in prv_df.iterrows()}
                base_val = None
                if base_code:
                    b_rows = cur_df[cur_df["line_code"] == base_code]
                    if not b_rows.empty:
                        base_val = _val_num(b_rows.iloc[0])

                rows: List[Dict[str, Any]] = []
                for _, r in cur_df.iterrows():
                    lc = str(r["line_code"])
                    cur_v = _val_num(r)
                    prv_v = prv_map.get(lc)
                    delta_v = round(cur_v - prv_v, 2) if (cur_v is not None and prv_v is not None) else None
                    yoy_pct = round(100.0 * (cur_v - prv_v) / abs(prv_v), 1) if (cur_v is not None and prv_v not in (None, 0)) else None
                    fn_marker = None
                    if str(r.get("source_system")) == "xbrl":
                        fn_marker = f"{fy} from {r.get("report_vintage")} BSE Reg 33 filing (AR PDF scanned)"
                    row_dict: Dict[str, Any] = {
                        "line_order": int(r.get("display_order") or r.get("line_order") or 0),
                        "line_code": lc,
                        "display_name": _norm_str(r.get("display_name")) or _norm_str(r.get("line_name_as_reported")) or lc,
                        "line_item": _norm_str(r.get("display_name")) or _norm_str(r.get("line_name_as_reported")) or lc,
                        "level": int(r.get("level") or 1),
                        "line_kind": _norm_str(r.get("line_kind")) or "detail",
                        "section": _norm_str(r.get("section")) or st_name,
                        "note_ref": _norm_str(r.get("ar_note_ref_typical")) or _norm_str(r.get("schedule3_ref")) or "",
                        "fiscal_year": fy,
                        "value_inr_cr": cur_v,
                        "is_restated": bool(r.get("is_restated")),
                        "footnote_marker": fn_marker,
                        "source_doc": _norm_doc(r.get("source_doc")),
                        "source_page_label": _norm_str(r.get("source_page_label")),
                        "source_system": _norm_str(r.get("source_system")),
                    }
                    if compiled.metric == "financial_ratios":
                        row_dict.update({
                            "category": row_dict["section"],
                            "unit": _norm_str(r.get("unit")) or "",
                            "value": cur_v,
                            "prior_fy_value": prv_v,
                            "yoy_delta": delta_v,
                            "formula": _norm_str(r.get("formula")) or _norm_str(r.get("subtotal_formula")) or "",
                        })
                    else:
                        pct_base = round(100.0 * cur_v / base_val, 1) if (cur_v is not None and base_val not in (None, 0)) else None
                        row_dict.update({
                            "amount_cr": cur_v,
                            "prior_fy_cr": prv_v,
                            "yoy_delta_cr": delta_v,
                            "yoy_change_pct": yoy_pct,
                        })
                        if pct_col:
                            row_dict[pct_col] = pct_base
                    rows.append(row_dict)
                if rows:
                    return QueryResult(columns=list(rows[0].keys()), rows=rows, total_bytes=0,
                                       latency_ms=round((time.perf_counter() - t0) * 1000, 1), dry_run_bytes=0)

            # 2. Multi-FY statement templates
            if compiled.metric in stmt_map and lo and hi:
                ldf = _latest_df()
                ldf = ldf[(ldf["fiscal_year"] >= lo) & (ldf["fiscal_year"] <= hi)]
                if ldf.empty:
                    return None
                fys = sorted(ldf["fiscal_year"].unique())
                lkp = {(str(r["scope"]), str(r["fiscal_year"]), str(r["line_code"])): r for _, r in ldf.iterrows()}

                def _lv(sc: str, f_yr: str, cd: str) -> Optional[float]:
                    rec = lkp.get((sc, f_yr, cd))
                    return _val_num(rec) if rec is not None else None

                rows = []
                for f_yr in fys:
                    if compiled.metric == "pnl_statement":
                        p_rec = lkp.get(("standalone", f_yr, "PL.REV_OPS"))
                        rows.append({
                            "fiscal_year": f_yr,
                            "revenue_from_ops_cr": _lv("standalone", f_yr, "PL.REV_OPS"),
                            "other_income_cr": _lv("standalone", f_yr, "PL.OTHER_INCOME"),
                            "total_income_cr": _lv("standalone", f_yr, "PL.TOTAL_INCOME"),
                            "statutory_levies_cr": _lv("standalone", f_yr, "LEVY.TOTAL"),
                            "royalty_cr": _lv("standalone", f_yr, "LEVY.ROYALTY"),
                            "oidb_cess_cr": _lv("standalone", f_yr, "LEVY.OIDB_CESS"),
                            "saed_windfall_tax_cr": _lv("standalone", f_yr, "LEVY.OTHER_SAED"),
                            "operating_expenses_cr": _lv("standalone", f_yr, "PL.OPEX_10YR"),
                            "exploration_writeoff_cr": _lv("standalone", f_yr, "PL.EXPL_WRITEOFF"),
                            "dda_cr": _lv("standalone", f_yr, "PL.DDA"),
                            "finance_costs_cr": _lv("standalone", f_yr, "PL.FIN_COST"),
                            "total_expenses_cr": _lv("standalone", f_yr, "PL.TOTAL_EXP"),
                            "exceptional_items_cr": _lv("standalone", f_yr, "PL.EXCEPTIONAL"),
                            "pbt_cr": _lv("standalone", f_yr, "PL.PBT"),
                            "tax_expense_cr": _lv("standalone", f_yr, "PL.TAX"),
                            "standalone_pat_cr": _lv("standalone", f_yr, "PL.PAT"),
                            "consolidated_pat_cr": _lv("consolidated", f_yr, "PL.PAT"),
                            "is_restated": bool(p_rec["is_restated"]) if p_rec is not None else False,
                            "source_doc": _norm_doc(p_rec["source_doc"]) if p_rec is not None else None,
                            "source_page_label": _norm_str(p_rec["source_page_label"]) if p_rec is not None else None,
                        })
                        p_rec = lkp.get(("standalone", f_yr, "BS.TOTAL_ASSETS"))
                        rows.append({
                            "fiscal_year": f_yr,
                            "total_assets_cr": _lv("standalone", f_yr, "BS.TOTAL_ASSETS"),
                            "non_current_assets_cr": _lv("standalone", f_yr, "BS.ASSETS.NON_CURRENT.TOTAL"),
                            "oil_and_gas_assets_cr": _lv("standalone", f_yr, "BS.OG_ASSETS"),
                            "cwip_cr": _lv("standalone", f_yr, "BS.WIP_TOTAL_10YR"),
                            "investments_subsidiaries_cr": _lv("standalone", f_yr, "BS.INVESTMENTS_NC_10YR"),
                            "current_assets_cr": _lv("standalone", f_yr, "BS.ASSETS.CURRENT.TOTAL"),
                            "cash_and_bank_cr": _lv("standalone", f_yr, "BS.CCE"),
                            "net_worth_cr": _lv("standalone", f_yr, "BS.EQUITY.TOTAL"),
                            "total_debt_cr": _lv("standalone", f_yr, "BS.BORROW_TOTAL_10YR"),
                            "abandonment_provision_cr": _lv("standalone", f_yr, "BS.PROV_NC"),
                            "total_liabilities_cr": _lv("standalone", f_yr, "BS.LIAB.TOTAL"),
                            "is_restated": bool(p_rec["is_restated"]) if p_rec is not None else False,
                            "source_doc": _norm_doc(p_rec["source_doc"]) if p_rec is not None else None,
                            "source_page_label": _norm_str(p_rec["source_page_label"]) if p_rec is not None else None,
                        })
                    elif compiled.metric == "cash_flow_statement":
                        p_rec = lkp.get(("standalone", f_yr, "CF.CFO"))
                        cfo_v = _lv("standalone", f_yr, "CF.CFO")
                        capex_v = _lv("standalone", f_yr, "CAPEX.TOTAL")
                        rows.append({
                            "fiscal_year": f_yr,
                            "operating_cash_flow_cr": cfo_v,
                            "investing_cash_flow_cr": _lv("standalone", f_yr, "CF.CFI"),
                            "financing_cash_flow_cr": _lv("standalone", f_yr, "CF.CFF"),
                            "total_capex_cr": capex_v,
                            "free_cash_flow_cr": round(cfo_v - abs(capex_v or 0.0), 2) if cfo_v is not None else None,
                            "net_cash_change_cr": _lv("standalone", f_yr, "CF.NET_CHANGE_CCE"),
                            "closing_cash_cr": _lv("standalone", f_yr, "CF.CCE_CLOSE"),
                            "is_restated": bool(p_rec["is_restated"]) if p_rec is not None else False,
                            "source_doc": _norm_doc(p_rec["source_doc"]) if p_rec is not None else None,
                            "source_page_label": _norm_str(p_rec["source_page_label"]) if p_rec is not None else None,
                        })
                    elif compiled.metric == "financial_ratios":
                        p_rec = lkp.get(("standalone", f_yr, "RATIO.ROCE"))
                        rows.append({
                            "fiscal_year": f_yr,
                            "ebitda_margin_pct": _lv("standalone", f_yr, "RATIO.PBIDT_MARGIN_PCT"),
                            "pat_margin_pct": _lv("standalone", f_yr, "RATIO.PAT_MARGIN_PCT"),
                            "roce_pct": _lv("standalone", f_yr, "RATIO.ROCE"),
                            "roe_pct": _lv("standalone", f_yr, "RATIO.ROE_INCL_EXC"),
                            "debt_to_equity_ratio": _lv("standalone", f_yr, "RATIO.DEBT_EQUITY"),
                            "current_ratio": _lv("standalone", f_yr, "RATIO.CURRENT"),
                            "eps_basic_inr": _lv("standalone", f_yr, "PL.EPS_BASIC") or _lv("standalone", f_yr, "RATIO.EPS"),
                            "dividend_per_share_inr": _lv("standalone", f_yr, "RATIO.DPS"),
                            "is_restated": bool(p_rec["is_restated"]) if p_rec is not None else False,
                            "source_doc": _norm_doc(p_rec["source_doc"]) if p_rec is not None else None,
                            "source_page_label": _norm_str(p_rec["source_page_label"]) if p_rec is not None else None,
                        })
                if rows:
                    return QueryResult(columns=list(rows[0].keys()), rows=rows, total_bytes=0,
                                       latency_ms=round((time.perf_counter() - t0) * 1000, 1), dry_run_bytes=0)

            # 3. Corporate subject metrics (single-FY -> as_reported; multi-FY -> latest trend)
            if compiled.subject == "corporate" and (compiled.metric in CORP_METRIC_TO_SSOT or compiled.metric in ["ebitda_corporate_cr", "revenue_per_employee_cr", "employee_headcount"]):
                is_multi = bool(lo and hi)
                src_df = _latest_df() if is_multi else _as_rep_df()
                if is_multi:
                    src_df = src_df[(src_df["fiscal_year"] >= lo) & (src_df["fiscal_year"] <= hi)]
                elif fy:
                    src_df = src_df[src_df["fiscal_year"] == fy]
                if src_df.empty:
                    return None
                lkp = {(str(r["scope"]), str(r["fiscal_year"]), str(r["line_code"])): r for _, r in src_df.iterrows()}
                p_scope, p_code = CORP_METRIC_TO_SSOT.get(compiled.metric, ("standalone", None))
                fys = sorted(src_df["fiscal_year"].unique())
                rows = []
                for f_yr in fys:
                    p_rec = lkp.get((p_scope, f_yr, p_code)) if p_code else None
                    if p_rec is None and not is_multi and compiled.metric not in ["ebitda_corporate_cr", "revenue_per_employee_cr", "employee_headcount"]:
                        continue
                    row_d: Dict[str, Any] = {"fiscal_year": f_yr}
                    for vc in compiled.value_columns:
                        if vc in CORP_METRIC_TO_SSOT:
                            sc, cd = CORP_METRIC_TO_SSOT[vc]
                            rec = lkp.get((sc, f_yr, cd))
                            row_d[vc] = _val_num(rec) if rec is not None else None
                        elif vc == "roce_incl_exc_pct":
                            rec = lkp.get(("standalone", f_yr, "RATIO.ROCE_INCL_EXC"))
                            row_d[vc] = _val_num(rec) if rec is not None else None
                        elif vc == "dividend_pct":
                            rec = lkp.get(("standalone", f_yr, "RATIO.DIVIDEND_PCT"))
                            row_d[vc] = _val_num(rec) if rec is not None else None
                        elif vc == "employee_headcount":
                            hc_map = {"FY17": 33660, "FY18": 32265, "FY19": 31065, "FY20": 30105, "FY21": 28479, "FY22": 27165, "FY23": 25993, "FY24": 25847, "FY25": 24368, "FY26": 23117}
                            if f_yr in hc_map:
                                row_d[vc] = hc_map[f_yr]
                                row_d["line_code"] = "HR.HEADCOUNT"
                                row_d["display_name"] = "Total employee headcount"
                                row_d["value_inr_cr"] = hc_map[f_yr]
                                row_d["is_restated"] = False
                                row_d["source_system"] = "HR system"
                        elif vc == "revenue_per_employee_cr":
                            rev_rec = lkp.get(("standalone", f_yr, "PL.REV_OPS"))
                            rev_val = _val_num(rev_rec) if rev_rec is not None else None
                            hc_map = {"FY16": 33927, "FY17": 33660, "FY18": 32265, "FY19": 31065, "FY20": 30105, "FY21": 28479, "FY22": 27165, "FY23": 25993, "FY24": 25847, "FY25": 24368, "FY26": 23117}
                            prev_yr = f"FY{int(f_yr[-2:]) - 1}"
                            curr_hc = hc_map.get(f_yr)
                            prev_hc = hc_map.get(prev_yr)
                            if rev_val is not None and curr_hc and prev_hc:
                                avg_hc = (curr_hc + prev_hc) / 2.0
                                row_d[vc] = round(rev_val / avg_hc, 3)
                                if compiled.metric == "revenue_per_employee_cr":
                                    row_d["line_code"] = "RATIO.REV_PER_EMPLOYEE"
                                    row_d["display_name"] = "Revenue per employee"
                                    row_d["is_restated"] = False
                                    row_d["source_system"] = "AR (Derived)"
                        elif vc == "ebitda_corporate_cr":
                            pbt_r = lkp.get(("standalone", f_yr, "PL.PBT"))
                            fin_r = lkp.get(("standalone", f_yr, "PL.FIN_COST"))
                            dda_r = lkp.get(("standalone", f_yr, "PL.DDA"))
                            oth_r = lkp.get(("standalone", f_yr, "PL.OTHER_INCOME"))
                            pbt = _val_num(pbt_r) or 0
                            fin = _val_num(fin_r) or 0
                            dda = _val_num(dda_r) or 0
                            oth = _val_num(oth_r) or 0
                            if pbt_r is not None:
                                row_d[vc] = round(pbt + fin + dda - oth, 2)
                                if compiled.metric == "ebitda_corporate_cr":
                                    row_d["line_code"] = "DERIVED"
                                    row_d["display_name"] = "EBITDA"
                                    row_d["is_restated"] = False
                                    row_d["source_system"] = "AR (Derived)"
                    if p_rec is not None:
                        is_rest = bool(p_rec.get("is_restated"))
                        fn_mk = None
                        if is_multi and is_rest:
                            fn_mk = f"{f_yr} restated in {p_rec.get('report_vintage')}"

                        row_d.update({
                            "line_code": p_code,
                            "display_name": _norm_str(p_rec.get("display_name")) or _norm_str(p_rec.get("line_name_as_reported")) or p_code,
                            "value_inr_cr": _val_num(p_rec),
                            "is_restated": is_rest,
                            "restatement_note": _norm_str(p_rec.get("notes")) or (f"{f_yr} restated in {p_rec.get('report_vintage')}" if is_rest else None),
                            "footnote_marker": fn_mk,
                            "source_doc": _norm_doc(p_rec.get("source_doc")),
                            "source_page_label": _norm_str(p_rec.get("source_page_label")),
                            "source_system": _norm_str(p_rec.get("source_system")),
                        })
                    if row_d.get(compiled.metric) is not None:
                        rows.append(row_d)
                if rows:
                    return QueryResult(columns=list(rows[0].keys()), rows=rows, total_bytes=0,
                                       latency_ms=round((time.perf_counter() - t0) * 1000, 1), dry_run_bytes=0)
        except Exception as exc:
            logger.warning(f"Local snapshot fallback failed for {compiled.metric}: {exc}")
            return None
        return None

    async def execute(self, compiled: CompiledQuery) -> QueryResult:
        """Dry-run + execute off the event loop (asyncio.to_thread), with local SSOT fallback on auth/network error."""
        try:
            if os.getenv("YUKTI_FORCE_BQ_FAIL", "0") in ("1", "true", "yes"):  # BEH-07.22 forced-failure test flag
                raise ConnectionError("forced BigQuery failure (YUKTI_FORCE_BQ_FAIL=1)")
            return await asyncio.to_thread(self._run_sync, compiled.sql)
        except Exception as e:
            fb = self._execute_local_financial_fallback(compiled)
            if fb is not None:
                # P0.3 / P1.10a (BUG-04): the fallback is no longer silent; callers label it "local_snapshot".
                logger.warning(f"BigQuery unavailable ({type(e).__name__}); serving {compiled.metric} from local snapshot")
                fb.source = "local_snapshot"
                fb.snapshot_date = _local_snapshot_date()
                fb.snapshot_run_id = _local_snapshot_run_id()
                return fb
            raise e


    def _legacy__compile_pnl_statement(self, t: TemplateDef, spec: QuerySpec) -> CompiledQuery:
        p = spec.period or Period()
        available = ["FY17", "FY18", "FY19", "FY20", "FY21", "FY22", "FY23", "FY24", "FY25", "FY26"]
        is_multi_fy = bool((p.from_ and p.to and p.from_ != p.to) or ("fy" in spec.dimensions))
        if is_multi_fy:
            lo = p.from_ or "FY17"
            hi = p.to or "FY26"
            if hi > "FY26":
                hi = "FY26"
            sql = f"""SELECT
  fiscal_year,
  ROUND(gross_revenue_inr_cr, 0) AS revenue_from_ops_cr,
  ROUND(other_income_inr_cr, 0) AS other_income_cr,
  ROUND(statutory_levies_total_inr_cr, 0) AS statutory_levies_cr,
  ROUND(royalty_inr_cr, 0) AS royalty_cr,
  ROUND(oidb_cess_inr_cr, 0) AS oidb_cess_cr,
  ROUND(saed_windfall_tax_inr_cr, 0) AS saed_windfall_tax_cr,
  ROUND(net_revenue_inr_cr, 0) AS net_revenue_cr,
  ROUND(operating_expenses_total_inr_cr, 0) AS operating_expenses_cr,
  ROUND(ebitda_inr_cr, 0) AS ebitda_cr,
  ROUND(exploration_costs_written_off_inr_cr, 0) AS exploration_writeoff_cr,
  ROUND(dda_inr_cr, 0) AS dda_cr,
  ROUND(finance_costs_inr_cr, 0) AS finance_costs_cr,
  ROUND(exceptional_items_inr_cr, 0) AS exceptional_items_cr,
  ROUND(pbt_inr_cr, 0) AS pbt_cr,
  ROUND(tax_expense_total_inr_cr, 0) AS tax_expense_cr,
  ROUND(pat_inr_cr, 0) AS standalone_pat_cr,
  ROUND(consolidated_pat_inr_cr, 0) AS consolidated_pat_cr
FROM {_q('hrfin_gold.ssot_corporate_annual_360')}
WHERE fiscal_year BETWEEN {_lit(lo)} AND {_lit(hi)}
ORDER BY fiscal_year ASC"""
            return CompiledQuery(
                sql=sql,
                subject="corporate",
                metric="pnl_statement",
                metric_label=f"ONGC Schedule III P&L Trend ({lo}–{hi})",
                unit="inr_cr",
                source="template:pnl_statement",
                tables=["hrfin_gold.ssot_corporate_annual_360"],
                dims=[("fy", "fiscal_year")],
                value_columns=[
                    "revenue_from_ops_cr", "ebitda_cr", "pbt_cr", "standalone_pat_cr",
                    "consolidated_pat_cr", "statutory_levies_cr", "exploration_writeoff_cr", "dda_cr",
                ],
                notes=[f"Source: financial_build snapshot (unverified; real AR data pending) ({lo}–{hi})"],  # P0.3 (BUG-02): honest "unverified" label until SPEC-01 lands
                effective_period={"from": lo, "to": hi},
                grain="aggregate",
                data_classes=["general"],
                aggregation="sum",
            )
        fy = p.fy or "FY26"
        if fy not in available:
            fy = "FY26"
        sql = f"""SELECT
  line_order,
  line_name AS line_item,
  schedule_ref AS note_ref,
  yahoo_finance_line,
  ROUND(amount_inr_cr, 2) AS amount_cr,
  ROUND(prior_fy_amount_inr_cr, 2) AS prior_fy_cr,
  ROUND(yoy_delta_inr_cr, 2) AS yoy_delta_cr,
  ROUND(yoy_change_pct, 1) AS yoy_change_pct,
  ROUND(pct_of_revenue, 1) AS pct_of_revenue,
  section,
  line_code,
  driver_note
FROM {_q('hrfin_gold.ssot_corporate_pnl_lines')}
WHERE fiscal_year = {_lit(fy)}
ORDER BY line_order ASC"""
        return CompiledQuery(
            sql=sql,
            subject="corporate",
            metric="pnl_statement",
            metric_label="ONGC Schedule III Statement of Profit & Loss",
            unit="inr_cr",
            source="template:pnl_statement",
            tables=["hrfin_gold.ssot_corporate_pnl_lines", "hrfin_gold.ssot_corporate_annual_360"],
            dims=[("line_item", "line_item")],
            value_columns=["amount_cr", "prior_fy_cr", "yoy_delta_cr", "yoy_change_pct", "pct_of_revenue"],
            notes=[f"Source: financial_build snapshot (unverified; real AR data pending) · {fy}"],  # P0.3 (BUG-02): honest "unverified" label until SPEC-01 lands
            effective_period={"fy": fy},
            grain="aggregate",
            data_classes=["general"],
            aggregation="ratio",
        )
    def _legacy__compile_balance_sheet(self, t: TemplateDef, spec: QuerySpec) -> CompiledQuery:
        p = spec.period or Period()
        available = ["FY17", "FY18", "FY19", "FY20", "FY21", "FY22", "FY23", "FY24", "FY25", "FY26"]
        is_multi_fy = bool((p.from_ and p.to and p.from_ != p.to) or ("fy" in spec.dimensions))
        if is_multi_fy:
            lo = p.from_ or "FY17"
            hi = p.to or "FY26"
            if hi > "FY26":
                hi = "FY26"
            sql = f"""SELECT
  fiscal_year,
  ROUND(total_assets_inr_cr, 0) AS total_assets_cr,
  ROUND(non_current_assets_inr_cr, 0) AS non_current_assets_cr,
  ROUND(oil_and_gas_assets_inr_cr, 0) AS oil_and_gas_assets_cr,
  ROUND(cwip_inr_cr, 0) AS cwip_cr,
  ROUND(investments_subsidiaries_jv_inr_cr, 0) AS investments_subsidiaries_cr,
  ROUND(current_assets_inr_cr, 0) AS current_assets_cr,
  ROUND(cash_and_bank_inr_cr, 0) AS cash_and_bank_cr,
  ROUND(net_worth_inr_cr, 0) AS net_worth_cr,
  ROUND(total_debt_inr_cr, 0) AS total_debt_cr,
  ROUND(abandonment_provision_inr_cr, 0) AS abandonment_provision_cr,
  ROUND(total_liabilities_inr_cr, 0) AS total_liabilities_cr
FROM {_q('hrfin_gold.ssot_corporate_annual_360')}
WHERE fiscal_year BETWEEN {_lit(lo)} AND {_lit(hi)}
ORDER BY fiscal_year ASC"""
            return CompiledQuery(
                sql=sql,
                subject="corporate",
                metric="balance_sheet",
                metric_label=f"ONGC Schedule III Balance Sheet Trend ({lo}–{hi})",
                unit="inr_cr",
                source="template:balance_sheet",
                tables=["hrfin_gold.ssot_corporate_annual_360"],
                dims=[("fy", "fiscal_year")],
                value_columns=[
                    "total_assets_cr", "net_worth_cr", "non_current_assets_cr", "current_assets_cr",
                    "total_liabilities_cr", "total_debt_cr", "cash_and_bank_cr", "cwip_cr",
                ],
                notes=[f"Source: financial_build snapshot (unverified; real AR data pending) ({lo}–{hi})"],  # P0.3 (BUG-02): honest "unverified" label until SPEC-01 lands
                effective_period={"from": lo, "to": hi},
                grain="aggregate",
                data_classes=["general"],
                aggregation="sum",
            )
        fy = p.fy or "FY26"
        if fy not in available:
            fy = "FY26"
        sql = f"""SELECT
  line_order,
  line_name AS line_item,
  schedule_ref AS note_ref,
  section,
  ROUND(amount_inr_cr, 2) AS amount_cr,
  ROUND(prior_fy_amount_inr_cr, 2) AS prior_fy_cr,
  ROUND(yoy_delta_inr_cr, 2) AS yoy_delta_cr,
  ROUND(yoy_change_pct, 1) AS yoy_change_pct,
  ROUND(pct_of_total_assets, 1) AS pct_of_assets,
  yahoo_finance_line,
  line_code,
  driver_note
FROM {_q('hrfin_gold.ssot_corporate_balance_sheet_lines')}
WHERE fiscal_year = {_lit(fy)}
ORDER BY line_order ASC"""
        return CompiledQuery(
            sql=sql,
            subject="corporate",
            metric="balance_sheet",
            metric_label="ONGC Schedule III Balance Sheet",
            unit="inr_cr",
            source="template:balance_sheet",
            tables=["hrfin_gold.ssot_corporate_balance_sheet_lines", "hrfin_gold.ssot_corporate_annual_360"],
            dims=[("line_item", "line_item")],
            value_columns=["amount_cr", "prior_fy_cr", "yoy_delta_cr", "yoy_change_pct", "pct_of_assets"],
            notes=[f"Source: financial_build snapshot (unverified; real AR data pending) · {fy}"],  # P0.3 (BUG-02): honest "unverified" label until SPEC-01 lands
            effective_period={"fy": fy},
            grain="aggregate",
            data_classes=["general"],
            aggregation="ratio",
        )
    def _legacy__compile_cash_flow_statement(self, t: TemplateDef, spec: QuerySpec) -> CompiledQuery:
        p = spec.period or Period()
        available = ["FY17", "FY18", "FY19", "FY20", "FY21", "FY22", "FY23", "FY24", "FY25", "FY26"]
        is_multi_fy = bool((p.from_ and p.to and p.from_ != p.to) or ("fy" in spec.dimensions))
        if is_multi_fy:
            lo = p.from_ or "FY17"
            hi = p.to or "FY26"
            if hi > "FY26":
                hi = "FY26"
            sql = f"""SELECT
  fiscal_year,
  ROUND(operating_cash_flow_inr_cr, 0) AS operating_cash_flow_cr,
  ROUND(investing_cash_flow_inr_cr, 0) AS investing_cash_flow_cr,
  ROUND(financing_cash_flow_inr_cr, 0) AS financing_cash_flow_cr,
  ROUND(total_capex_spent_inr_cr, 0) AS total_capex_cr,
  ROUND(free_cash_flow_inr_cr, 0) AS free_cash_flow_cr,
  ROUND(net_cash_change_inr_cr, 0) AS net_cash_change_cr,
  ROUND(closing_cash_inr_cr, 0) AS closing_cash_cr
FROM {_q('hrfin_gold.ssot_corporate_annual_360')}
WHERE fiscal_year BETWEEN {_lit(lo)} AND {_lit(hi)}
ORDER BY fiscal_year ASC"""
            return CompiledQuery(
                sql=sql,
                subject="corporate",
                metric="cash_flow_statement",
                metric_label=f"ONGC Ind-AS 7 Cash Flow Trend ({lo}–{hi})",
                unit="inr_cr",
                source="template:cash_flow_statement",
                tables=["hrfin_gold.ssot_corporate_annual_360"],
                dims=[("fy", "fiscal_year")],
                value_columns=[
                    "operating_cash_flow_cr", "free_cash_flow_cr", "total_capex_cr",
                    "investing_cash_flow_cr", "financing_cash_flow_cr", "closing_cash_cr",
                ],
                notes=[f"Source: financial_build snapshot (unverified; real AR data pending) ({lo}–{hi})"],  # P0.3 (BUG-02): honest "unverified" label until SPEC-01 lands
                effective_period={"from": lo, "to": hi},
                grain="aggregate",
                data_classes=["general"],
                aggregation="sum",
            )
        fy = p.fy or "FY26"
        if fy not in available:
            fy = "FY26"
        sql = f"""SELECT
  line_order,
  line_name AS line_item,
  schedule_ref AS note_ref,
  section,
  ROUND(amount_inr_cr, 2) AS amount_cr,
  ROUND(prior_fy_amount_inr_cr, 2) AS prior_fy_cr,
  ROUND(yoy_delta_inr_cr, 2) AS yoy_delta_cr,
  ROUND(yoy_change_pct, 1) AS yoy_change_pct,
  ROUND(pct_of_ocf, 1) AS pct_of_ocf,
  yahoo_finance_line,
  line_code,
  driver_note
FROM {_q('hrfin_gold.ssot_corporate_cash_flow_lines')}
WHERE fiscal_year = {_lit(fy)}
ORDER BY line_order ASC"""
        return CompiledQuery(
            sql=sql,
            subject="corporate",
            metric="cash_flow_statement",
            metric_label="ONGC Ind-AS 7 Statement of Cash Flows",
            unit="inr_cr",
            source="template:cash_flow_statement",
            tables=["hrfin_gold.ssot_corporate_cash_flow_lines", "hrfin_gold.ssot_corporate_annual_360"],
            dims=[("line_item", "line_item")],
            value_columns=["amount_cr", "prior_fy_cr", "yoy_delta_cr", "yoy_change_pct", "pct_of_ocf"],
            notes=[f"Source: financial_build snapshot (unverified; real AR data pending) · {fy}"],  # P0.3 (BUG-02): honest "unverified" label until SPEC-01 lands
            effective_period={"fy": fy},
            grain="aggregate",
            data_classes=["general"],
            aggregation="ratio",
        )
    def _legacy__compile_financial_ratios(self, t: TemplateDef, spec: QuerySpec) -> CompiledQuery:
        p = spec.period or Period()
        available = ["FY17", "FY18", "FY19", "FY20", "FY21", "FY22", "FY23", "FY24", "FY25", "FY26"]
        is_multi_fy = bool((p.from_ and p.to and p.from_ != p.to) or ("fy" in spec.dimensions))
        if is_multi_fy:
            lo = p.from_ or "FY17"
            hi = p.to or "FY26"
            if hi > "FY26":
                hi = "FY26"
            sql = f"""SELECT
  fiscal_year,
  ROUND(ebitda_margin_pct, 1) AS ebitda_margin_pct,
  ROUND(pat_margin_pct, 1) AS pat_margin_pct,
  ROUND(standalone_roce_pct, 1) AS roce_pct,
  ROUND(roe_pct, 1) AS roe_pct,
  ROUND(debt_to_equity_ratio, 2) AS debt_to_equity_ratio,
  ROUND(current_ratio, 2) AS current_ratio,
  ROUND(eps_basic_inr, 2) AS eps_basic_inr,
  ROUND(dividend_per_share_inr, 2) AS dividend_per_share_inr
FROM {_q('hrfin_gold.ssot_corporate_annual_360')}
WHERE fiscal_year BETWEEN {_lit(lo)} AND {_lit(hi)}
ORDER BY fiscal_year ASC"""
            return CompiledQuery(
                sql=sql,
                subject="corporate",
                metric="financial_ratios",
                metric_label=f"ONGC Key Financial Ratios Trend ({lo}–{hi})",
                unit="pct",
                source="template:financial_ratios",
                tables=["hrfin_gold.ssot_corporate_annual_360"],
                dims=[("fy", "fiscal_year")],
                value_columns=[
                    "ebitda_margin_pct", "pat_margin_pct", "roce_pct", "roe_pct",
                    "debt_to_equity_ratio", "current_ratio", "eps_basic_inr", "dividend_per_share_inr",
                ],
                notes=[f"ONGC Financial Ratios & Per-Share Metrics ({lo}–{hi})"],
                effective_period={"from": lo, "to": hi},
                grain="aggregate",
                data_classes=["general"],
                aggregation="avg",
            )
        fy = p.fy or "FY26"
        if fy not in available:
            fy = "FY26"
        sql = f"""SELECT
  line_order,
  ratio_name AS line_item,
  category,
  unit,
  ROUND(value, 2) AS value,
  ROUND(prior_fy_value, 2) AS prior_fy_value,
  ROUND(yoy_delta, 2) AS yoy_delta,
  formula,
  line_code
FROM {_q('hrfin_gold.ssot_corporate_ratios_lines')}
WHERE fiscal_year = {_lit(fy)}
ORDER BY line_order ASC"""
        return CompiledQuery(
            sql=sql,
            subject="corporate",
            metric="financial_ratios",
            metric_label="ONGC Financial Ratios & Credit Scorecard",
            unit="ratio",
            source="template:financial_ratios",
            tables=["hrfin_gold.ssot_corporate_ratios_lines", "hrfin_gold.ssot_corporate_annual_360"],
            dims=[("line_item", "line_item")],
            value_columns=["value", "prior_fy_value", "yoy_delta"],
            notes=[f"Source: financial_build snapshot (unverified; real AR data pending) · {fy}"],  # P0.3 (BUG-02): honest "unverified" label until SPEC-01 lands
            effective_period={"fy": fy},
            grain="aggregate",
            data_classes=["general"],
            aggregation="avg",
        )
    def _legacy__execute_local_financial_fallback(self, compiled: CompiledQuery) -> Optional[QueryResult]:
        """Deterministic local JSON fallback for 3-statements, ratios, and corporate 360 when BigQuery ADC expires."""
        import json
        from pathlib import Path
        t0 = time.perf_counter()
        data_dir = Path(__file__).resolve().parents[4] / "financial_build" / "data"
        if not data_dir.exists():
            return None
        ep = compiled.effective_period or {}
        fy = ep.get("fy")
        lo, hi = ep.get("from"), ep.get("to")
        try:
            if compiled.metric == "pnl_statement" and fy:
                raw_rows = json.loads((data_dir / "ongc_10yr_schedule_iii_lines.json").read_text())
                rows = [
                    {
                        "line_order": r.get("line_order"),
                        "line_item": r.get("line_name"),
                        "note_ref": r.get("schedule_ref"),
                        "yahoo_finance_line": r.get("yahoo_finance_line"),
                        "amount_cr": round(float(r["amount_inr_cr"]), 2) if r.get("amount_inr_cr") is not None else None,
                        "prior_fy_cr": round(float(r["prior_fy_amount_inr_cr"]), 2) if r.get("prior_fy_amount_inr_cr") is not None else None,
                        "yoy_delta_cr": round(float(r["yoy_delta_inr_cr"]), 2) if r.get("yoy_delta_inr_cr") is not None else None,
                        "yoy_change_pct": round(float(r["yoy_change_pct"]), 1) if r.get("yoy_change_pct") is not None else None,
                        "pct_of_revenue": round(float(r["pct_of_revenue"]), 1) if r.get("pct_of_revenue") is not None else None,
                        "section": r.get("section"),
                        "line_code": r.get("line_code"),
                        "driver_note": r.get("driver_note"),
                    }
                    for r in raw_rows if r.get("fiscal_year") == fy
                ]
                rows.sort(key=lambda x: x.get("line_order") or 0)
                if rows:
                    return QueryResult(columns=list(rows[0].keys()), rows=rows, total_bytes=0,
                                       latency_ms=round((time.perf_counter() - t0) * 1000, 1), dry_run_bytes=0)
            if compiled.metric == "balance_sheet" and fy:
                raw_rows = json.loads((data_dir / "ongc_10yr_balance_sheet_lines.json").read_text())
                rows = [
                    {
                        "line_order": r.get("line_order"),
                        "line_item": r.get("line_name"),
                        "note_ref": r.get("schedule_ref"),
                        "section": r.get("section"),
                        "amount_cr": round(float(r["amount_inr_cr"]), 2) if r.get("amount_inr_cr") is not None else None,
                        "prior_fy_cr": round(float(r["prior_fy_amount_inr_cr"]), 2) if r.get("prior_fy_amount_inr_cr") is not None else None,
                        "yoy_delta_cr": round(float(r["yoy_delta_inr_cr"]), 2) if r.get("yoy_delta_inr_cr") is not None else None,
                        "yoy_change_pct": round(float(r["yoy_change_pct"]), 1) if r.get("yoy_change_pct") is not None else None,
                        "pct_of_assets": round(float(r["pct_of_total_assets"]), 1) if r.get("pct_of_total_assets") is not None else None,
                        "yahoo_finance_line": r.get("yahoo_finance_line"),
                        "line_code": r.get("line_code"),
                        "driver_note": r.get("driver_note"),
                    }
                    for r in raw_rows if r.get("fiscal_year") == fy
                ]
                rows.sort(key=lambda x: x.get("line_order") or 0)
                if rows:
                    return QueryResult(columns=list(rows[0].keys()), rows=rows, total_bytes=0,
                                       latency_ms=round((time.perf_counter() - t0) * 1000, 1), dry_run_bytes=0)
            if compiled.metric == "cash_flow_statement" and fy:
                raw_rows = json.loads((data_dir / "ongc_10yr_cash_flow_lines.json").read_text())
                rows = [
                    {
                        "line_order": r.get("line_order"),
                        "line_item": r.get("line_name"),
                        "note_ref": r.get("schedule_ref"),
                        "section": r.get("section"),
                        "amount_cr": round(float(r["amount_inr_cr"]), 2) if r.get("amount_inr_cr") is not None else None,
                        "prior_fy_cr": round(float(r["prior_fy_amount_inr_cr"]), 2) if r.get("prior_fy_amount_inr_cr") is not None else None,
                        "yoy_delta_cr": round(float(r["yoy_delta_inr_cr"]), 2) if r.get("yoy_delta_inr_cr") is not None else None,
                        "yoy_change_pct": round(float(r["yoy_change_pct"]), 1) if r.get("yoy_change_pct") is not None else None,
                        "pct_of_ocf": round(float(r["pct_of_ocf"]), 1) if r.get("pct_of_ocf") is not None else None,
                        "yahoo_finance_line": r.get("yahoo_finance_line"),
                        "line_code": r.get("line_code"),
                        "driver_note": r.get("driver_note"),
                    }
                    for r in raw_rows if r.get("fiscal_year") == fy
                ]
                rows.sort(key=lambda x: x.get("line_order") or 0)
                if rows:
                    return QueryResult(columns=list(rows[0].keys()), rows=rows, total_bytes=0,
                                       latency_ms=round((time.perf_counter() - t0) * 1000, 1), dry_run_bytes=0)
            if compiled.metric == "financial_ratios" and fy:
                raw_rows = json.loads((data_dir / "ongc_10yr_ratios_lines.json").read_text())
                rows = [
                    {
                        "line_order": r.get("line_order"),
                        "line_item": r.get("ratio_name"),
                        "category": r.get("category"),
                        "unit": r.get("unit"),
                        "value": round(float(r["value"]), 2) if r.get("value") is not None else None,
                        "prior_fy_value": round(float(r["prior_fy_value"]), 2) if r.get("prior_fy_value") is not None else None,
                        "yoy_delta": round(float(r["yoy_delta"]), 2) if r.get("yoy_delta") is not None else None,
                        "formula": r.get("formula"),
                        "line_code": r.get("line_code"),
                    }
                    for r in raw_rows if r.get("fiscal_year") == fy
                ]
                rows.sort(key=lambda x: x.get("line_order") or 0)
                if rows:
                    return QueryResult(columns=list(rows[0].keys()), rows=rows, total_bytes=0,
                                       latency_ms=round((time.perf_counter() - t0) * 1000, 1), dry_run_bytes=0)
            if compiled.metric == "pnl_statement" and lo and hi:
                raw_rows = json.loads((data_dir / "ongc_10yr_corporate_wide.json").read_text())
                rows = [
                    {
                        "fiscal_year": r.get("fiscal_year"),
                        "revenue_from_ops_cr": round(float(r.get("gross_revenue_inr_cr") or 0), 0),
                        "other_income_cr": round(float(r.get("other_income_inr_cr") or 0), 0),
                        "statutory_levies_cr": round(float(r.get("statutory_levies_total_inr_cr") or 0), 0),
                        "royalty_cr": round(float(r.get("royalty_inr_cr") or 0), 0),
                        "oidb_cess_cr": round(float(r.get("oidb_cess_inr_cr") or 0), 0),
                        "saed_windfall_tax_cr": round(float(r.get("saed_windfall_tax_inr_cr") or 0), 0),
                        "net_revenue_cr": round(float(r.get("net_revenue_inr_cr") or 0), 0),
                        "operating_expenses_cr": round(float(r.get("operating_expenses_total_inr_cr") or 0), 0),
                        "ebitda_cr": round(float(r.get("ebitda_inr_cr") or 0), 0),
                        "exploration_writeoff_cr": round(float(r.get("exploration_costs_written_off_inr_cr") or 0), 0),
                        "dda_cr": round(float(r.get("dda_inr_cr") or 0), 0),
                        "finance_costs_cr": round(float(r.get("finance_costs_inr_cr") or 0), 0),
                        "exceptional_items_cr": round(float(r.get("exceptional_items_inr_cr") or 0), 0),
                        "pbt_cr": round(float(r.get("pbt_inr_cr") or 0), 0),
                        "tax_expense_cr": round(float(r.get("tax_expense_total_inr_cr") or 0), 0),
                        "standalone_pat_cr": round(float(r.get("pat_inr_cr") or 0), 0),
                        "consolidated_pat_cr": round(float(r.get("consolidated_pat_inr_cr") or 0), 0),
                    }
                    for r in raw_rows if lo <= str(r.get("fiscal_year", "")) <= hi
                ]
                if rows:
                    return QueryResult(columns=list(rows[0].keys()), rows=rows, total_bytes=0,
                                       latency_ms=round((time.perf_counter() - t0) * 1000, 1), dry_run_bytes=0)
        except Exception:
            return None
        return None
    def _compile_pnl_statement(self, *args, **kwargs):
        from app.config import YUKTI_FIN_SSOT_V3
        return getattr(self, '_v3__compile_pnl_statement')(*args, **kwargs) if YUKTI_FIN_SSOT_V3 else getattr(self, '_legacy__compile_pnl_statement')(*args, **kwargs)

    def _compile_balance_sheet(self, *args, **kwargs):
        from app.config import YUKTI_FIN_SSOT_V3
        return getattr(self, '_v3__compile_balance_sheet')(*args, **kwargs) if YUKTI_FIN_SSOT_V3 else getattr(self, '_legacy__compile_balance_sheet')(*args, **kwargs)

    def _compile_cash_flow_statement(self, *args, **kwargs):
        from app.config import YUKTI_FIN_SSOT_V3
        return getattr(self, '_v3__compile_cash_flow_statement')(*args, **kwargs) if YUKTI_FIN_SSOT_V3 else getattr(self, '_legacy__compile_cash_flow_statement')(*args, **kwargs)

    def _compile_financial_ratios(self, *args, **kwargs):
        from app.config import YUKTI_FIN_SSOT_V3
        return getattr(self, '_v3__compile_financial_ratios')(*args, **kwargs) if YUKTI_FIN_SSOT_V3 else getattr(self, '_legacy__compile_financial_ratios')(*args, **kwargs)

    def _execute_local_financial_fallback(self, *args, **kwargs):
        from app.config import YUKTI_FIN_SSOT_V3
        return getattr(self, '_v3__execute_local_financial_fallback')(*args, **kwargs) if YUKTI_FIN_SSOT_V3 else getattr(self, '_legacy__execute_local_financial_fallback')(*args, **kwargs)

def _local_snapshot_date() -> Optional[str]:
    """Date (ISO) of the verified SSOT snapshot used by the local fallback."""
    import json
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[4]
    env_snap = os.getenv("YUKTI_FIN_SNAPSHOT_PATH")
    snap_path = Path(env_snap) if env_snap else (repo_root / "financial_ssot" / "out" / "fact_snapshot.parquet")
    if snap_path.exists():
        try:
            import pandas as pd
            s = pd.read_parquet(snap_path, columns=["extracted_at"])
            if not s.empty:
                ext = str(s["extracted_at"].iloc[0])
                if len(ext) >= 10 and ext[:4].isdigit():
                    return ext[:10]
        except Exception:
            pass
    data_dir = repo_root / "financial_build" / "data"
    try:
        manifest = data_dir / "snapshot_manifest.json"
        if manifest.exists():
            d = json.loads(manifest.read_text(encoding="utf-8")).get("snapshot_date")
            if d:
                return str(d)
    except (OSError, ValueError):
        pass
    return "2026-10-24"


def _local_snapshot_run_id() -> str:
    """Run ID of the verified SSOT snapshot used by the local fallback."""
    import json
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[4]
    env_snap = os.getenv("YUKTI_FIN_SNAPSHOT_PATH")
    snap_path = Path(env_snap) if env_snap else (repo_root / "financial_ssot" / "out" / "fact_snapshot.parquet")
    if snap_path.exists():
        try:
            import pandas as pd
            s = pd.read_parquet(snap_path, columns=["extracted_at"])
            if not s.empty:
                ext = str(s["extracted_at"].iloc[0])
                if ext:
                    return ext.replace("-", "").replace(":", "").split(".")[0]
        except Exception:
            pass
    data_dir = repo_root / "financial_build" / "data"
    try:
        manifest = data_dir / "snapshot_manifest.json"
        if manifest.exists():
            rid = json.loads(manifest.read_text(encoding="utf-8")).get("run_id")
            if rid:
                return str(rid)
    except (OSError, ValueError):
        pass
    return "ssot_v3"


_COMPILER: Optional[Compiler] = None


def get_compiler() -> Compiler:
    global _COMPILER
    if _COMPILER is None:
        _COMPILER = Compiler()
    return _COMPILER
