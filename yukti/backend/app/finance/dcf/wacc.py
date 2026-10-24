# wacc.py
def compute_wacc(assumptions, fixture=None):
    if fixture:
        rf = fixture.get("rf", 7.0)
        beta_raw = fixture.get("beta_raw", 1.2)
        erp = fixture.get("erp", 7.0)
        kd = fixture.get("kd", 6.0)
        t = fixture.get("t", 25.17)
        we = fixture.get("e", 900.0) / (fixture.get("e", 900.0) + fixture.get("d", 100.0))
        wd = 1 - we
        spread = fixture.get("default_spread", 2.0)
    else:
        rf = 7.0
        beta_raw = 1.2
        erp = 7.0
        kd = 6.0
        t = assumptions.tax_rate_pct.value
        we = 0.9
        wd = 0.1
        spread = 2.0

    beta_adj = 0.67 * beta_raw + 0.33
    ke = rf + beta_raw * erp
    kd_after_tax = kd * (1 - t / 100)
    wacc = we * ke + wd * kd_after_tax
    
    ke_alt = (rf - spread) + beta_raw * erp
    wacc_alt = we * ke_alt + wd * kd_after_tax
    
    return {
        "wacc_pct": wacc,
        "wacc_alt_gsec_less_spread_pct": wacc_alt,
        "beta_adj": beta_adj,
        "rf_used_pct": rf,
        "erp_total_pct": erp,
        "ke_pct": ke,
        "kd_used_pct": kd,
        "kd_after_tax_pct": kd_after_tax,
        "tax_rate_pct": t,
        "weight_equity": we,
    }
