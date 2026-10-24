"""Variance-attribution engine (deterministic, pure Python).

Implements YoY variance attribution and PBT bridge decomposition matching
SPEC-08 §6.1, §6.5 and packet P2F.4.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


class BridgeDoesNotClose(Exception):
    """Raised when the sum of PBT bridge impacts does not equal delta PBT within tolerance."""
    pass


@dataclass
class VarianceRow:
    """Row in variance_attribution (SPEC-08 §6.1)."""

    fy_from: str
    fy_to: str
    scope: str
    line_code: str
    delta_inr_cr: float
    component: str
    impact_inr_cr: float
    impact_on_pbt_inr_cr: float
    method: str
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    coverage: str = "full"
    rank: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


@dataclass
class Bridge:
    """PBT/PAT Waterfall Bridge (SPEC-08 §6.1, §6.5)."""

    fy_from: str
    fy_to: str
    scope: str
    start: float
    end: float
    delta: float
    closure_error: float
    rows: List[VarianceRow] = field(default_factory=list)

    @property
    def items(self) -> List[VarianceRow]:
        return self.rows

    def __len__(self) -> int:
        return len(self.rows)

    def __iter__(self):
        return iter(self.rows)

    def __getitem__(self, idx):
        return self.rows[idx]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fy_from": self.fy_from,
            "fy_to": self.fy_to,
            "scope": self.scope,
            "start": self.start,
            "end": self.end,
            "delta": self.delta,
            "closure_error": self.closure_error,
            "rows": [r.to_dict() for r in self.rows],
        }

    def get_impact(self, line_code: str) -> Optional[float]:
        """Look up impact_on_pbt_inr_cr for a given line code or alias."""
        norm_lc = _normalize_line_code(line_code)
        for r in self.rows:
            if _normalize_line_code(r.line_code) == norm_lc or r.line_code == line_code:
                return r.impact_on_pbt_inr_cr
        return None


# Line aliases mapping variants to canonical codes
LINE_ALIASES: Dict[str, str] = {
    "LEVY.OTHER": "LEVY.OTHER_SAED",
    "LEVY.SAED": "LEVY.OTHER_SAED",
    "PL.OPEX": "PL.OPEX_10YR",
    "EXP.OPERATING": "PL.OPEX_10YR",
    "EXP.OPEX": "PL.OPEX_10YR",
    "PL.EXCHANGE_LOSS": "PL.EXCHANGE_LOSS_10YR",
    "EXP.EXCHANGE_LOSS": "PL.EXCHANGE_LOSS_10YR",
    "PL.OTHER_EXP": "PL.OTHER_EXP_10YR",
    "PL.OTHER_EXPENSES": "PL.OTHER_EXP_10YR",
    "EXP.OTHER": "PL.OTHER_EXP_10YR",
    "EXP.EXPLORATION_WRITEOFF": "PL.EXPL_WRITEOFF",
    "PL.EXPLORATION": "PL.EXPL_WRITEOFF",
    "EXP.STATUTORY_LEVIES": "LEVY.TOTAL",
    "PL.STATUTORY_LEVIES": "LEVY.TOTAL",
}

# Cost lines where an increase in cost has a negative impact on PBT
COST_LINE_PREFIXES = (
    "LEVY.",
    "PL.OPEX",
    "PL.EXPL_",
    "PL.PROVISIONS",
    "PL.EXCHANGE_LOSS",
    "PL.OTHER_EXP",
    "PL.DDA",
    "PL.FIN_COST",
    "EXP.",
    "N36.",
    "N37.",
)

# Core 10 drivers in the PBT bridge
PBT_BRIDGE_DRIVERS = [
    ("PL.REV_OPS", ["PL.REV_OPS"]),
    ("PL.OTHER_INCOME", ["PL.OTHER_INCOME"]),
    ("LEVY.TOTAL", ["LEVY.TOTAL", "EXP.STATUTORY_LEVIES"]),
    ("PL.OPEX_10YR", ["PL.OPEX_10YR", "PL.OPEX", "EXP.OPERATING"]),
    ("PL.EXPL_WRITEOFF", ["PL.EXPL_WRITEOFF", "EXP.EXPLORATION_WRITEOFF"]),
    ("PL.PROVISIONS_WRITEOFF", ["PL.PROVISIONS_WRITEOFF"]),
    ("PL.EXCHANGE_LOSS_10YR", ["PL.EXCHANGE_LOSS_10YR", "PL.EXCHANGE_LOSS", "EXP.EXCHANGE_LOSS"]),
    ("PL.OTHER_EXP_10YR", ["PL.OTHER_EXP_10YR", "PL.OTHER_EXP", "PL.OTHER_EXPENSES"]),
    ("PL.DDA", ["PL.DDA"]),
    ("PL.FIN_COST", ["PL.FIN_COST"]),
]


def _normalize_line_code(line_code: str) -> str:
    """Normalize line code using known aliases."""
    lc = line_code.strip()
    return LINE_ALIASES.get(lc, lc)


def _is_cost_line(line_code: str) -> bool:
    """Return True if line is a cost line whose increase reduces PBT."""
    norm = _normalize_line_code(line_code)
    return any(norm.startswith(p) for p in COST_LINE_PREFIXES)


def _prev_fy(fy: str) -> str:
    """Compute default previous fiscal year from fy (e.g. FY26 -> FY25)."""
    fy_str = fy.strip()
    if fy_str.upper().startswith("FY") and fy_str[2:].isdigit():
        num = int(fy_str[2:])
        width = len(fy_str[2:])
        return f"FY{num - 1:0{width}d}"
    if fy_str.isdigit():
        return str(int(fy_str) - 1)
    return fy_str


def _lookup_row(
    df: pd.DataFrame,
    line_codes: List[str] | str,
    fy: str,
    scope: str = "standalone",
) -> Tuple[Optional[float], Optional[Dict[str, Any]]]:
    """Look up verified value and lineage for a line_code and fiscal year."""
    if isinstance(line_codes, str):
        line_codes = [line_codes]

    # Expand aliases
    expanded_codes: List[str] = []
    for lc in line_codes:
        expanded_codes.append(lc)
        norm = _normalize_line_code(lc)
        if norm not in expanded_codes:
            expanded_codes.append(norm)
        for k, v in LINE_ALIASES.items():
            if v == lc and k not in expanded_codes:
                expanded_codes.append(k)

    sub = df
    if "scope" in sub.columns:
        sub = sub[sub["scope"] == scope]
    if "period_type" in sub.columns:
        sub = sub[sub["period_type"] == "annual"]
    if "verified" in sub.columns:
        sub = sub[sub["verified"] == True]
    if "is_latest_vintage" in sub.columns:
        sub = sub[sub["is_latest_vintage"] == True]

    fy_col = "fiscal_year" if "fiscal_year" in sub.columns else ("fy" if "fy" in sub.columns else None)
    if fy_col and not sub.empty:
        sub = sub[sub[fy_col].astype(str).str.upper() == fy.upper()]

    lc_col = "line_code" if "line_code" in sub.columns else None
    if not lc_col or sub.empty:
        return None, None

    for lc in expanded_codes:
        match = sub[sub[lc_col] == lc]
        if not match.empty:
            row = match.iloc[0]
            val: Optional[float] = None
            for col in ("value_inr_cr", "value", "value_native"):
                if col in row and pd.notna(row[col]):
                    val = float(row[col])
                    break

            if val is not None:
                src_doc = str(row.get("source_doc", "")).strip() if pd.notna(row.get("source_doc")) else ""
                src_page = (
                    str(row.get("source_page_label", row.get("source_page", ""))).strip()
                    if pd.notna(row.get("source_page_label", row.get("source_page", "")))
                    else ""
                )
                src = f"{src_doc} {src_page}".strip()
                lineage = {
                    "line_code": lc,
                    "fy": fy,
                    "value": val,
                    "source": src,
                }
                return val, lineage

    return None, None


def attribute(
    df: pd.DataFrame,
    line_code: str,
    fy_to: str,
    fy_from: Optional[str] = None,
    scope: str = "standalone",
) -> List[VarianceRow]:
    """Decompose YoY change of a P&L line into components (SPEC-08 §6.1)."""
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)

    if fy_from is None:
        fy_from = _prev_fy(fy_to)

    norm_code = _normalize_line_code(line_code)

    # 1. PBT or PAT full bridge
    if norm_code == "PL.PBT":
        return pbt_bridge(df, fy_to, fy_from, scope).rows

    if norm_code == "PL.PAT":
        bridge = pbt_bridge(df, fy_to, fy_from, scope)
        rows_pat = list(bridge.rows)
        t_to, l_t_to = _lookup_row(df, "PL.TAX", fy_to, scope)
        t_from, l_t_from = _lookup_row(df, "PL.TAX", fy_from, scope)
        if t_to is not None and t_from is not None:
            tax_delta = round(round(t_to, 1) - round(t_from, 1), 1)
            pbt_imp = round(-tax_delta, 1)
            rows_pat.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code="PL.TAX",
                delta_inr_cr=tax_delta, component="sub_line", impact_inr_cr=tax_delta,
                impact_on_pbt_inr_cr=pbt_imp, method="M-TAX", inputs=[l_t_from, l_t_to],
                coverage="full",
            ))
        rows_pat.sort(key=lambda r: (-abs(r.impact_on_pbt_inr_cr), r.line_code, r.component))
        for idx, r in enumerate(rows_pat, 1):
            r.rank = idx
        return rows_pat

    # Look up base values for line_code
    val_to, lineage_to = _lookup_row(df, [line_code, norm_code], fy_to, scope)
    val_from, lineage_from = _lookup_row(df, [line_code, norm_code], fy_from, scope)

    if val_to is None or val_from is None:
        # Check if line_code can be synthesized from child lines (e.g. PL.OTHER_INCOME)
        if norm_code == "PL.OTHER_INCOME":
            d_to, l_d_to = _lookup_row(df, "PL.DIVIDEND_INCOME_10YR", fy_to, scope)
            o_to, l_o_to = _lookup_row(df, "PL.OTHER_NON_OP_INCOME_10YR", fy_to, scope)
            d_from, l_d_from = _lookup_row(df, "PL.DIVIDEND_INCOME_10YR", fy_from, scope)
            o_from, l_o_from = _lookup_row(df, "PL.OTHER_NON_OP_INCOME_10YR", fy_from, scope)
            if all(v is not None for v in [d_to, o_to, d_from, o_from]):
                val_to = round(d_to, 1) + round(o_to, 1)
                val_from = round(d_from, 1) + round(o_from, 1)
                lineage_to = {"line_code": "PL.OTHER_INCOME", "fy": fy_to, "value": val_to, "source": "derived"}
                lineage_from = {"line_code": "PL.OTHER_INCOME", "fy": fy_from, "value": val_from, "source": "derived"}

    if val_to is None or val_from is None:
        return []

    delta = round(round(val_to, 1) - round(val_from, 1), 1)
    base_inputs = [i for i in [lineage_from, lineage_to] if i]
    is_cost = _is_cost_line(norm_code)
    cost_factor = -1.0 if is_cost else 1.0

    rows: List[VarianceRow] = []

    # 2. Product Revenue (Crude, Gas, VAP)
    if norm_code in ("REV.CRUDE", "REV.GAS", "REV.VAP"):
        qty_code = (
            "QTY.CRUDE_SOLD"
            if norm_code == "REV.CRUDE"
            else ("QTY.GAS_SOLD" if norm_code == "REV.GAS" else "QTY.VAP_SOLD")
        )
        q_to, l_q_to = _lookup_row(df, qty_code, fy_to, scope)
        q_from, l_q_from = _lookup_row(df, qty_code, fy_from, scope)

        # Check for realization data for M-REV-PVF
        realisation_code = f"REALISATION.{norm_code.split('.')[1]}"
        p_to, l_p_to = _lookup_row(df, realisation_code, fy_to, scope)
        p_from, l_p_from = _lookup_row(df, realisation_code, fy_from, scope)
        fx_to, l_fx_to = _lookup_row(df, "FX.USD_INR", fy_to, scope)
        fx_from, l_fx_from = _lookup_row(df, "FX.USD_INR", fy_from, scope)

        if all(v is not None for v in [q_to, q_from, p_to, p_from, fx_to, fx_from]):
            # M-REV-PVF: ensure sum equals delta identically
            vol_imp = round((q_to - q_from) * p_from * fx_from, 1)
            price_imp = round(q_to * (p_to - p_from) * fx_from, 1)
            fx_imp = round(delta - vol_imp - price_imp, 1)
            inputs = base_inputs + [l_q_from, l_q_to, l_p_from, l_p_to, l_fx_from, l_fx_to]

            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="volume", impact_inr_cr=vol_imp,
                impact_on_pbt_inr_cr=vol_imp, method="M-REV-PVF", inputs=inputs, coverage="full",
            ))
            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="price", impact_inr_cr=price_imp,
                impact_on_pbt_inr_cr=price_imp, method="M-REV-PVF", inputs=inputs, coverage="full",
            ))
            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="fx", impact_inr_cr=fx_imp,
                impact_on_pbt_inr_cr=fx_imp, method="M-REV-PVF", inputs=inputs, coverage="full",
            ))
        elif q_to is not None and q_from is not None and q_from > 0:
            # M-REV-PV: Volume = R0 * (Q1/Q0 - 1); price_incl_fx = remainder
            vol_imp = round(val_from * (q_to / q_from - 1.0), 1)
            price_fx_imp = round(delta - vol_imp, 1)
            inputs = base_inputs + [l_q_from, l_q_to]

            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="volume", impact_inr_cr=vol_imp,
                impact_on_pbt_inr_cr=vol_imp, method="M-REV-PV", inputs=inputs, coverage="full",
            ))
            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="price_incl_fx", impact_inr_cr=price_fx_imp,
                impact_on_pbt_inr_cr=price_fx_imp, method="M-REV-PV", inputs=inputs, coverage="full",
            ))
        else:
            # Degrade to other_unexplained with coverage='partial'
            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="other_unexplained", impact_inr_cr=delta,
                impact_on_pbt_inr_cr=delta, method="other_unexplained", inputs=base_inputs, coverage="partial",
            ))

    # 3. Policy levies (e.g. SAED / Other levies)
    elif norm_code in ("LEVY.OTHER_SAED", "LEVY.OTHER"):
        rows.append(VarianceRow(
            fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
            delta_inr_cr=delta, component="policy_levy", impact_inr_cr=delta,
            impact_on_pbt_inr_cr=round(-delta, 1), method="M-POLICY", inputs=base_inputs, coverage="full",
        ))

    # 4. Total Levies (M-SUB decomposition)
    elif norm_code == "LEVY.TOTAL":
        child_codes = [
            ("LEVY.ROYALTY", "sub_line"),
            ("LEVY.OIDB_CESS", "sub_line"),
            ("LEVY.NCCD", "sub_line"),
            ("LEVY.OTHER_SAED", "policy_levy"),
        ]
        sub_sum = 0.0
        for c_code, comp in child_codes:
            c_to, l_c_to = _lookup_row(df, c_code, fy_to, scope)
            c_from, l_c_from = _lookup_row(df, c_code, fy_from, scope)
            if c_to is not None and c_from is not None:
                c_delta = round(round(c_to, 1) - round(c_from, 1), 1)
                sub_sum += c_delta
                rows.append(VarianceRow(
                    fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=c_code,
                    delta_inr_cr=c_delta, component=comp, impact_inr_cr=c_delta,
                    impact_on_pbt_inr_cr=round(-c_delta, 1),
                    method="M-POLICY" if comp == "policy_levy" else "M-SUB",
                    inputs=[l_c_from, l_c_to], coverage="full",
                ))
        residual = round(delta - sub_sum, 1)
        if abs(residual) > 0.05:
            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="other_unexplained", impact_inr_cr=residual,
                impact_on_pbt_inr_cr=round(-residual, 1), method="other_unexplained",
                inputs=base_inputs, coverage="partial",
            ))

    # 5. Royalty / OIDB Cess (M-LEVY with base, or degrade)
    elif norm_code in ("LEVY.ROYALTY", "LEVY.OIDB_CESS", "LEVY.NCCD"):
        base_code = "REV.CRUDE" if norm_code == "LEVY.ROYALTY" else "PL.REV_OPS"
        b_to, l_b_to = _lookup_row(df, base_code, fy_to, scope)
        b_from, l_b_from = _lookup_row(df, base_code, fy_from, scope)
        if b_to is not None and b_from is not None and b_from > 0 and b_to > 0:
            rate_from = val_from / b_from
            base_imp = round((b_to - b_from) * rate_from, 1)
            rate_imp = round(delta - base_imp, 1)  # closes exactly to delta
            inputs = base_inputs + [l_b_from, l_b_to]
            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="levy_base", impact_inr_cr=base_imp,
                impact_on_pbt_inr_cr=round(-base_imp, 1), method="M-LEVY", inputs=inputs, coverage="full",
            ))
            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="levy_rate", impact_inr_cr=rate_imp,
                impact_on_pbt_inr_cr=round(-rate_imp, 1), method="M-LEVY", inputs=inputs, coverage="full",
            ))
        else:
            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="other_unexplained", impact_inr_cr=delta,
                impact_on_pbt_inr_cr=round(-delta, 1), method="other_unexplained",
                inputs=base_inputs, coverage="partial",
            ))

    # 6. Revenue from operations (M-SUB decomposition)
    elif norm_code == "PL.REV_OPS":
        child_codes = ["REV.CRUDE", "REV.GAS", "REV.VAP"]
        sub_sum = 0.0
        for c_code in child_codes:
            c_to, l_c_to = _lookup_row(df, c_code, fy_to, scope)
            c_from, l_c_from = _lookup_row(df, c_code, fy_from, scope)
            if c_to is not None and c_from is not None:
                c_delta = round(round(c_to, 1) - round(c_from, 1), 1)
                sub_sum += c_delta
                rows.append(VarianceRow(
                    fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=c_code,
                    delta_inr_cr=c_delta, component="sub_line", impact_inr_cr=c_delta,
                    impact_on_pbt_inr_cr=c_delta, method="M-SUB",
                    inputs=[l_c_from, l_c_to], coverage="full",
                ))
        residual = round(delta - sub_sum, 1)
        if abs(residual) > 0.05:
            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="other_unexplained", impact_inr_cr=residual,
                impact_on_pbt_inr_cr=residual, method="other_unexplained",
                inputs=base_inputs, coverage="partial",
            ))

    # 7. Other income (M-SUB: Dividend vs Other non-operating)
    elif norm_code == "PL.OTHER_INCOME":
        child_codes = ["PL.DIVIDEND_INCOME_10YR", "PL.OTHER_NON_OP_INCOME_10YR"]
        sub_sum = 0.0
        for c_code in child_codes:
            c_to, l_c_to = _lookup_row(df, c_code, fy_to, scope)
            c_from, l_c_from = _lookup_row(df, c_code, fy_from, scope)
            if c_to is not None and c_from is not None:
                c_delta = round(round(c_to, 1) - round(c_from, 1), 1)
                sub_sum += c_delta
                rows.append(VarianceRow(
                    fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=c_code,
                    delta_inr_cr=c_delta, component="sub_line", impact_inr_cr=c_delta,
                    impact_on_pbt_inr_cr=c_delta, method="M-SUB",
                    inputs=[l_c_from, l_c_to], coverage="full",
                ))
        residual = round(delta - sub_sum, 1)
        if abs(residual) > 0.05:
            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="other_unexplained", impact_inr_cr=residual,
                impact_on_pbt_inr_cr=residual, method="other_unexplained",
                inputs=base_inputs, coverage="partial",
            ))

    # 8. Exploration write-offs (M-SUB: Survey vs Exploratory wells)
    elif norm_code == "PL.EXPL_WRITEOFF":
        child_codes = ["PL.EXPL_SURVEY", "PL.EXPL_WELL"]
        sub_sum = 0.0
        for c_code in child_codes:
            c_to, l_c_to = _lookup_row(df, c_code, fy_to, scope)
            c_from, l_c_from = _lookup_row(df, c_code, fy_from, scope)
            if c_to is not None and c_from is not None:
                c_delta = round(round(c_to, 1) - round(c_from, 1), 1)
                sub_sum += c_delta
                rows.append(VarianceRow(
                    fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=c_code,
                    delta_inr_cr=c_delta, component="sub_line", impact_inr_cr=c_delta,
                    impact_on_pbt_inr_cr=round(-c_delta, 1), method="M-SUB",
                    inputs=[l_c_from, l_c_to], coverage="full",
                ))
        residual = round(delta - sub_sum, 1)
        if abs(residual) > 0.05:
            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="other_unexplained", impact_inr_cr=residual,
                impact_on_pbt_inr_cr=round(-residual, 1), method="other_unexplained",
                inputs=base_inputs, coverage="partial",
            ))

    # 9. DD&A (Note 37 components: Depletion, Depr ROU, Amort, Impairment)
    elif norm_code == "PL.DDA":
        note37_children = [
            ("N37.DEPLETION", "Depletion"),
            ("N37.DEPR_ROU", "Depreciation of Right-of-Use Assets"),
            ("N37.AMORT", "Amortisation of Intangibles"),
            ("N37.IMPAIR", "Impairment of Property, Plant & Equipment"),
        ]
        found_children = False
        sub_sum = 0.0
        for c_code, _ in note37_children:
            c_to, l_c_to = _lookup_row(df, c_code, fy_to, scope)
            c_from, l_c_from = _lookup_row(df, c_code, fy_from, scope)
            if c_to is not None and c_from is not None:
                found_children = True
                c_delta = round(round(c_to, 1) - round(c_from, 1), 1)
                sub_sum += c_delta
                rows.append(VarianceRow(
                    fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=c_code,
                    delta_inr_cr=c_delta, component="sub_line", impact_inr_cr=c_delta,
                    impact_on_pbt_inr_cr=round(-c_delta, 1), method="M-SUB",
                    inputs=[l_c_from, l_c_to], coverage="full",
                ))
        if found_children:
            residual = round(delta - sub_sum, 1)
            if abs(residual) > 0.05:
                rows.append(VarianceRow(
                    fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                    delta_inr_cr=delta, component="other_unexplained", impact_inr_cr=residual,
                    impact_on_pbt_inr_cr=round(-residual, 1), method="other_unexplained",
                    inputs=base_inputs, coverage="partial",
                ))
        else:
            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="sub_line", impact_inr_cr=delta,
                impact_on_pbt_inr_cr=round(-delta, 1), method="M-SUB",
                inputs=base_inputs, coverage="full",
            ))

    # 10. Finance Costs (Note 36 components: Unwind Decom, Unwind Lease, Interest)
    elif norm_code == "PL.FIN_COST":
        note36_children = [
            ("N36.UNWIND_DECOM", "Decommissioning unwinding"),
            ("N36.UNWIND_LEASE", "Lease interest unwinding"),
            ("N36.BORROW_INT", "Borrowing interest expense"),
        ]
        found_children = False
        sub_sum = 0.0
        for c_code, _ in note36_children:
            c_to, l_c_to = _lookup_row(df, c_code, fy_to, scope)
            c_from, l_c_from = _lookup_row(df, c_code, fy_from, scope)
            if c_to is not None and c_from is not None:
                found_children = True
                c_delta = round(round(c_to, 1) - round(c_from, 1), 1)
                sub_sum += c_delta
                rows.append(VarianceRow(
                    fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=c_code,
                    delta_inr_cr=c_delta, component="sub_line", impact_inr_cr=c_delta,
                    impact_on_pbt_inr_cr=round(-c_delta, 1), method="M-SUB",
                    inputs=[l_c_from, l_c_to], coverage="full",
                ))
        if found_children:
            residual = round(delta - sub_sum, 1)
            if abs(residual) > 0.05:
                rows.append(VarianceRow(
                    fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                    delta_inr_cr=delta, component="other_unexplained", impact_inr_cr=residual,
                    impact_on_pbt_inr_cr=round(-residual, 1), method="other_unexplained",
                    inputs=base_inputs, coverage="partial",
                ))
        else:
            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="sub_line", impact_inr_cr=delta,
                impact_on_pbt_inr_cr=round(-delta, 1), method="M-SUB",
                inputs=base_inputs, coverage="full",
            ))

    # 11. One-off lines
    elif norm_code in (
        "PL.PROVISIONS_WRITEOFF",
        "PL.EXCHANGE_LOSS_10YR",
        "PL.OTHER_EXP_10YR",
        "PL.EXCEPTIONAL",
    ):
        pbt_imp = round(cost_factor * delta, 1)
        rows.append(VarianceRow(
            fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
            delta_inr_cr=delta, component="one_off", impact_inr_cr=delta,
            impact_on_pbt_inr_cr=pbt_imp, method="M-ONEOFF", inputs=base_inputs, coverage="full",
        ))

    # 12. Operating Expenses (M-UNIT if boe available, else degrade)
    elif norm_code == "PL.OPEX_10YR":
        boe_to, l_boe_to = _lookup_row(df, ["PROD.TOTAL_BOE", "QTY.TOTAL_BOE"], fy_to, scope)
        boe_from, l_boe_from = _lookup_row(df, ["PROD.TOTAL_BOE", "QTY.TOTAL_BOE"], fy_from, scope)
        if boe_to is not None and boe_from is not None and boe_from > 0 and boe_to > 0:
            unit_from = val_from / boe_from
            act_imp = round((boe_to - boe_from) * unit_from, 1)
            unit_imp = round(delta - act_imp, 1)  # closes exactly to delta
            inputs = base_inputs + [l_boe_from, l_boe_to]
            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="activity", impact_inr_cr=act_imp,
                impact_on_pbt_inr_cr=round(-act_imp, 1), method="M-UNIT", inputs=inputs, coverage="full",
            ))
            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="unit_cost", impact_inr_cr=unit_imp,
                impact_on_pbt_inr_cr=round(-unit_imp, 1), method="M-UNIT", inputs=inputs, coverage="full",
            ))
        else:
            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="other_unexplained", impact_inr_cr=delta,
                impact_on_pbt_inr_cr=round(-delta, 1), method="other_unexplained",
                inputs=base_inputs, coverage="partial",
            ))

    # 13. Tax (M-TAX)
    elif norm_code == "PL.TAX":
        pbt_to, l_pbt_to = _lookup_row(df, "PL.PBT", fy_to, scope)
        pbt_from, l_pbt_from = _lookup_row(df, "PL.PBT", fy_from, scope)
        if pbt_to is not None and pbt_from is not None and pbt_from > 0 and pbt_to > 0:
            t_from = val_from / pbt_from
            delta_pbt = pbt_to - pbt_from
            base_imp = round(delta_pbt * t_from, 1)
            rate_imp = round(delta - base_imp, 1)  # closes exactly to delta
            inputs = base_inputs + [l_pbt_from, l_pbt_to]
            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="levy_base", impact_inr_cr=base_imp,
                impact_on_pbt_inr_cr=round(-base_imp, 1), method="M-TAX", inputs=inputs, coverage="full",
            ))
            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="levy_rate", impact_inr_cr=rate_imp,
                impact_on_pbt_inr_cr=round(-rate_imp, 1), method="M-TAX", inputs=inputs, coverage="full",
            ))
        else:
            rows.append(VarianceRow(
                fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
                delta_inr_cr=delta, component="other_unexplained", impact_inr_cr=delta,
                impact_on_pbt_inr_cr=round(-delta, 1), method="other_unexplained",
                inputs=base_inputs, coverage="partial",
            ))

    # 14. Default fallback
    else:
        pbt_imp = round(cost_factor * delta, 1)
        rows.append(VarianceRow(
            fy_from=fy_from, fy_to=fy_to, scope=scope, line_code=line_code,
            delta_inr_cr=delta, component="other_unexplained", impact_inr_cr=delta,
            impact_on_pbt_inr_cr=pbt_imp, method="other_unexplained", inputs=base_inputs, coverage="partial",
        ))

    # Sort deterministically by |impact_on_pbt| descending, then line_code, component
    rows.sort(key=lambda r: (-abs(r.impact_on_pbt_inr_cr), r.line_code, r.component))
    for idx, r in enumerate(rows, 1):
        r.rank = idx

    return rows


def pbt_bridge(
    df: pd.DataFrame,
    fy_to: str,
    fy_from: Optional[str] = None,
    scope: str = "standalone",
) -> Bridge:
    """Build the PBT waterfall bridge decomposing YoY change (SPEC-08 §6.1, §6.5)."""
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)

    if fy_from is None:
        fy_from = _prev_fy(fy_to)

    pbt_to, l_pbt_to = _lookup_row(df, "PL.PBT", fy_to, scope)
    pbt_from, l_pbt_from = _lookup_row(df, "PL.PBT", fy_from, scope)

    if pbt_to is None or pbt_from is None:
        raise BridgeDoesNotClose(f"Missing PL.PBT in {fy_from} or {fy_to}")

    start_pbt = round(float(pbt_from), 1)
    end_pbt = round(float(pbt_to), 1)
    delta_pbt = round(end_pbt - start_pbt, 1)

    bridge_rows: List[VarianceRow] = []

    for canonical_code, aliases in PBT_BRIDGE_DRIVERS:
        v_to, l_to = _lookup_row(df, aliases, fy_to, scope)
        v_from, l_from = _lookup_row(df, aliases, fy_from, scope)

        # Prefer 10-year summary children for PL.OTHER_INCOME if available (fixes P2F4-B2)
        if canonical_code == "PL.OTHER_INCOME":
            d_to, l_d_to = _lookup_row(df, "PL.DIVIDEND_INCOME_10YR", fy_to, scope)
            o_to, l_o_to = _lookup_row(df, "PL.OTHER_NON_OP_INCOME_10YR", fy_to, scope)
            d_from, l_d_from = _lookup_row(df, "PL.DIVIDEND_INCOME_10YR", fy_from, scope)
            o_from, l_o_from = _lookup_row(df, "PL.OTHER_NON_OP_INCOME_10YR", fy_from, scope)
            if all(x is not None for x in [d_to, o_to, d_from, o_from]):
                v_to = round(d_to, 1) + round(o_to, 1)
                v_from = round(d_from, 1) + round(o_from, 1)
                l_to = {"line_code": canonical_code, "fy": fy_to, "value": v_to, "source": "derived"}
                l_from = {"line_code": canonical_code, "fy": fy_from, "value": v_from, "source": "derived"}

        # Fallback for LEVY.TOTAL if not explicitly present
        if (v_to is None or v_from is None) and canonical_code == "LEVY.TOTAL":
            l_parts_to = [_lookup_row(df, c, fy_to, scope)[0] for c in ["LEVY.ROYALTY", "LEVY.OIDB_CESS", "LEVY.NCCD", "LEVY.OTHER_SAED"]]
            l_parts_from = [_lookup_row(df, c, fy_from, scope)[0] for c in ["LEVY.ROYALTY", "LEVY.OIDB_CESS", "LEVY.NCCD", "LEVY.OTHER_SAED"]]
            if all(x is not None for x in l_parts_to) and all(x is not None for x in l_parts_from):
                v_to = sum(l_parts_to)
                v_from = sum(l_parts_from)
                l_to = {"line_code": canonical_code, "fy": fy_to, "value": v_to, "source": "derived"}
                l_from = {"line_code": canonical_code, "fy": fy_from, "value": v_from, "source": "derived"}

        # Fallback for PL.EXPL_WRITEOFF if not explicitly present
        if (v_to is None or v_from is None) and canonical_code == "PL.EXPL_WRITEOFF":
            e_parts_to = [_lookup_row(df, c, fy_to, scope)[0] for c in ["PL.EXPL_SURVEY", "PL.EXPL_WELL"]]
            e_parts_from = [_lookup_row(df, c, fy_from, scope)[0] for c in ["PL.EXPL_SURVEY", "PL.EXPL_WELL"]]
            if all(x is not None for x in e_parts_to) and all(x is not None for x in e_parts_from):
                v_to = sum(e_parts_to)
                v_from = sum(e_parts_from)
                l_to = {"line_code": canonical_code, "fy": fy_to, "value": v_to, "source": "derived"}
                l_from = {"line_code": canonical_code, "fy": fy_from, "value": v_from, "source": "derived"}

        if v_to is not None and v_from is not None:
            # Compute 1-dp bridge delta: round(round(v_to, 1) - round(v_from, 1), 1)
            line_delta = round(round(v_to, 1) - round(v_from, 1), 1)
            is_cost = _is_cost_line(canonical_code)
            pbt_impact = round(-line_delta if is_cost else line_delta, 1)
            inputs = [i for i in [l_from, l_to] if i]
            component = "one_off" if canonical_code in (
                "PL.PROVISIONS_WRITEOFF", "PL.EXCHANGE_LOSS_10YR", "PL.OTHER_EXP_10YR"
            ) else "sub_line"

            bridge_rows.append(VarianceRow(
                fy_from=fy_from,
                fy_to=fy_to,
                scope=scope,
                line_code=canonical_code,
                delta_inr_cr=line_delta,
                component=component,
                impact_inr_cr=line_delta,
                impact_on_pbt_inr_cr=pbt_impact,
                method="M-BRIDGE",
                inputs=inputs,
                coverage="full",
            ))

    # Also check for exceptional items
    exc_to, l_exc_to = _lookup_row(df, "PL.EXCEPTIONAL", fy_to, scope)
    exc_from, l_exc_from = _lookup_row(df, "PL.EXCEPTIONAL", fy_from, scope)
    if exc_to is not None or exc_from is not None:
        e_to = round(float(exc_to or 0.0), 1)
        e_from = round(float(exc_from or 0.0), 1)
        exc_delta = round(e_to - e_from, 1)
        if abs(exc_delta) > 0.05:
            inputs = [i for i in [l_exc_from, l_exc_to] if i]
            bridge_rows.append(VarianceRow(
                fy_from=fy_from,
                fy_to=fy_to,
                scope=scope,
                line_code="PL.EXCEPTIONAL",
                delta_inr_cr=exc_delta,
                component="one_off",
                impact_inr_cr=exc_delta,
                impact_on_pbt_inr_cr=exc_delta,
                method="M-BRIDGE",
                inputs=inputs,
                coverage="full",
            ))

    # Closure verification (Packet §5: |Σ impacts − ΔPBT| ≤ 0.1 ₹ cr, else raise BridgeDoesNotClose)
    total_impact = round(sum(r.impact_on_pbt_inr_cr for r in bridge_rows), 1)
    closure_error = round(abs(total_impact - delta_pbt), 4)

    if closure_error > 0.1:
        raise BridgeDoesNotClose(
            f"PBT bridge does not close: sum of impacts {total_impact:.1f} != "
            f"delta PBT {delta_pbt:.1f} (error {closure_error:.2f} > 0.1 ₹ cr)"
        )

    # Rank drivers by |impact_on_pbt| descending, deterministic tie break
    bridge_rows.sort(key=lambda r: (-abs(r.impact_on_pbt_inr_cr), r.line_code))
    for idx, r in enumerate(bridge_rows, 1):
        r.rank = idx

    return Bridge(
        fy_from=fy_from,
        fy_to=fy_to,
        scope=scope,
        start=start_pbt,
        end=end_pbt,
        delta=delta_pbt,
        closure_error=closure_error,
        rows=bridge_rows,
    )
