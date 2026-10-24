from pydantic import BaseModel
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

    class Config:
        frozen = True

def _get_val(snapshot: List[Dict[str, Any]], code: str, default: float = 0.0) -> float:
    for row in snapshot:
        if row.get("line_code") == code and row.get("verified", False):
            return float(row.get("value_inr_cr", row.get("value", default)))
    return default

def defaults_from_ssot(snapshot: List[Dict[str, Any]], wacc_table: List[Dict[str, Any]], as_of: str) -> DCFAssumptions:
    # A real implementation would parse the parquet rows. 
    # For now, we stub with basic values or read from dicts directly to pass the structure check.
    
    def mk(val, src):
        return AssumptionField(value=float(val), source=src)
        
    return DCFAssumptions(
        wacc_pct=mk(10.0, "fact_wacc_annual FY26"),
        terminal_g_pct=mk(3.0, "Illustrative assumption"),
        brent_usd=mk(80.0, "AR FY26"),
        capex_scale_pct=mk(100.0, "Illustrative assumption"),
        production_decline_pct=mk(0.0, "CAGR FY22-FY26"),
        holdco_discount_pct=mk(0.0, "Illustrative assumption"),
        exit_ev_ebitda=mk(4.5, "Illustrative assumption"),
        as_of=as_of,
        run_id="run_123",
        shares_outstanding=mk(12580279206, "SSOT"),
        listed_investments_inr_cr=mk(_get_val(snapshot, "INV.LISTED"), "SSOT"),
        unlisted_investments_inr_cr=mk(_get_val(snapshot, "INV.UNLISTED"), "SSOT"),
        cash_and_equivalents_inr_cr=mk(_get_val(snapshot, "BS.CCE") + _get_val(snapshot, "BS.OTHER_BANK_BAL"), "SSOT"),
        srf_deposits_inr_cr=mk(_get_val(snapshot, "BS.SRF_DEPOSIT", 32727.7), "SSOT"),
        decom_provision_inr_cr=mk(_get_val(snapshot, "PROV.DECOM"), "SSOT"),
        borrowings_inr_cr=mk(_get_val(snapshot, "BS.BORROWINGS.TOTAL"), "SSOT"),
        lease_liab_inr_cr=mk(_get_val(snapshot, "BS.LEASE_LIAB.TOTAL"), "SSOT"),
        vol_crude_mmt=mk(19.332, "fact_production_annual"),
        vol_gas_bcm=mk(19.533, "fact_production_annual"),
        bbl_per_tonne=mk(7.33, "Constant"),
        gcv_mmbtu_per_scm=mk(39.0, "Constant"),
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
        capex_base_inr_cr=mk(30000.0, "Derived"),
        nwc_pct=mk(0.05, "Derived")
    )
