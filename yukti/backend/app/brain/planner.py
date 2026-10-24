"""QuerySpec planner (B2.2): Gemini structured output -> new QuerySpec or SpecPatch.

Input: the question, the previous QuerySpec (if any) and a catalog summary generated from
`semantic_model.yaml` + the entity dictionary. Output (JSON, schema-constrained) is turned
into a validated QuerySpec / SpecPatch here. Two deterministic guards run after the model:
the fiscal-year resolver (D-30) and the entity dictionary (codes must exist), so the LLM
never decides a period or an entity code on its own.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from functools import lru_cache
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from app.brain.query_spec import Compare, Filter, Period, QuerySpec, Sort, SpecPatch, apply_patch
from app.brain.semantic_model import SemanticModel, get_semantic_model
from app.config import DEFAULT_TEXT_MODEL, GCP_PROJECT, VERTEX_TEXT_LOCATION
from app.semantic.entities import get_entities
from app.semantic.normalize import current_fy, fiscal_years_for_sql, last_complete_fy, resolve_fy

logger = logging.getLogger("yukti.brain.planner")

DIM_ALIASES = {"work_centre": "wc", "location": "wc", "station": "wc", "asset_wc": "asset", "fiscal_year": "fy",
               "year": "fy", "field_name": "field", "grade_id": "grade", "discipline_id": "discipline"}


def normalize_asr_query(question: str) -> str:
    """Normalizes common speech-to-text phonetic mis-transcriptions for ONGC terms."""
    if not question:
        return ""
    q = question
    q = re.sub(r"\b(nyc|o\s*n\s*g\s*c|oen\s*gc|ong\s*see)\b", "ONGC", q, flags=re.IGNORECASE)
    q = re.sub(r"\b([eE])\s*-\s*([0-9])\b", lambda m: f"E{m.group(2)}", q)
    q = re.sub(r"\bmahesana\b", "Mehsana", q, flags=re.IGNORECASE)
    return q

PLANNER_MODEL = os.getenv("YUKTI_PLANNER_MODEL", DEFAULT_TEXT_MODEL)
_OPS = ["=", "!=", ">", ">=", "<", "<=", "in", "not_in", "between", "like"]
_CHARTS = ["pie", "donut", "bar", "hbar", "stacked_bar", "grouped_bar", "line", "area", "combo", "histogram",
           "box", "treemap", "heatmap", "waterfall", "bullet", "gauge", "funnel", "scatter", "kpi", "table", "map"]

PLAN_SCHEMA: Dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "intent": {"type": "STRING", "enum": ["data", "replot", "policy", "what_if", "document", "chitchat", "other"]},
        "is_followup": {"type": "BOOLEAN"},
        "metric": {"type": "STRING"},
        "grain": {"type": "STRING", "enum": ["aggregate", "row"]},
        "set_dimensions": {"type": "BOOLEAN"},
        "dimensions": {"type": "ARRAY", "items": {"type": "STRING"}},
        "filters": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "field": {"type": "STRING"}, "op": {"type": "STRING", "enum": _OPS},
            "values": {"type": "ARRAY", "items": {"type": "STRING"}}}, "required": ["field", "op", "values"]}},
        "remove_filters": {"type": "ARRAY", "items": {"type": "STRING"}},
        "compare_field": {"type": "STRING"},
        "compare_values": {"type": "ARRAY", "items": {"type": "STRING"}},
        "fy": {"type": "STRING"},
        "fy_from": {"type": "STRING"},
        "fy_to": {"type": "STRING"},
        "sort_by": {"type": "STRING"},
        "sort_dir": {"type": "STRING", "enum": ["asc", "desc"]},
        "limit": {"type": "INTEGER"},
        "chart_kind": {"type": "STRING", "enum": _CHARTS},
    },
    "required": ["intent", "is_followup"],
}


@dataclass
class Plan:
    intent: str
    is_followup: bool = False
    spec: Optional[QuerySpec] = None            # the resulting full spec (new or patched)
    patch: Optional[SpecPatch] = None           # set for follow-ups / drill-downs
    chart_kind: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0


@lru_cache(maxsize=1)
def catalog_summary() -> str:
    """Compact catalog for the planner prompt (generated, never hand-written)."""
    m: SemanticModel = get_semantic_model()
    ents = get_entities()
    from app.semantic.normalize import categorical_values

    lines: List[str] = ["SUBJECTS, METRICS AND FIELDS (use these names exactly):"]
    for s in m.subjects.values():
        lines.append(f"- subject {s.name} [{s.domain}; period={s.period}{'; default ' + s.default_fy if s.default_fy else ''}]: {s.description}")
        lines.append("  metrics: " + "; ".join(f"{mn} = {md.label}" for mn, md in s.metrics.items()))
        vals = categorical_values([s.table])
        fdesc = []
        for fn, fd in s.fields.items():
            if fd.entity:
                fdesc.append(f"{fn} (code of {fd.entity})")
            elif fd.kind == "categorical":
                v = sorted(vals.get(fd.column.lower(), []))
                fdesc.append(f"{fn} in {v[:12]}" if v else fn)
            else:
                fdesc.append(f"{fn} ({fd.kind})")
        lines.append("  fields: " + "; ".join(fdesc))
        if s.row_columns:
            lines.append("  grain=row returns a list with: " + ", ".join(rc["as"] for rc in s.row_columns))
    for t in m.templates.values():
        lines.append(f"- analysis metric {t.name} [{t.domain}]: {t.description}")
    lines.append("- filter field `region` (any subject with wc/asset) values: " + ", ".join(sorted(ents._regions_cfg)))
    lines.append("\nWORK CENTRES (code: name, city): " + "; ".join(
        f"{c}: {a.get('short_name')} ({a.get('city')})" for c, a in ents.work_centres.items()))
    lines.append("DISCIPLINES: " + "; ".join(f"{c}: {a.get('name')}" for c, a in ents.disciplines.items()))
    lines.append("FIELDS (oil/gas): " + "; ".join(f"{c}: {a.get('name')}" for c, a in ents.fields.items()))
    lines.append("GRADES (ordered): " + "; ".join(f"{c}: {a.get('designation', '')[:40]}" for c, a in ents.grades.items()))
    return "\n".join(lines)


RULES = f"""You turn an ONGC executive's question into a structured data plan. Output JSON only.
Intent: "data" for any question answerable from the subjects below (counts, lists, rankings, trends,
comparisons); "replot" if the user only asks to show the SAME data as another chart/table; "policy" for
rules/clauses/eligibility questions with no numbers; "what_if" for hypothetical simulations; "document" for
drafting notes/letters/replies; "chitchat" for greetings; "other" if no subject fits (do not force a metric).
Questions about rules, norms, limits, entitlements, eligibility, procedures or "what is the minimum/maximum
allowed" are "policy" even when they mention numbers or tenure. Questions about one specific person ("my", "my
reporting officer", an employee id) are "other". Questions mixing a rule with a count of people are "data".
Rules:
- metric MUST be one of the listed metric names. Pick the subject that holds the data.
- Follow-ups: if a previous plan is given and the question refines it (pronouns like "their", "them",
  "those", "this", "what about X", "only ...", "by ...", "compare with ...", "last year"), set is_followup=true and
  output ONLY what changes: new/replaced filters in `filters` (a filter on an already-filtered field replaces it),
  `remove_filters`, `set_dimensions`+`dimensions` for a new breakdown, `grain`, fy fields, metric if it changes.
  A brand-new topic is is_followup=false with a full plan.
