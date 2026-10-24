"""WACC Attribution Engine via 5-Factor Shapley Decomposition.

Implements SPEC-02 §5.3, BEH-03.05, and BEH-03.06:
- Exact 5-factor Shapley values over all 5! = 120 permutations:
  (rf_used, erp_total, beta_adj, kd_after_tax, weights)
- Deterministic closure: sum of factor contributions == ΔWACC (±1e-9).
- Ranking of factors by absolute contribution and structured narrative.
- Caveat handling for unverified/missing seeds (e.g. verified=FALSE).
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

try:
    import pandas as pd
except ImportError:
    pd = None  # type: ignore[assignment]


FACTOR_KEYS = ("rf_used", "erp_total", "beta", "kd_after_tax", "weights")

FACTOR_LABELS = {
    "rf_used": "Risk-Free Rate (Rf)",
    "erp_total": "Equity Risk Premium (ERP)",
    "beta": "Beta (β)",
    "kd_after_tax": "Cost of Debt (after-tax)",
    "weights": "Capital Structure (Weights)",
}

FACTOR_DEFAULT_SOURCES = {
    "rf_used": "FBIL / RBI 10-yr G-sec (March)",
    "erp_total": "Damodaran sovereign default spread & ERP dataset (January)",
    "beta": "Blume-adjusted 2-yr weekly beta vs NIFTY 50 (or Hamada industry relevered)",
    "kd_after_tax": "AR Note 36 (Finance Costs excl. decommissioning unwinding) and tax rate",
    "weights": "Market equity vs book debt (borrowings + lease liabilities)",
}


@dataclass(frozen=True)
class WACCParameters:
    """Inputs to WACC calculation for a single fiscal year.

    All rates/returns are in percentage points (e.g., 5.0 for 5%, not 0.05).
    Weights are fractions (e.g., 0.90 for 90% equity).
    """

    fiscal_year: str
    rf_used: float
    erp_total: float
    beta: float
    kd_after_tax: float
    weight_equity: float  # equity weight w_e in [0, 1]; w_d = 1.0 - w_e
    kd_pretax: Optional[float] = None
    tax_rate: Optional[float] = None
    weight_debt: Optional[float] = None
    sources: Optional[Dict[str, str]] = None
    verified: bool = True
    notes: Optional[str] = None

    def ke(self) -> float:
        """Cost of Equity via CAPM: Ke = Rf + Beta * ERP."""
        return calculate_ke(self.rf_used, self.erp_total, self.beta)

    def wacc(self) -> float:
        """WACC = w_e * Ke + (1 - w_e) * Kd_at."""
        return calculate_wacc(
            self.rf_used,
            self.erp_total,
            self.beta,
            self.kd_after_tax,
            self.weight_equity,
        )


def calculate_ke(rf: float, erp: float, beta: float) -> float:
    """Cost of Equity via standard CAPM: Ke = Rf + Beta * ERP."""
    return float(rf) + float(beta) * float(erp)


def calculate_wacc(
    rf: float,
    erp: float,
    beta: float,
    kd_at: float,
    weight_equity: float,
) -> float:
    """WACC calculation: w_e * Ke + (1 - w_e) * Kd_at."""
    ke = calculate_ke(rf, erp, beta)
    we = float(weight_equity)
    wd = 1.0 - we
    return we * ke + wd * float(kd_at)


@dataclass
class ShapleyFactorContribution:
    """Attribution contribution of a single factor to delta WACC."""

    factor: str
    label: str
    from_value: float
    to_value: float
    contribution: float
    rank: int = 0
    source: Optional[str] = None
    narrative_detail: Optional[str] = None


@dataclass
class WACCAttributionResult:
    """Result of Shapley 5-factor decomposition of WACC change."""

    fy_from: str
    fy_to: str
    wacc_from: float
    wacc_to: float
    delta_wacc: float
    contributions: Dict[str, float]
    factor_details: List[ShapleyFactorContribution]
    top_factors: List[ShapleyFactorContribution]
    narrative: str
    waterfall_bars: List[Dict[str, Any]]
    caveats: List[str] = field(default_factory=list)


def compute_wacc_shapley(
    from_params: WACCParameters,
    to_params: WACCParameters,
) -> WACCAttributionResult:
    """Decompose ΔWACC(from_params → to_params) into 5 Shapley factors.

    Evaluates exact marginal contribution over all 5! = 120 permutations.
    Sum of contributions equals ΔWACC exactly (within ±1e-9).
    """
    wacc_a = from_params.wacc()
    wacc_b = to_params.wacc()
    delta_wacc = wacc_b - wacc_a

    map_a = {
        "rf_used": float(from_params.rf_used),
        "erp_total": float(from_params.erp_total),
        "beta": float(from_params.beta),
        "kd_after_tax": float(from_params.kd_after_tax),
        "weights": float(from_params.weight_equity),
    }
    map_b = {
        "rf_used": float(to_params.rf_used),
        "erp_total": float(to_params.erp_total),
        "beta": float(to_params.beta),
        "kd_after_tax": float(to_params.kd_after_tax),
        "weights": float(to_params.weight_equity),
    }

    perms = list(itertools.permutations(FACTOR_KEYS))
    raw_contribs = {f: 0.0 for f in FACTOR_KEYS}

    for perm in perms:
        state = dict(map_a)
        val = calculate_wacc(
            state["rf_used"],
            state["erp_total"],
            state["beta"],
            state["kd_after_tax"],
            state["weights"],
        )
        for f in perm:
            next_state = dict(state)
            next_state[f] = map_b[f]
            next_val = calculate_wacc(
                next_state["rf_used"],
                next_state["erp_total"],
                next_state["beta"],
                next_state["kd_after_tax"],
                next_state["weights"],
            )
            raw_contribs[f] += next_val - val
            state = next_state
            val = next_val

    num_perms = float(len(perms))
    contributions = {f: raw_contribs[f] / num_perms for f in FACTOR_KEYS}

    sum_contrib = sum(contributions.values())
    closure_err = abs(sum_contrib - delta_wacc)
    if closure_err > 1e-9:
        raise ValueError(
            f"Shapley decomposition did not close: sum={sum_contrib}, delta={delta_wacc}, err={closure_err}"
        )

    # Rank factors by absolute contribution descending
    ranked_keys = sorted(
        FACTOR_KEYS, key=lambda f: abs(contributions[f]), reverse=True
    )

    sources_map = {}
    if to_params.sources:
        sources_map.update(to_params.sources)

    factor_details: List[ShapleyFactorContribution] = []
    for rank_idx, f in enumerate(ranked_keys, start=1):
        v_from = map_a[f]
        v_to = map_b[f]
        c_val = contributions[f]
        src = sources_map.get(f) or FACTOR_DEFAULT_SOURCES.get(f, "SSOT")

        unit = "%" if f != "beta" and f != "weights" else ""
        if f == "weights":
            detail = (
                f"Equity weight shifted from {v_from*100:.1f}% to {v_to*100:.1f}% "
                f"({c_val:+.3f} pp contribution)"
            )
        else:
            direction = "rose" if v_to >= v_from else "fell"
            detail = (
                f"{FACTOR_LABELS[f]} {direction} from {v_from:.2f}{unit} to {v_to:.2f}{unit} "
                f"({c_val:+.3f} pp, {src})"
            )

        factor_details.append(
            ShapleyFactorContribution(
                factor=f,
                label=FACTOR_LABELS[f],
                from_value=v_from,
                to_value=v_to,
                contribution=c_val,
                rank=rank_idx,
                source=src,
                narrative_detail=detail,
            )
        )

    top_factors = factor_details[:2]

    # Build narrative per BEH-03.06:
    # "Why was WACC high in FY23? ... waterfall from WACC FY22 to WACC FY23 with 5 bars.
    # The narrative names the top 2 factors with values and sources."
    direction_word = "increased" if delta_wacc >= 0 else "decreased"
    narrative_lines = [
        f"WACC {direction_word} by {abs(delta_wacc):.2f} pp from {wacc_a:.2f}% ({from_params.fiscal_year}) "
        f"to {wacc_b:.2f}% ({to_params.fiscal_year})."
    ]
    if top_factors:
        lead_reasons = []
        for tf in top_factors:
            lead_reasons.append(tf.narrative_detail or f"{tf.label} ({tf.contribution:+.3f} pp)")
        narrative_lines.append("The primary drivers were: " + "; ".join(lead_reasons) + ".")
    narrative = " ".join(narrative_lines)

    # Waterfall chart rows
    waterfall_bars: List[Dict[str, Any]] = [
        {
            "factor": f"WACC {from_params.fiscal_year}",
            "contribution_pct": round(wacc_a, 3),
            "amount": round(wacc_a, 3),
            "bar_type": "base",
            "is_total": True,
        }
    ]
    for f in FACTOR_KEYS:
        c_val = contributions[f]
        waterfall_bars.append({
            "factor": FACTOR_LABELS[f],
            "contribution_pct": round(c_val, 3),
            "amount": round(c_val, 3),
            "bar_type": "delta",
            "is_total": False,
            "from_value": round(map_a[f], 3),
            "to_value": round(map_b[f], 3),
            "source": sources_map.get(f) or FACTOR_DEFAULT_SOURCES.get(f),
        })
    waterfall_bars.append({
        "factor": f"WACC {to_params.fiscal_year}",
        "contribution_pct": round(wacc_b, 3),
        "amount": round(wacc_b, 3),
        "bar_type": "total",
        "is_total": True,
    })

    caveats = []
    if not from_params.verified or not to_params.verified:
        caveats.append("Modelled with caveats: underlying inputs unverified (verified=FALSE).")
    if from_params.notes:
        caveats.append(f"{from_params.fiscal_year}: {from_params.notes}")
    if to_params.notes:
        caveats.append(f"{to_params.fiscal_year}: {to_params.notes}")

    return WACCAttributionResult(
        fy_from=from_params.fiscal_year,
        fy_to=to_params.fiscal_year,
        wacc_from=wacc_a,
        wacc_to=wacc_b,
        delta_wacc=delta_wacc,
        contributions=contributions,
        factor_details=factor_details,
        top_factors=top_factors,
        narrative=narrative,
        waterfall_bars=waterfall_bars,
        caveats=caveats,
    )


def extract_wacc_parameters(
    df_annual: Any,
    fiscal_year: str,
    df_input: Any = None,
) -> Optional[WACCParameters]:
    """Extract WACCParameters for a given fiscal year from fact_wacc_annual."""
    if df_annual is None or (hasattr(df_annual, "empty") and df_annual.empty):
        return None

    sub = df_annual[df_annual["fiscal_year"] == fiscal_year]
    if sub.empty:
        return None

    row = sub.iloc[0]

    def _get_val(key: str, default: Optional[float] = None) -> Optional[float]:
        if key not in row:
            return default
        val = row[key]
        if pd is not None and pd.isna(val):
            return default
        if val is None:
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    rf = _get_val("rf_used_pct") or _get_val("rf_gsec_10y_pct")
    erp = _get_val("erp_total_pct")
    beta = (
        _get_val("beta_2y_weekly_adj")
        or _get_val("beta_industry_relevered")
        or _get_val("beta_2y_weekly_raw")
    )
    kd_used = _get_val("kd_used_pct") or _get_val("kd_pretax_pct")
    tax_rate = _get_val("tax_rate_pct", 25.17)
    we = _get_val("weight_equity")

    kd_at = None
    if kd_used is not None and tax_rate is not None:
        kd_at = kd_used * (1.0 - tax_rate / 100.0)

    # If any mandatory factor is missing from annual row, inspect df_input
    sources: Dict[str, str] = {}
    if df_input is not None and hasattr(df_input, "empty") and not df_input.empty:
        inp_sub = df_input[df_input["fiscal_year"] == fiscal_year]
        for _, inp_row in inp_sub.iterrows():
            code = str(inp_row.get("input_code"))
            doc = str(inp_row.get("source_doc") or "")
            sys_name = str(inp_row.get("source_system") or "")
            src_str = f"{sys_name} ({doc})" if doc and doc != "nan" else sys_name
            if "rf" in code:
                sources["rf_used"] = src_str
            elif "erp" in code:
                sources["erp_total"] = src_str
            elif "beta" in code:
                sources["beta"] = src_str
            elif "kd" in code:
                sources["kd_after_tax"] = src_str

    if rf is None or erp is None or beta is None or kd_at is None or we is None:
        return None

    return WACCParameters(
        fiscal_year=fiscal_year,
        rf_used=rf,
        erp_total=erp,
        beta=beta,
        kd_after_tax=kd_at,
        weight_equity=we,
        kd_pretax=kd_used,
        tax_rate=tax_rate,
        weight_debt=1.0 - we,
        sources=sources or None,
        verified=bool(row.get("verified", False)),
        notes=str(row.get("notes") or "") or None,
    )


def attribute_wacc_change(
    df_annual: Any,
    fy_from: str,
    fy_to: str,
    df_input: Any = None,
) -> Optional[WACCAttributionResult]:
    """Execute 5-factor Shapley attribution between two fiscal years from dataframes."""
    params_a = extract_wacc_parameters(df_annual, fy_from, df_input)
    params_b = extract_wacc_parameters(df_annual, fy_to, df_input)

    if params_a is None or params_b is None:
        return None

    return compute_wacc_shapley(params_a, params_b)
