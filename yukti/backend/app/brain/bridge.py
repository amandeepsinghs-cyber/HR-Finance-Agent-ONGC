"""Signed P&L waterfall bridge builder (SPEC-09 §4.3; BUG-08, BUG-09, BUG-22).

Python twin of `yukti/frontend/src/charts/bridge.ts`. Both implementations read the same
single source of truth (`yukti/contracts/statement_line_classes.json`) and are tested against
the shared fixtures in `yukti/contracts/fixtures/bridge/`.

The bridge starts at reported Revenue from Operations, applies every intermediate line with its
accounting sign (`add` -> `+value`, `deduct` -> `-abs(value)`, `signed` -> `value`), asserts each
reported subtotal on the way within ₹0.5 cr, and asserts that the running total lands on reported
PAT within ₹0.5 cr. Anything else returns a `BridgeError` — never fabricated EBITDA, DD&A, or
"OPEX & Levies".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, Union
import yaml

BridgeClass = Literal["start", "add", "deduct", "signed", "subtotal", "end", "skip"]
BridgeErrorCode = Literal[
    "missing_start",
    "missing_end",
    "subtotal_mismatch",
    "pat_mismatch",
    "single_value",
]

_CONTRACTS_DIR = Path(__file__).resolve().parents[3] / "contracts"
_CLASSES_PATH = _CONTRACTS_DIR / "statement_line_classes.json"
_COPY_PATH = Path(__file__).resolve().parent / "bridge_copy.yaml"


@lru_cache(maxsize=1)
def _load_classes_cfg() -> Dict[str, Any]:
    with _CLASSES_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def _load_copy_cfg() -> Dict[str, Any]:
    if not _COPY_PATH.exists():
        return {}
    with _COPY_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


BRIDGE_TOLERANCE_CR: float = float(_load_classes_cfg().get("tolerance_inr_cr", 0.5))


def _round2(n: float) -> float:
    return round(float(n) + 1e-12, 2)


def bridge_class_of(line_code: Optional[str]) -> Optional[BridgeClass]:
    """Return the bridge class for a statement `line_code`, or None if unknown."""
    if not line_code:
        return None
    cfg = _load_classes_cfg()
    cls = (cfg.get("classes") or {}).get(str(line_code))
    return cls  # type: ignore[return-value]


@dataclass
class BridgeBar:
    """A single bar in a signed P&L waterfall bridge."""

    label: str
    value: float
    type: Literal["total", "delta"]
    line_code: Optional[str] = None
    merged: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "label": self.label,
            "value": self.value,
            "type": self.type,
        }
        if self.line_code is not None:
            out["line_code"] = self.line_code
        if self.merged:
            out["merged"] = list(self.merged)
        return out

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)


# Alias for SPEC-09 / packet references
BridgeRow = BridgeBar


@dataclass
class BridgeOk:
    """Successful signed P&L waterfall bridge."""

    ok: Literal[True] = True
    period: str = ""
    unit: str = "₹ Cr"
    bars: List[BridgeBar] = field(default_factory=list)
    residual: float = 0.0

    @property
    def rows(self) -> List[BridgeBar]:
        return self.bars

    @property
    def start_value(self) -> float:
        return self.bars[0].value if self.bars else 0.0

    @property
    def end_value(self) -> float:
        return self.bars[-1].value if self.bars else 0.0

    def default_title(self) -> str:
        rev_s = f"{self.start_value:,.0f}"
        pat_s = f"{self.end_value:,.0f}"
        prefix = f"{self.period}: " if self.period else ""
        return f"{prefix}₹{rev_s} cr revenue to ₹{pat_s} cr PAT"

    def to_chart_rows(self) -> List[Dict[str, Any]]:
        return bridge_chart_rows(self)

    def to_chart_spec(self, title: Optional[str] = None) -> Dict[str, Any]:
        """Build the AnswerContract `visual.chart` specification for this bridge."""
        data = bridge_chart_rows(self)
        return {
            "kind": "waterfall",
            "title": title or self.default_title(),
            "x": "step",
            "y": "amount_cr",
            "category": "step",
            "value": "amount_cr",
            "unit": self.unit,
            "sort": "none",
            "bridge_version": "v3",
            "period": self.period,
            "data": data,
        }

    def spoken_summary(self, lang: str = "en") -> str:
        copy = (_load_copy_cfg().get("success") or {}).get("bridge") or {}
        lang_key = "hi" if lang == "hi" else ("hi_en" if lang == "hi-en" else "en")
        tmpl = copy.get(lang_key) or copy.get("en") or (
            "Here is the {period} P&L waterfall bridge from ₹{rev} crore revenue to ₹{pat} crore PAT."
        )
        return tmpl.format(
            period=self.period or "current period",
            rev=f"{self.start_value:,.2f}".rstrip("0").rstrip("."),
            pat=f"{self.end_value:,.2f}".rstrip("0").rstrip("."),
        )


@dataclass
class BridgeError:
    """Honest refusal when a statement or KPI cannot be bridged (SPEC-09 §4.3 step 6)."""

    ok: Literal[False] = False
    code: BridgeErrorCode = "single_value"
    reason: str = ""

    def message(self, lang: str = "en") -> str:
        return bridge_error_copy(self, lang=lang)

    def suggestion(self, lang: str = "en", entity: Optional[str] = None) -> Optional[str]:
        if self.code != "single_value":
            return None
        err_cfg = ((_load_copy_cfg().get("errors") or {}).get("single_value")) or {}
        is_hi = lang == "hi"
        if entity:
            tmpl = err_cfg.get("suggestion_hi" if is_hi else "suggestion_en")
            if tmpl:
                return tmpl.format(entity=entity)
        return err_cfg.get("suggestion_default_hi" if is_hi else "suggestion_default_en")


BridgeResult = Union[BridgeOk, BridgeError]


def single_value_error() -> BridgeError:
    """A single KPI / one-row visual can never be bridged (BEH-04.13, BEH-07.34)."""
    return BridgeError(
        ok=False,
        code="single_value",
        reason="a single value cannot be shown as a bridge",
    )


def bridge_error_copy(err: BridgeError, lang: str = "en") -> str:
    """Honest user-facing copy for a BridgeError (SPEC-09 §4.3 step 6; EN + HI)."""
    errors_cfg = _load_copy_cfg().get("errors") or {}
    entry = errors_cfg.get(err.code) or {}
    lang_key = "hi" if lang == "hi" else ("hi_en" if lang == "hi-en" else "en")
    tmpl = entry.get(lang_key) or entry.get("en")
    if tmpl:
        return tmpl.format(reason=err.reason)
    if lang == "hi":
        return f"इन पंक्तियों से विश्वसनीय वॉटरफॉल ब्रिज नहीं बनाया जा सकता ({err.reason})। यहाँ विवरण तालिका है।"
    return f"I can't build a reliable bridge from these lines ({err.reason}). Here is the statement table."


_KIND_FRIENDLY_EN: Dict[str, str] = {
    "pie": "pie chart",
    "donut": "donut chart",
    "histogram": "histogram distribution",
    "hbar": "horizontal ranked bar chart",
    "bar": "vertical bar chart",
    "stacked_bar": "stacked bar chart",
    "line": "line trend chart",
    "area": "area chart",
    "scatter": "scatter plot",
    "treemap": "hierarchical treemap",
    "heatmap": "heatmap matrix",
    "waterfall": "waterfall bridge chart",
    "table": "data table",
}

_KIND_FRIENDLY_HI: Dict[str, str] = {
    "pie": "पाई चार्ट",
    "donut": "डोनट चार्ट",
    "histogram": "हिस्टोग्राम",
    "hbar": "क्षैतिज बार चार्ट",
    "bar": "कॉलम चार्ट",
    "line": "रेखा चार्ट",
    "waterfall": "वॉटरफॉल चार्ट",
    "table": "डेटा तालिका",
}


def no_visual_copy(kind: str, lang: str = "en") -> str:
    """Honest refusal copy when there is no visual on screen to re-plot (from bridge_copy.yaml)."""
    errors_cfg = _load_copy_cfg().get("errors") or {}
    entry = errors_cfg.get("no_visual") or {}
    lang_key = "hi" if lang == "hi" else ("hi_en" if lang == "hi-en" else "en")
    tmpl = entry.get(lang_key) or entry.get("en")
    if tmpl:
        return tmpl.format(kind=kind)
    if lang == "hi":
        return f"स्क्रीन पर अभी कोई डेटा उपलब्ध नहीं है जिसे {kind} में बदला जा सके। कृपया पहले कोई डेटा प्रश्न पूछें।"
    return (
        f"There is no chartable dataset on screen yet to re-plot as a {kind}. "
        "Ask a data question first, and then I can switch the chart view."
    )


def replot_success_copy(kind: str, lang: str = "en") -> str:
    """Confirmation copy when a re-plot visual has been produced (from bridge_copy.yaml)."""
    success_cfg = _load_copy_cfg().get("success") or {}
    entry = success_cfg.get("replot") or {}
    lang_key = "hi" if lang == "hi" else ("hi_en" if lang == "hi-en" else "en")
    en_label = _KIND_FRIENDLY_EN.get(kind, f"{kind} view")
    kind_label = _KIND_FRIENDLY_HI.get(kind, en_label) if lang == "hi" else en_label
    tmpl = entry.get(lang_key) or entry.get("en")
    if tmpl:
        return tmpl.format(kind_label=kind_label)
    if lang == "hi":
        return f"मैंने वर्तमान डेटा को स्क्रीन पर {kind_label} के रूप में प्रदर्शित कर दिया है।"
    return f"I've replotted the current data as a {kind_label} on screen."


def which_year_copy(periods: Sequence[str], lang: str = "en") -> str:
    """Clarification copy when a waterfall bridge is requested on a multi-period statement (BEH-04.12)."""
    errors_cfg = _load_copy_cfg().get("errors") or {}
    entry = errors_cfg.get("which_year") or {}
    lang_key = "hi" if lang == "hi" else ("hi_en" if lang == "hi-en" else "en")
    periods_str = ", ".join(str(p) for p in periods if p) or "FY26, FY25"
    tmpl = entry.get(lang_key) or entry.get("en")
    if tmpl:
        return tmpl.format(periods=periods_str)
    if lang == "hi":
        return f"आप किस वित्तीय वर्ष का वॉटरफॉल ब्रिज देखना चाहेंगे? कृपया वर्ष चुनें ({periods_str})।"
    return f"Which year would you like to see as a waterfall bridge? Please pick a year ({periods_str})."


def bridge_chart_rows(res: BridgeOk) -> List[Dict[str, Any]]:
    """Convert `BridgeOk.bars` to typed chart rows understood by `waterfallOption`."""
    rows: List[Dict[str, Any]] = []
    for b in res.bars:
        row: Dict[str, Any] = {
            "step": b.label,
            "label": b.label,
            "amount_cr": b.value,
            "value": b.value,
            "type": b.type,
        }
        if b.line_code is not None:
            row["line_code"] = b.line_code
        if b.merged:
            row["merged"] = list(b.merged)
        rows.append(row)
    return rows


def _extract_rows_and_period(
    statement_or_rows: Any,
    period: Optional[str],
) -> tuple[List[Dict[str, Any]], Optional[str], bool]:
    """Extract `(rows, effective_period, force_single_value)` from statement visual, fixture, or row list."""
    if statement_or_rows is None:
        return [], period, True

    if isinstance(statement_or_rows, dict):
        vtype = str(statement_or_rows.get("visual_type") or statement_or_rows.get("type") or "").lower()
        if vtype == "kpi":
            return list(statement_or_rows.get("rows") or []), period, True

        inner = statement_or_rows.get("statement")
        if isinstance(inner, dict):
            statement_or_rows = inner

        periods = statement_or_rows.get("periods")
        eff_period = period
        if eff_period is None and isinstance(periods, list) and len(periods) == 1:
            eff_period = str(periods[0])

        sections = statement_or_rows.get("sections")
        if isinstance(sections, list):
            flat: List[Dict[str, Any]] = []
            for sec in sections:
                if isinstance(sec, dict) and isinstance(sec.get("rows"), list):
                    flat.extend(r for r in sec["rows"] if isinstance(r, dict))
            return flat, eff_period, False

        if isinstance(statement_or_rows.get("rows"), list):
            rows_list = [r for r in statement_or_rows["rows"] if isinstance(r, dict)]
            return rows_list, eff_period, len(rows_list) <= 1

        if isinstance(statement_or_rows.get("table"), dict) and isinstance(statement_or_rows["table"].get("rows"), list):
            rows_list = [r for r in statement_or_rows["table"]["rows"] if isinstance(r, dict)]
            return rows_list, eff_period, len(rows_list) <= 1

        return [], eff_period, True

    if isinstance(statement_or_rows, (list, tuple)):
        rows_list = [r for r in statement_or_rows if isinstance(r, dict)]
        eff_period = period
        if eff_period is None:
            for r in rows_list:
                if isinstance(r.get("values"), dict) and len(r["values"]) == 1:
                    eff_period = str(next(iter(r["values"].keys())))
                    break
                if r.get("fiscal_year"):
                    eff_period = str(r["fiscal_year"])
                    break
        return rows_list, eff_period, len(rows_list) <= 1

    return [], period, True


def _value_of(line: Dict[str, Any], period: Optional[str]) -> Optional[float]:
    vals = line.get("values")
    if isinstance(vals, dict):
        if period is not None and period in vals:
            v = vals[period]
        elif period is None and len(vals) == 1:
            v = next(iter(vals.values()))
        else:
            v = None
        if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v)):
            return float(v)
        return None

    for key in ("value", "amount_cr", "amount_inr_cr", "value_inr_cr"):
        v = line.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v)):
            return float(v)
    return None


def _label_of(line: Dict[str, Any]) -> str:
    lbl = line.get("label") or line.get("line_item") or line.get("line_name")
    if isinstance(lbl, str) and lbl.strip():
        return lbl.strip()
    code = line.get("line_code")
    if isinstance(code, str) and code:
        cfg_lines = _load_classes_cfg().get("lines") or {}
        meta = cfg_lines.get(code)
        if isinstance(meta, dict) and meta.get("label"):
            return str(meta["label"])
        return code
    return "Line"


def bridge(
    statement_or_rows: Union[Dict[str, Any], Sequence[Dict[str, Any]], None],
    period: Optional[str] = None,
    granularity: Literal["standard", "full"] = "standard",
) -> BridgeResult:
    """Build the signed P&L waterfall bridge for one period (SPEC-09 §4.3).

    - `granularity="standard"` folds `deduct` lines below 2% of revenue into a single
      `"Other expenses (net)"` delta bar per segment, emitted immediately before the next
      `subtotal`/`end` row (never across a subtotal).
    - `granularity="full"` keeps every non-skip line separate.
    """
    rows, eff_period, is_single = _extract_rows_and_period(statement_or_rows, period)
    if is_single:
        has_start_and_end = (
            any(bridge_class_of(r.get("line_code")) == "start" for r in rows)
            and any(bridge_class_of(r.get("line_code")) == "end" for r in rows)
        )
        if not has_start_and_end:
            return single_value_error()

    classified: List[tuple[Dict[str, Any], BridgeClass, float]] = []
    for r in rows:
        cls = bridge_class_of(r.get("line_code"))
        if not cls or cls == "skip":
            continue
        v = _value_of(r, eff_period)
        if v is None:
            continue
        classified.append((r, cls, v))

    if not classified and len(rows) <= 1:
        return single_value_error()

    start = next((x for x in classified if x[1] == "start"), None)
    if start is None:
        return BridgeError(
            ok=False,
            code="missing_start",
            reason="no start line (Revenue from operations) in the statement",
        )

    end = next((x for x in classified if x[1] == "end"), None)
    if end is None:
        return BridgeError(
            ok=False,
            code="missing_end",
            reason="no end line (PAT / profit for the year) in the statement",
        )

    cfg = _load_classes_cfg()
    tol = float(cfg.get("tolerance_inr_cr", 0.5))
    small_pct = float(cfg.get("small_deduct_threshold_pct_of_revenue", 0.02))
    merged_label = str(cfg.get("merged_deduct_label", "Other expenses (net)"))

    start_r, _, start_v = start
    threshold = abs(start_v) * small_pct
    bars: List[BridgeBar] = [
        BridgeBar(
            label=_label_of(start_r),
            value=float(start_v),
            type="total",
            line_code=start_r.get("line_code"),
        )
    ]
    running = start_v
    pending = 0.0
    pending_codes: List[str] = []

    def flush() -> None:
        nonlocal pending, pending_codes
        if not pending_codes:
            return
        bars.append(
            BridgeBar(
                label=merged_label,
                value=_round2(pending),
                type="delta",
                merged=list(pending_codes),
            )
        )
        pending = 0.0
        pending_codes = []

    started = False
    for r, cls, v in classified:
        if r is start_r and not started:
            started = True
            continue
        if cls in ("add", "deduct", "signed"):
            delta = abs(v) if cls == "add" else (-abs(v) if cls == "deduct" else v)
            running += delta
            if granularity == "standard" and cls == "deduct" and abs(v) < threshold:
                pending += delta
                pending_codes.append(str(r.get("line_code") or _label_of(r)))
            else:
                bars.append(
                    BridgeBar(
                        label=_label_of(r),
                        value=_round2(delta),
                        type="delta",
                        line_code=r.get("line_code"),
                    )
                )
        elif cls in ("subtotal", "end"):
            flush()
            diff = abs(running - v)
            if diff > tol:
                name = _label_of(r)
                code_str = f" ({r.get('line_code')})" if r.get("line_code") else ""
                if cls == "end":
                    return BridgeError(
                        ok=False,
                        code="pat_mismatch",
                        reason=f"lines do not add up to reported PAT ({name}): off by ₹{_round2(diff)} cr",
                    )
                return BridgeError(
                    ok=False,
                    code="subtotal_mismatch",
                    reason=f"lines do not add up to reported subtotal {name}{code_str}: off by ₹{_round2(diff)} cr",
                )
            running = v  # re-anchor on the reported figure to prevent rounding drift
            bars.append(
                BridgeBar(
                    label=_label_of(r),
                    value=float(v),
                    type="total",
                    line_code=r.get("line_code"),
                )
            )
            if cls == "end":
                return BridgeOk(
                    ok=True,
                    period=eff_period or "",
                    unit="₹ Cr",
                    bars=bars,
                    residual=0.0,
                )

    return BridgeError(
        ok=False,
        code="missing_end",
        reason="statement ended before the PAT line",
    )
