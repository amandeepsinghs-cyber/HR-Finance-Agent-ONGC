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
        beta_adj = 0.67 * beta_raw + 0.33
        ke = rf + beta_raw * erp
        kd_after_tax = kd * (1 - t / 100)
        wacc = we * ke + wd * kd_after_tax
        ke_alt = (rf - spread) + beta_raw * erp
        wacc_alt = we * ke_alt + wd * kd_after_tax
    else:
        from app.finance.dcf.inputs import load_fy26_wacc_default
        _, _, meta = load_fy26_wacc_default()
        rf = float(meta.get("rf_used_pct", 7.0782))
        spread = float(meta.get("default_spread_pct", 1.8678))
        erp = float(meta.get("erp_total_pct", 7.0754))
        beta_raw = float(meta.get("beta_industry_relevered", 0.7607))
        beta_adj = round(0.67 * beta_raw + 0.33, 4)
        kd = float(meta.get("kd_used_pct", 4.1272))
        t = float(assumptions.tax_rate_pct.value if assumptions and hasattr(assumptions, "tax_rate_pct") else meta.get("tax_rate_pct", 25.17))
        we = float(meta.get("weight_equity", 0.914114))
        wd = float(meta.get("weight_debt", 1.0 - we))
        ke = round(float(meta.get("ke_pct", rf + beta_raw * erp)), 4)
        kd_after_tax = round(kd * (1 - t / 100), 4)
        wacc = round(float(assumptions.wacc_pct.value if assumptions and hasattr(assumptions, "wacc_pct") else meta.get("wacc_pct", we * ke + wd * kd_after_tax)), 4)
        ke_alt = (rf - spread) + beta_raw * erp
        wacc_alt = round(float(meta.get("wacc_alt_gsec_less_spread_pct", we * ke_alt + wd * kd_after_tax)), 4)

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