- "names", "who are they", "list them", "give me their names" => grain "row" (keeps filters).
- "by X" / "breakdown by X" / "X-wise" => set_dimensions=true, dimensions=[X]; back to aggregate if it was a list.
- "compare with B" / "versus B" => compare_field = the entity field (e.g. wc), compare_values = [B]; keep the rest.
- Grades: "E5 and above"/"E5+" => filter grade >= E5; "GMs" => grade = E7; "GM and above" => grade >= E7.
- "executives"/"officers" => cadre = executive. "posted/in office/stayed for N years or more", "N+ years",
  "more than N years", "N saal se zyada" => station_tenure_years >= N (tenure thresholds always use >=).
- "asset"/"work centre"/"location"/"station" as a breakdown => dimension wc (HR subjects) or asset (finance).
- When a work centre is named, do NOT add state/sector/city filters for it.
- Entities: use codes from the lists (wc, discipline, field, grade). Regions ("North East", "Western Offshore",
  "Gujarat") => filter field region with the region name.
- "loss-making"/"made losses" fields => metric pbt_cr, dimensions [field], filter pbt_cr < 0 only if the user asks
  ONLY for the losses; "most profitable and loss-making" => no filter (ranking shows both).
- Fiscal years: anchor date 19-Oct-2026, current FY = {current_fy()} (in progress); "last year" = {last_complete_fy()};
  "last N years" = N complete FYs ending {last_complete_fy()}. A resolved time hint may be supplied; follow it.
- Metric hints: headcount growth / increase / "added headcount" over years => headcount_change (period range);
  attrition / exits / resignations => separations or voluntary_exits (dimension grade if "by grade");
  manpower or employee cost per BOE / barrel => manpower_cost_usd_per_boe (dimension asset);
  employee cost as % of revenue => manpower_cost_pct_of_revenue; lifting cost => lifting_cost_usd_per_boe;
  company "profit and loss statement" / "P&L statement" / "income statement" / "complete P&L" (no field/asset named) => pnl_statement;
  company "balance sheet" / "assets and liabilities" / "statement of financial position" => balance_sheet;
  company "cash flow statement" / "statement of cash flows" / "cash flow bridge" => cash_flow_statement;
  company "financial ratios" / "key ratios" / "ratio analysis" / "credit ratios" / "solvency ratios" => financial_ratios;
  company "profit" / "munafa" (no field named) => pat_cr (profit after tax); only "PBT"/"before tax" => pbt_corporate_cr;
  statutory levies / royalty / OIDB cess / SAED windfall tax => statutory_levies_cr, royalty_cr, oidb_cess_cr, or saed_windfall_tax_cr;
  exploration costs written off / dry wells / survey costs => exploration_costs_written_off_cr, exploratory_wells_written_off_cr, or survey_costs_written_off_cr;
  DD&A / depreciation / depletion => dda_cr; tax expense / current tax / deferred tax => tax_expense_cr, current_tax_cr, or deferred_tax_cr;
  total assets / non-current assets / current assets / CWIP / oil & gas assets / investments in subsidiaries / site restoration fund / cash & bank / inventories / trade receivables => total_assets_cr, non_current_assets_cr, current_assets_cr, cwip_cr, oil_and_gas_assets_cr, investments_subsidiaries_jv_cr, site_restoration_fund_cr, cash_and_bank_cr, inventories_cr, or trade_receivables_cr;
  net worth / equity / share capital / reserves / debt / borrowings / net debt / lease liabilities / abandonment provision (ARO) / deferred tax liability => net_worth_cr, equity_share_capital_cr, other_equity_reserves_cr, total_debt_cr, long_term_debt_cr, short_term_debt_cr, net_debt_cr, lease_liabilities_cr, abandonment_provision_cr, or deferred_tax_liability_net_cr;
  ROE / ROA / ROCE / debt-to-equity / net debt-to-EBITDA / interest coverage / current ratio / receivable days / EPS / book value per share / dividend per share => roe_pct, roa_pct, roce_pct, debt_to_equity_ratio, net_debt_to_ebitda_ratio, interest_coverage_ratio, current_ratio, receivable_days, eps_basic_inr, book_value_per_share_inr, or dividend_per_share_inr;
  consolidated PAT / consolidated revenue / ONGC.NS group => consolidated_pat_cr or consolidated_revenue_cr;
  subsidiaries (HPCL, MRPL, OVL, OPAL, OTPC) => subsidiary_pat_cr or subsidiary_revenue_cr (dimension subsidiary).
