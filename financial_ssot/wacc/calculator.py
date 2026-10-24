"""Pure-Python WACC calculations, Blume adjustment, Hamada re-levering, and OLS regression.

SPEC-02 §3.1, §10; Packet: docs/delegation/packets/v3/P1.9_wacc_inputs.md
"""
from __future__ import annotations

import numpy as np


def blume_adjustment(beta_raw: float) -> float:
    """Blume adjustment: 0.67 * beta_raw + 0.33."""
    return round(0.67 * beta_raw + 0.33, 4)


def hamada_relever(
    beta_unlevered: float,
    debt_bv: float,
    equity_bv: float,
    tax_rate_pct: float,
) -> float:
    """Hamada formula for re-levering industry unlevered beta using book D/E and tax rate.

    beta_levered = beta_unlevered * (1 + (1 - t) * (D / E))
    """
    if equity_bv <= 0:
        return beta_unlevered
    t = tax_rate_pct / 100.0
    de_ratio = debt_bv / equity_bv
    return round(beta_unlevered * (1.0 + (1.0 - t) * de_ratio), 4)


def compute_ke(rf_pct: float, beta: float, erp_pct: float) -> float:
    """Cost of Equity (Ke) = Rf + beta * ERP."""
    return round(rf_pct + beta * erp_pct, 4)


def compute_kd_after_tax(kd_pretax_pct: float, tax_rate_pct: float) -> float:
    """Cost of Debt after tax = Kd_pretax * (1 - tax_rate)."""
    t = tax_rate_pct / 100.0
    return round(kd_pretax_pct * (1.0 - t), 4)


def compute_wacc(
    equity: float,
    debt: float,
    ke_pct: float,
    kd_after_tax_pct: float,
) -> tuple[float, float, float]:
    """Compute WACC, weight_equity, and weight_debt.

    WACC = E/(D+E) * Ke + D/(D+E) * Kd_after_tax
    Returns (wacc_pct, weight_equity, weight_debt).
    """
    total_val = equity + debt
    if total_val <= 0:
        return (0.0, 0.0, 0.0)
    w_e = equity / total_val
    w_d = debt / total_val
    wacc = w_e * ke_pct + w_d * kd_after_tax_pct
    return (round(wacc, 4), round(w_e, 6), round(w_d, 6))


def compute_ols_beta(
    r_stock: np.ndarray | list[float],
    r_market: np.ndarray | list[float],
) -> tuple[float, float]:
    """Calculate OLS beta (slope) and R-squared between stock and market returns.

    Returns (beta_raw, r_squared).
    """
    y = np.asarray(r_stock, dtype=float)
    x = np.asarray(r_market, dtype=float)

    if len(y) != len(x) or len(y) < 2:
        raise ValueError("Inputs must have identical length >= 2")

    x_mean = np.mean(x)
    y_mean = np.mean(y)

    ss_xx = np.sum((x - x_mean) ** 2)
    ss_xy = np.sum((x - x_mean) * (y - y_mean))
    ss_yy = np.sum((y - y_mean) ** 2)

    if ss_xx == 0:
        return (0.0, 0.0)

    beta = ss_xy / ss_xx
    r2 = (ss_xy ** 2) / (ss_xx * ss_yy) if ss_yy > 0 else 0.0

    return (round(float(beta), 4), round(float(r2), 4))
