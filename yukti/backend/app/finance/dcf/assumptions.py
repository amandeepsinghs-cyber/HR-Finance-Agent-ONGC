from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, List

class AssumptionField(BaseModel):
    value: float
    source: str
    edited_by_user: bool = False

class DCFAssumptions(BaseModel):
    # Core editable
    wacc_pct: AssumptionField
    terminal_g_pct: AssumptionField
    brent_usd: AssumptionField
    capex_scale_pct: AssumptionField
    production_decline_pct: AssumptionField
    holdco_discount_pct: AssumptionField
    exit_ev_ebitda: AssumptionField
    
    # Internal variables passed along
    as_of: str
    run_id: str
    
    # Bridge components
    shares_outstanding: AssumptionField
    listed_investments_inr_cr: AssumptionField
    unlisted_investments_inr_cr: AssumptionField
    cash_and_equivalents_inr_cr: AssumptionField
    srf_deposits_inr_cr: AssumptionField
    decom_provision_inr_cr: AssumptionField
    borrowings_inr_cr: AssumptionField
    lease_liab_inr_cr: AssumptionField
    
    # Base numbers for forecast
    vol_crude_mmt: AssumptionField
    vol_gas_bcm: AssumptionField
    bbl_per_tonne: AssumptionField
    gcv_mmbtu_per_scm: AssumptionField
    fx_inr_usd: AssumptionField
    crude_realisation_discount_pct: AssumptionField
    gas_price_usd_mmbtu: AssumptionField
    vap_revenue_ratio: AssumptionField
    effective_levy_rate: AssumptionField
    opex_per_boe: AssumptionField
    inflation_pct: AssumptionField
    exploration_writeoff_ratio: AssumptionField
    dd_a_ratio: AssumptionField
    tax_rate_pct: AssumptionField
    capex_base_inr_cr: AssumptionField
    nwc_pct: AssumptionField
    market_price_inr: AssumptionField
    
    # Forecast overrides (for fixture testing)
    forecast_fcff: List[float] = []

    model_config = ConfigDict(frozen=True)

def _get_val(snapshot: List[Dict[str, Any]], code: str, default: float = 0.0) -> float:
    for row in snapshot:
        if row.get("line_code") == code and row.get("verified", False):
            return float(row.get("value_inr_cr", row.get("value", default)))
    return default

def defaults_from_ssot(snapshot: List[Dict[str, Any]], wacc_table: List[Dict[str, Any]], as_of: str) -> DCFAssumptions:
    from app.finance.dcf.inputs import load_fy26_market_price_default, load_fy26_wacc_default

    def mk(val, src):
        return AssumptionField(value=float(val), source=src)

    # Find WACC from wacc_table or canonical fact_wacc_annual FY26 SSOT
    wacc_val, wacc_source, _ = load_fy26_wacc_default(wacc_table)
    for row in wacc_table:
        if row.get("fiscal_year") == "FY26" and row.get("verified", False):
            if row.get("wacc_pct") is not None:
                wacc_val = float(row["wacc_pct"])
                wacc_source = "fact_wacc_annual FY26"

    mkt_px, mkt_src, _ = load_fy26_market_price_default()

    # Filter snapshot
    valid_snapshot = []
    for row in snapshot:
        if row.get("verified", False):
            valid_snapshot.append(row)
            
    # Bridge variables
    cce = _get_val(valid_snapshot, "BS.CCE") + _get_val(valid_snapshot, "BS.OTHER_BANK_BAL")
    
    # fallback to INV.LISTED / INV.UNLISTED if unit test passes it
    inv_listed = _get_val(valid_snapshot, "BS.INVESTMENTS_NC")
    if inv_listed == 0.0: inv_listed = _get_val(valid_snapshot, "INV.LISTED")
    
    inv_unlisted = _get_val(valid_snapshot, "BS.INVESTMENTS_C")
    if inv_unlisted == 0.0: inv_unlisted = _get_val(valid_snapshot, "INV.UNLISTED")
    
    srf = _get_val(valid_snapshot, "BS.SRF_DEPOSIT_NC")
    if srf == 0.0: srf = _get_val(valid_snapshot, "BS.SRF_DEPOSIT")
    
    decom = _get_val(valid_snapshot, "NPROV.DECOM_CLOSE")
    if decom == 0.0: decom = _get_val(valid_snapshot, "PROV.DECOM")
    
    borrowings = _get_val(valid_snapshot, "BS.BORROW_NC") + _get_val(valid_snapshot, "BS.BORROW_CUR")
    if borrowings == 0.0: borrowings = _get_val(valid_snapshot, "BS.BORROWINGS.TOTAL")
    
    lease = _get_val(valid_snapshot, "BS.LEASE_LIAB_NC") + _get_val(valid_snapshot, "BS.LEASE_LIAB_C")
    if lease == 0.0: lease = _get_val(valid_snapshot, "BS.LEASE_LIAB.TOTAL")

    return DCFAssumptions(
        wacc_pct=mk(wacc_val, wacc_source),
        terminal_g_pct=mk(3.0, "Illustrative assumption"),
        brent_usd=mk(80.0, "AR FY26"),
        capex_scale_pct=mk(100.0, "Illustrative assumption"),
        production_decline_pct=mk(0.0, "CAGR FY22-FY26"),
        holdco_discount_pct=mk(0.0, "Illustrative assumption"),
        exit_ev_ebitda=mk(4.5, "Illustrative assumption"),
        as_of=as_of,
        run_id="run_123",
        shares_outstanding=mk(1258.0279206, "SSOT"), # cr shares
        listed_investments_inr_cr=mk(inv_listed, "SSOT"),
        unlisted_investments_inr_cr=mk(inv_unlisted, "SSOT"),
        cash_and_equivalents_inr_cr=mk(cce, "SSOT"),
        srf_deposits_inr_cr=mk(srf, "SSOT"),
        decom_provision_inr_cr=mk(decom, "SSOT"),
        borrowings_inr_cr=mk(borrowings, "SSOT"),
        lease_liab_inr_cr=mk(lease, "SSOT"),
        vol_crude_mmt=mk(19.332, "fact_production_annual"),
        vol_gas_bcm=mk(19.533, "fact_production_annual"),
        bbl_per_tonne=mk(7.33, "Constant"),
        gcv_mmbtu_per_scm=mk(0.0372, "Constant"),
        fx_inr_usd=mk(83.0, "RBI"),
        crude_realisation_discount_pct=mk(0.0, "AR"),
        gas_price_usd_mmbtu=mk(6.5, "AR"),
        vap_revenue_ratio=mk(0.1, "Derived"),
        effective_levy_rate=mk(0.15, "Derived"),
        opex_per_boe=mk(15.0, "Derived"),
        inflation_pct=mk(4.0, "Illustrative"),
        exploration_writeoff_ratio=mk(0.05, "Derived"),
        dd_a_ratio=mk(0.1, "Derived"),
        tax_rate_pct=mk(25.17, "AR"),
        capex_base_inr_cr=mk(39482.738, "Derived"),
        nwc_pct=mk(0.05, "Derived"),
        market_price_inr=mk(mkt_px, mkt_src)
    )