- Years "in/at an office, station, city or work centre" = station_tenure_years; total_tenure_years only for
  total service ("with ONGC", "service", "career").
- "profit margin"/"margins" of fields or assets => ebitda_margin_pct (pbt_margin_pct only if PBT is named).
- "retention rate"/"share who stayed 5+ years" => long_stay_share_pct with cadre filter, and REMOVE any
  station_tenure_years filter (remove_filters) because the share is computed over everyone.
- Trends ("increased/decreased/changed over the last N years", "trend", "year by year") => add dimension fy.
- If the question needs a measure that is not listed (e.g. DPC cases, grievances, succession), answer intent "other" instead of substituting a different metric.
- Never invent numbers; never write SQL.
"""


class Planner:
    def __init__(self, model: str = PLANNER_MODEL):
        self.model = model
        self._client: Optional[genai.Client] = None
        self.sm = get_semantic_model()
        self.ents = get_entities()

    @property
    def client(self) -> genai.Client:
        # The genai async transport binds to the event loop that first used it; re-create the client
        # when called from a different loop (tests, scripts) so a stale loop never breaks planning.
        try:
            loop_id = id(asyncio.get_running_loop())
        except RuntimeError:
            loop_id = None
        if self._client is None or getattr(self, "_client_loop", None) != loop_id:
            self._client = genai.Client(vertexai=True, project=GCP_PROJECT, location=VERTEX_TEXT_LOCATION)
            self._client_loop = loop_id
        return self._client

    def _prompt(self, question: str, prev: Optional[QuerySpec], history: List[str], fy_hint: Optional[Dict[str, Any]]) -> str:
        parts = [RULES, catalog_summary()]
        if prev is not None:
            parts.append("PREVIOUS PLAN (the answer currently on screen): " + json.dumps(prev.to_contract()))
        if history:
            parts.append("RECENT USER QUESTIONS (oldest first): " + " | ".join(history[-3:]))
        if fy_hint:
            parts.append(f"RESOLVED TIME HINT for this question: {json.dumps(fy_hint)}")
        parts.append(f"QUESTION: {question}")
        return "\n\n".join(parts)

    async def _call(self, prompt: str) -> Dict[str, Any]:
        cfg = types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=PLAN_SCHEMA,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            max_output_tokens=1024,
        )
        resp = None
        for attempt in range(3):
            try:
                resp = await self.client.aio.models.generate_content(model=self.model, contents=prompt, config=cfg)
                break
            except Exception as e:
                if attempt < 2 and ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)):
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                raise
        text = (resp.text or "").strip() if resp else ""
        return json.loads(text) if text else {}

    # ------------------------------------------------------------ helpers
    def _subject_for(self, metric: str):
        subj, m, t = self.sm.resolve_metric(metric)
        return subj, m, t

    def _coerce_filter(self, f: Dict[str, Any], subject, notes: List[str]) -> Optional[Filter]:
        field = str(f.get("field", "")).strip()
        op = f.get("op") or "="
        vals = [str(v).strip() for v in (f.get("values") or []) if str(v).strip() != ""]
        if not field or not vals:
            return None
        fd = subject.fields.get(field) if subject is not None else None
        from app.brain.compiler import WC_ATTRIBUTE_FIELDS
        if field in WC_ATTRIBUTE_FIELDS and subject is not None and fd is None:
            return Filter(field=field, op="in" if op in ("=", "in") else op, value=vals) if op in ("=", "in", "!=", "not_in") else None
        if field != "region" and subject is not None and fd is None:
            fb = subject.dimension_fallbacks.get(field)
            if not fb:
                notes.append(f"dropped filter {field} (not in {subject.name})")
                return None
            field, fd = fb, subject.fields.get(fb)
        parsed: List[Any] = []
        for v in vals:
            if fd is not None and fd.kind == "number":
                m = re.search(r"-?\d+(?:\.\d+)?", v.replace(",", ""))
                if not m:
                    return None
                parsed.append(float(m.group(0)) if "." in m.group(0) else int(m.group(0)))
            elif fd is not None and fd.entity:
                code = self._entity(fd.entity, v)
                if not code and field == "field" and subject is not None and "asset" in subject.fields:
                    wc_code = self._entity("wc", v)
                    if wc_code and all(self._entity("wc", x) or self._entity("field", x) for x in vals):
                        field = "asset"
                        fd = subject.fields.get("asset")
                        parsed = [self._entity("wc", x) or self._entity("field", x) for x in vals]
                        parsed = [x for x in parsed if x]
                        break
                if not code:
                    notes.append(f"dropped unknown {fd.entity} '{v}'")
                    continue
                parsed.append(code)
            else:
                parsed.append(v)
        if not parsed:
            return None
        if op in ("in", "not_in"):
            return Filter(field=field, op=op, value=parsed)
        if op == "between":
            return Filter(field=field, op=op, value=parsed[:2]) if len(parsed) >= 2 else None
        if len(parsed) > 1 and op == "=":
            return Filter(field=field, op="in", value=parsed)
        return Filter(field=field, op=op, value=parsed[0])

    def _entity(self, etype: str, v: str) -> Optional[str]:
        table = {"wc": self.ents.work_centres, "discipline": self.ents.disciplines,
                 "field": self.ents.fields, "grade": self.ents.grades}[etype]
        if v in table:
            return v
        if v.upper() in table:
            return v.upper()
        if etype == "wc":
            return self.ents.resolve_wc(v)
        if etype == "discipline":
            return self.ents.resolve_discipline(v)
        if etype == "field":
            return self.ents.resolve_field(v)
        gs = self.ents.resolve_grades(v)
        return gs[0] if gs else None

    def _period(self, raw: Dict[str, Any]) -> Optional[Period]:
        fy, lo, hi = raw.get("fy"), raw.get("fy_from"), raw.get("fy_to")
        ok = lambda x: bool(x) and re.fullmatch(r"FY\d{2}", str(x).upper())
        if ok(fy):
            return Period(fy=str(fy).upper())
        if ok(lo) or ok(hi):
            return Period(**{"from": str(lo).upper() if ok(lo) else None, "to": str(hi).upper() if ok(hi) else None})
        return None

    def _fit_to_subject(self, spec: QuerySpec, notes: List[str]) -> QuerySpec:
        """After a metric change, map dimensions/filters to the new subject (e.g. field -> asset)."""
        subject, _, tdef = self._subject_for(spec.metric)
        if subject is None:
            return spec
        from app.brain.compiler import WC_ATTRIBUTE_FIELDS

        def fit(name: str) -> Optional[str]:
            if name in subject.fields or name == "region":
                return name
            if name in WC_ATTRIBUTE_FIELDS and ("wc" in subject.fields or "asset" in subject.fields):
                return name
            if name == "wc" and "asset" in subject.fields:
                return "asset"
            if name == "asset" and "wc" in subject.fields:
                return "wc"
            return subject.dimension_fallbacks.get(name)

        dims, filters = [], []
        for d in spec.dimensions:
            nd = fit(d)
            if nd and nd not in dims:
                dims.append(nd)
            if nd != d:
                notes.append(f"dimension {d} -> {nd}")
        for f in spec.filters:
            nf = fit(f.field)
            if nf:
                filters.append(Filter(field=nf, op=f.op, value=f.value))
            else:
                notes.append(f"filter {f.field} not applicable to {subject.name}")
        data = spec.model_dump(by_alias=True)
        data.update({"dimensions": dims, "filters": [x.model_dump() for x in filters], "domain": subject.domain})
        return QuerySpec.model_validate(data)

    # ------------------------------------------------------------ main
    async def plan(self, question: str, prev: Optional[QuerySpec] = None, history: Optional[List[str]] = None) -> Plan:
        t0 = time.perf_counter()
        question = normalize_asr_query(question)
        prev_subject = self._subject_for(prev.metric)[0] if prev else None
        avail = fiscal_years_for_sql(f"FROM {prev_subject.table}") if prev_subject else []
        fy_hint = resolve_fy(question, available=avail or None)
        try:
            raw = await asyncio.wait_for(self._call(self._prompt(question, prev, history or [], fy_hint)), timeout=12)
        except Exception as e:  # planner failure => try deterministic guards in to_plan first before legacy fallback
            logger.warning(f"planner call failed: {e}")
            det_plan = self.to_plan(question, {}, prev, fy_hint)
            if det_plan.intent in ("data", "replot") and det_plan.spec is not None:
                det_plan.notes.append(f"recovered from llm error via deterministic guard: {str(e)[:80]}")
                det_plan.latency_ms = round((time.perf_counter() - t0) * 1000, 1)
                return det_plan
            return Plan(intent="error", notes=[f"planner error: {str(e)[:120]}"],
                        latency_ms=round((time.perf_counter() - t0) * 1000, 1))
        plan = self.to_plan(question, raw, prev, fy_hint)
        plan.latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        return plan

    def to_plan(self, question: str, raw: Dict[str, Any], prev: Optional[QuerySpec],
                fy_hint: Optional[Dict[str, Any]] = None) -> Plan:
        """Deterministic conversion + guards (unit-testable without the LLM)."""
        question = normalize_asr_query(question)
        intent = raw.get("intent") or "other"
        notes: List[str] = []
        chart = raw.get("chart_kind")
        ql_early = question.lower()
        wants_waterfall = bool(
            re.search(r"\b(waterfall|bridge)\b", ql_early)
            or (
                re.search(r"\b(revenue|income|sales|turnover)\b", ql_early)
                and re.search(r"\b(cost\w*|expense\w*|opex|levies|outflow\w*|deduction\w*|margin\w*|profit|pbt|pat)\b", ql_early)
                and re.search(r"\b(plot\w*|chart\w*|graph\w*|visual\w*|draw|show|display|view|compare)\b", ql_early)
                and not re.search(r"\b(table|tabular)\b", ql_early)
            )
            or (
                re.search(r"\b(plot\w*|chart\w*|graph\w*|visual\w*|draw)\b", ql_early)
                and re.search(r"\b(p\s*&\s*l|pnl|profit\s+and\s+loss|income\s+statement|revenue\s+and\s+cost\w*|revenue\s+vs\s+cost\w*)\b", ql_early)
                and not re.search(r"\b(table|tabular)\b", ql_early)
            )
        )
        if intent == "replot" and prev is not None:
            if prev.metric in ("pnl_statement", "balance_sheet", "cash_flow_statement", "financial_ratios"):
                ck = "waterfall" if wants_waterfall else (chart or "table")
                spec = prev.model_copy(update={"chart_kind": ck})
                return Plan(intent="data", is_followup=True, spec=spec, patch=SpecPatch(chart_kind=ck), chart_kind=ck, raw=raw)
            patch = SpecPatch(chart_kind=chart or "table")
            return Plan(intent="replot", is_followup=True, spec=prev, patch=patch, chart_kind=patch.chart_kind, raw=raw)
        no_sub_entity = (
            not self.ents.resolve_wcs(question)
            and not self.ents.resolve_field(question)
            and not re.search(r"\b(field|fields|basin|basins)\b", ql_early)
        )
        is_corp_bs_stmt = bool(
            re.search(r"\b(balance\s+sheet\w*|statement\s+of\s+financial\s+position|assets\s+and\s+liabilities|equity\s+and\s+liabilities)\b", ql_early)
            and no_sub_entity
        )
        is_corp_cf_stmt = bool(
            re.search(r"\b(cash\s*flow\s+statement\w*|statement\s+of\s+cash\s*flows|ind[- ]?as\s*7|cash\s*flow\s+bridge|cash\s*flow\s+waterfall)\b", ql_early)
            and no_sub_entity
        )
        is_corp_ratios_stmt = bool(
            re.search(r"\b(financial\s+ratios|key\s+ratios|ratio\s+analysis|ratios\s+scorecard|credit\s+ratios|solvency\s+ratios|return\s+ratios)\b", ql_early)
            and no_sub_entity
        )
        is_generic_fin_stmt = bool(
            re.search(r"\b(financial\s+statement\w*|annual\s+statement\w*|annual\s+report\s+statement\w*)\b", ql_early)
            and not re.search(r"\b(p\s*&\s*l|pnl|profit\s+and\s+loss|income\s+statement\w*|balance\s+sheet\w*|cash\s*flow\w*)\b", ql_early)
            and no_sub_entity
        )
        is_rev_cost_bridge = bool(
            re.search(r"\b(revenue|income|sales|turnover)\b", ql_early)
            and re.search(r"\b(cost\w*|expense\w*|opex|levies|outflow\w*)\b", ql_early)
            and no_sub_entity
            and not re.search(r"\b(asset|assets)\b", ql_early)
        )
        is_corp_pnl_stmt = bool(
            (
                re.search(r"\b(p\s*&\s*l|pnl|profit\s+and\s+loss|income\s+statement\w*|financial\s+statement\w*|annual\s+statement\w*|schedule\s+iii)\b", ql_early)
                or is_rev_cost_bridge
            )
            and no_sub_entity
            and not is_corp_bs_stmt
            and not is_corp_cf_stmt
            and not is_corp_ratios_stmt
            and not re.search(r"\b(asset|assets)\b", ql_early)
        )
        if is_corp_bs_stmt:
            intent = "data"
            raw = dict(raw, intent="data", metric="balance_sheet", is_followup=False, dimensions=[])
            if not wants_waterfall and chart not in ("bar", "hbar", "line"):
                chart = "table"
        elif is_corp_cf_stmt:
            intent = "data"
            raw = dict(raw, intent="data", metric="cash_flow_statement", is_followup=False, dimensions=[])
            chart = "waterfall" if wants_waterfall else "table"
        elif is_corp_ratios_stmt:
            intent = "data"
            raw = dict(raw, intent="data", metric="financial_ratios", is_followup=False, dimensions=[])
            chart = "table"
        elif is_corp_pnl_stmt:
            intent = "data"
            raw = dict(raw, intent="data", metric="pnl_statement", is_followup=False, dimensions=[])
            if is_generic_fin_stmt:
                notes.append("ambiguous_financial_statement")
                chart = "waterfall" if re.search(r"\b(waterfall|bridge)\b", ql_early) else "table"
            elif wants_waterfall or is_rev_cost_bridge:
                chart = "waterfall"
            else:
                chart = "table"
        elif wants_waterfall and prev is not None and prev.metric in ("pnl_statement", "cash_flow_statement"):
            spec = prev.model_copy(update={"chart_kind": "waterfall"})
            return Plan(intent="data", is_followup=True, spec=spec, patch=SpecPatch(chart_kind="waterfall"), chart_kind="waterfall", raw=raw)

        # Deterministic Financial Causal & Action Guard ("Why did X happen?", "What action should the Finance Director take?")
        fin_kw = re.search(
            r"\b(pat|profit|pbt|revenue|ebitda|levies|royalty|oidb|saed|windfall|exploration|dry\s+well|survey\s+cost|"
            r"dd&a|dda|depreciation|depletion|impairment|115baa|deferred\s+tax|cwip|opal|hpcl|mrpl|ovl|otpc|subsidiar\w*|"
            r"borrowing\w*|debt|net\s+debt|lease\s+liabilit\w*|ind[- ]?as|abandonment|aro|site\s+restoration|"
            r"cash\s*flow|ocf|fcf|free\s+cash|capex|dividend\w*|buyback|roce|roe|roa|margin\w*|realisation|crude|gas|"
            r"lifting\s+cost|pec|new\s+well\s+gas|nwng|note\s+\d+|finance\s+director|director\s+finance)\b",
            ql_early,
        )
        prev_is_fin = bool(prev is not None and prev.metric in ("pnl_statement", "balance_sheet", "cash_flow_statement", "financial_ratios"))
        if not prev_is_fin and prev is not None:
            psubj, _, ptdef = self._subject_for(prev.metric)
            prev_is_fin = bool((psubj and psubj.domain == "finance") or (ptdef and ptdef.domain == "finance"))
        if (intent != "data" or not raw.get("metric")) and (fin_kw or (prev_is_fin and re.search(r"\b(why|what\s+happened|action|recommend\w*|interven\w*|improv\w*|explain|driver\w*|reason\w*|cause\w*|how)\b", ql_early))):
            inferred_m = raw.get("metric")
            if not inferred_m or not any(self._subject_for(inferred_m)):
                if re.search(r"\b(saed|windfall|statutory\s+levies|note\s+28|note\s+26)\b", ql_early):
                    inferred_m = "statutory_levies_cr"
                elif re.search(r"\b(exploration|dry\s+well\w*|note\s+32)\b", ql_early):
                    inferred_m = "exploration_costs_written_off_cr"
                elif re.search(r"\b(dd&a|dda|depletion|depreciation|note\s+33|note\s+30)\b", ql_early):
                    inferred_m = "dda_cr"
                elif re.search(r"\b(opal|hpcl|mrpl|ovl|otpc|subsidiar\w*)\b", ql_early) and re.search(r"\b(investment\w*|ccd|note\s+10|note\s+8|stake|buyout|acqui\w*)\b", ql_early):
                    inferred_m = "investments_subsidiaries_jv_cr"
                elif re.search(r"\b(opal|hpcl|mrpl|ovl|otpc|subsidiar\w*)\b", ql_early):
                    inferred_m = "subsidiary_pat_cr"
                elif re.search(r"\b(borrowing\w*|debt|net\s+debt|note\s+21|note\s+16)\b", ql_early):
                    inferred_m = "total_debt_cr"
                elif re.search(r"\b(lease\s+liabilit\w*|ind[- ]?as\s*116|note\s+21a|note\s+17)\b", ql_early):
                    inferred_m = "lease_liabilities_cr"
                elif re.search(r"\b(abandonment|aro|site\s+restoration|decommission\w*|note\s+22|note\s+11|note\s+18)\b", ql_early):
                    inferred_m = "abandonment_provision_cr"
                elif re.search(r"\b(cwip|work[- ]in[- ]progress|note\s+7|note\s+6)\b", ql_early):
                    inferred_m = "cwip_cr"
                elif re.search(r"\b(free\s+cash\s+flow|fcf|operating\s+cash\s+flow|ocf|cash\s*flow)\b", ql_early):
                    inferred_m = "cash_flow_statement"
                elif re.search(r"\b(roce|roe|roa|current\s+ratio|interest\s+coverage|debt[- ]to[- ]equity|eps|ratio\w*)\b", ql_early):
                    inferred_m = "financial_ratios"
                elif re.search(r"\b(lifting\s+cost)\b", ql_early):
                    inferred_m = "lifting_cost_usd_per_boe"
                elif re.search(r"\b(loss[- ]making\s+field\w*|pec|field\s+profit\w*)\b", ql_early):
                    inferred_m = "pbt_cr"
                elif prev_is_fin and prev is not None:
                    inferred_m = prev.metric
                else:
                    inferred_m = "pnl_statement"
            intent = "data"
            raw = dict(raw, intent="data", metric=inferred_m, is_followup=bool(prev_is_fin and inferred_m == (prev.metric if prev else None)))

        # SPEC-06 §4.3 / BUG-28: deterministic entry / starting pay scale guard -> pay_scale_min_inr
        is_entry_pay = bool(
            re.search(
                r"\b(starting\s+(?:basic\s+)?(?:pay|salary|scale)|entry[- ]?(?:level\s+)?(?:basic\s+)?(?:pay|salary|scale)|"
                r"minimum\s+(?:basic\s+)?(?:pay|scale)|get\s+on\s+joining|joining\s+pay|pay\s+scale\s+of\s+e[1-9])\b",
                ql_early,
            )
        )
        if is_entry_pay and (intent != "data" or not raw.get("metric")):
            g_match = re.search(r"\b(e[1-9])\b", ql_early, re.I)
            f_list = list(raw.get("filters") or [])
            if g_match and not any(f.get("field") == "grade" for f in f_list if isinstance(f, dict)):
                f_list.append({"field": "grade", "op": "=", "values": [g_match.group(1).upper()]})
            intent = "data"
            raw = dict(raw, intent="data", metric="pay_scale_min_inr", is_followup=False, dimensions=["grade"], filters=f_list)

        # SPEC-06 §4.5: possessive first-person ("my", "mera/meri", "मेरा/मेरी") + HR entity -> self_scope=True
        is_self_hr = bool(
            re.search(
                r"(?:(?<![a-z])(?:my|mine|myself|mera|meri|mere|i\s+have\s+been|have\s+i\s+been)(?![a-z])|(?:मेरा|मेरी|मेरे))"
                r".*?"
                r"(?:(?<![a-z])(?:salary|payslip|pay\s*slip|pay\s+components|pay\s+scale|ctc|basic\s*pay|da|hra|prp|"
                r"leave|el|cl|hpl|balance|posting|postings|posted|tenure|station|transfer|apar|rating|ratings|score|appraisal|"
                r"entitlement|entitlements|advance|advances|medical|reimbursement)(?![a-z])|"
                r"(?:वेतन|सैलरी|छुट्टी|पोस्टिंग|स्थानांतरण|एपार|पात्रता))",
                question,
                re.I,
            )
        )
        if is_self_hr:
            raw = dict(raw, self_scope=True)
            if intent != "data" or not raw.get("metric"):
                intent = "data"
                raw = dict(raw, intent="data", metric="headcount", grain="row", is_followup=False, dimensions=[], filters=[])

        if intent != "data":
            return Plan(intent=intent, raw=raw)

        is_fu = bool(raw.get("is_followup")) and prev is not None
        metric = raw.get("metric") or (prev.metric if is_fu else None)
        subject, mdef, tdef = self._subject_for(metric) if metric else (None, None, None)
        if metric and not (mdef or tdef):
            if is_fu:
                metric = prev.metric
                subject, mdef, tdef = self._subject_for(metric)
            else:
                return Plan(intent="other", notes=[f"unknown metric {metric}"], raw=raw)
        if not metric:
            return Plan(intent="other", notes=["no metric"], raw=raw)

        filters = [f for f in (self._coerce_filter(x, subject, notes) for x in raw.get("filters") or []) if f]
        from app.brain.compiler import WC_ATTRIBUTE_FIELDS
        if any(f.field in ("wc", "asset") for f in filters):
            # A named work centre makes state/sector/city filters redundant (and often wrong).
            dropped_attr = [f.field for f in filters if f.field in WC_ATTRIBUTE_FIELDS and subject is not None
                            and f.field not in subject.fields]
            filters = [f for f in filters if f.field not in dropped_attr]
            if dropped_attr:
                notes.append(f"dropped redundant {dropped_attr}")
        dims = []
        for d in raw.get("dimensions") or []:
            d = DIM_ALIASES.get(d, d) if subject is not None and d not in subject.fields else d
            if subject is not None and d not in subject.fields:
                if d == "wc" and "asset" in subject.fields:
                    d = "asset"
                elif d == "asset" and "wc" in subject.fields:
                    d = "wc"
                elif d in subject.dimension_fallbacks:
                    d = subject.dimension_fallbacks[d]
                else:
                    notes.append(f"dropped dimension {d}")
                    continue
            if d not in dims:
                dims.append(d)
        period = self._period(raw)
        # Deterministic FY guard (D-30): an explicit time phrase in the question wins.
        if fy_hint:
            period = Period(fy=fy_hint["fy"]) if fy_hint.get("fy") else Period(**{"from": fy_hint.get("from"), "to": fy_hint.get("to")})
        grain = raw.get("grain")
        sort = Sort(by=raw["sort_by"], dir=raw.get("sort_dir") or "desc") if raw.get("sort_by") else None
        limit = raw.get("limit") if isinstance(raw.get("limit"), int) and raw.get("limit") > 0 else None

        # Entity guard: a single work centre named in the question but missing from the plan.
        if wants_waterfall:
            chart = "waterfall"
        wc_field = None
        if subject is not None:
            wc_field = "wc" if "wc" in subject.fields else ("asset" if "asset" in subject.fields else None)
        named_wcs = self.ents.resolve_wcs(question)
        has_wc = any(f.field in ("wc", "asset", "region") for f in filters) or bool(raw.get("compare_field"))
        if wc_field and len(named_wcs) == 1 and not has_wc and not self.ents.resolve_region(question):
            filters.append(Filter(field=wc_field, op="=", value=named_wcs[0]))
            notes.append(f"entity guard added {wc_field}={named_wcs[0]}")

        # Entity guard (multi): "Compare Delhi and Mumbai" named as states/cities instead of work centres.
        if wc_field and len(named_wcs) >= 2 and not any(f.field in ("wc", "asset") for f in filters) \
                and not raw.get("compare_field") and not self.ents.resolve_region(question):
            filters = [f for f in filters if f.field not in WC_ATTRIBUTE_FIELDS or f.field in subject.fields]
            raw = dict(raw, compare_field=wc_field, compare_values=named_wcs[:4])
            notes.append(f"entity guard: compare {wc_field} {named_wcs[:4]}")

        # Deterministic shape guards (golden-set findings):
        # (a) one work centre named, but the plan expanded it to every work centre in that city.
        if len(named_wcs) == 1:
            for i, f in enumerate(filters):
                if f.field in ("wc", "asset") and f.op == "in" and isinstance(f.value, list) \
                        and named_wcs[0] in f.value and len(f.value) > 4:
                    filters[i] = Filter(field=f.field, op="=", value=named_wcs[0])
        # (b) years at a place are station tenure unless total service is asked for.
        ql = question.lower()
        if named_wcs and not re.search(r"\b(service|with ongc|in ongc|of service|career|joined|total tenure|total)\b", ql):
            filters = [Filter(field="station_tenure_years", op=f.op, value=f.value)
                       if f.field == "total_tenure_years" and subject is not None and "station_tenure_years" in subject.fields
                       else f for f in filters]
        # (c) "which fields / assets / disciplines ..." asks for a ranking by that entity.
        if not dims and subject is not None and not is_fu and grain != "row":
            for word, d in (("fields", "field"), ("assets", "asset"), ("work centres", "wc"), ("disciplines", "discipline"),
                            ("grades", "grade")):
                if re.search(rf"\b(which|what|top|bottom|list)\b.*\b{word}\b", ql):
                    d2 = d if d in subject.fields else ("wc" if d == "asset" and "wc" in subject.fields else
                                                        ("asset" if d == "wc" and "asset" in subject.fields else None))
                    if d2:
                        dims = [d2]
                        notes.append(f"shape guard: dimension {d2}")
                    break

        # (d) trend/history/profile wording over a period range, or a multi-year period with no other dimension => year-by-year breakdown.
        trend_q = re.search(
            r"\b(trend|increas\w*|decreas\w*|declin\w*|grew|grown|growth|changed|year[- ]by[- ]year|"
            r"over time|each year|every year|annual|yoy|year[- ]on[- ]year|by (?:fiscal |financial )?year|year[- ]?wise|"
            r"per year|yearly|fy[- ]?wise|history|historical|profile|trajectory|evolution|series)\b",
            ql,
        )
        multi_yr = bool(period is not None and period.from_ and period.to and period.from_ != period.to)
        non_fy_dims = [d for d in dims if d != "fy"]
        cumulative_only = bool(re.search(r"\b(cumulative|combined total|grand total)\b", ql) and not trend_q)
        if subject is not None and "fy" in subject.fields and (period is not None and (period.from_ or period.to)):
            if trend_q or (multi_yr and not non_fy_dims and not cumulative_only):
                if "fy" not in dims:
                    if is_fu:
                        if raw.get("set_dimensions"):
                            dims = dims + ["fy"]
                        else:
                            raw = dict(raw, set_dimensions=True)
                            dims = [d for d in (prev.dimensions if prev else []) if d in subject.fields] + ["fy"]
                    else:
                        dims = dims + ["fy"]
                    notes.append("shape guard: trend/multi-year -> dimension fy")
                elif is_fu and not raw.get("set_dimensions"):
                    raw = dict(raw, set_dimensions=True)
                    base_dims = [d for d in (prev.dimensions if prev else []) if d in subject.fields and d != "fy"]
                    dims = base_dims + [d for d in dims if d not in base_dims]
        # (d2) a year-by-year breakdown only when the question asks for a trend/history/profile or is a multi-year series with no other grouping.
        keep_fy = bool(trend_q or (multi_yr and not non_fy_dims and not cumulative_only) or (is_fu and prev and "fy" in prev.dimensions))
        if "fy" in dims and not keep_fy:
            dims = [d for d in dims if d != "fy"]
            notes.append("shape guard: dropped fy dimension (no trend asked)")
        # (e) retention-rate style share metric is computed over everyone: drop a carried tenure filter.
        if metric == "long_stay_share_pct":
            raw = dict(raw, remove_filters=list(set((raw.get("remove_filters") or []) + ["station_tenure_years", "grade"])))
            filters = [f for f in filters if f.field not in ("station_tenure_years",)]
        # (f) "top N fields" / "most profitable fields" / "all fields" without "loss" drops a carried pbt_cr < 0 filter.
        if re.search(r"\b(top\s+\d+|most\s+profitable|all\s+fields)\b", ql) and not re.search(r"\bloss", ql):
            raw = dict(raw, remove_filters=list(set((raw.get("remove_filters") or []) + ["pbt_cr"])))
            filters = [f for f in filters if f.field != "pbt_cr"]

        compare = None
        if raw.get("compare_field") and raw.get("compare_values"):
            cf = raw["compare_field"]
            if subject is not None and cf not in subject.fields:
                cf = subject.dimension_fallbacks.get(cf, cf)
            fd = subject.fields.get(cf) if subject is not None else None
            if fd is not None:
                new_vals = []
                for v in raw["compare_values"]:
                    code = self._entity(fd.entity, str(v)) if fd.entity else str(v)
                    if code and code not in new_vals:
                        new_vals.append(code)
                if cf == "field" and len(new_vals) < len(raw["compare_values"]) and subject is not None and "asset" in subject.fields and len(named_wcs) >= 2:
                    cf = "asset"
                    fd = subject.fields.get("asset")
                    new_vals = list(dict.fromkeys(named_wcs[:4]))
                    dims = ["asset" if d == "field" else d for d in dims]
                base = []
                src = prev if is_fu else None
                cur = src.filter_on(cf) if src is not None else None
                if cur is not None:
                    base = cur.value if isinstance(cur.value, list) else [cur.value]
                for f in filters:
                    if f.field == cf:
                        base += f.value if isinstance(f.value, list) else [f.value]
                vals = list(dict.fromkeys(base + new_vals))
                filters = [f for f in filters if f.field != cf]
                if len(vals) >= 2:
                    compare = Compare(field=cf, values=vals[:4])
                elif vals:
                    filters.append(Filter(field=cf, op="=", value=vals[0]))

        if is_fu:
            patch = SpecPatch(
                add_filters=filters,
                remove_filters=[r for r in raw.get("remove_filters") or [] if isinstance(r, str)],
                dimensions=dims if (raw.get("set_dimensions") or bool(dims)) else None,
                period=period if (period and (fy_hint or raw.get("fy") or raw.get("fy_from") or raw.get("fy_to"))) else None,
                grain=grain if grain and grain != prev.grain else None,
                metric=metric if metric != prev.metric else None,
                sort=sort, limit=limit, chart_kind=chart, compare=compare,
            )
            if patch.dimensions and prev.grain == "row" and patch.grain is None:
                patch.grain = "aggregate"  # "by discipline" after a names list returns to counts
            spec = self._fit_to_subject(apply_patch(prev, patch), notes)
            return Plan(intent="data", is_followup=True, spec=spec, patch=patch, chart_kind=chart, notes=notes, raw=raw)

        is_self_scope = bool(raw.get("self_scope"))
        if is_self_scope:
            filters = [f for f in filters if f.field != "wc"]
            grain = "row"
        spec = QuerySpec(domain=(subject.domain if subject else (tdef.domain if tdef else None)), metric=metric,
                         dimensions=[] if is_self_scope else dims, filters=filters, period=period,
                         grain=grain or "aggregate", sort=sort, limit=limit, self_scope=is_self_scope)
        if compare:
            spec = apply_patch(spec, SpecPatch(compare=compare))
        return Plan(intent="data", is_followup=False, spec=spec, chart_kind=chart, notes=notes, raw=raw)


_PLANNER: Optional[Planner] = None


def get_planner() -> Planner:
    global _PLANNER
    if _PLANNER is None:
        _PLANNER = Planner()
    return _PLANNER
