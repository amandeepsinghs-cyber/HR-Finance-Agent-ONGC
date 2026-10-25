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
        from app.finance.dcf.inputs import DCFInputMissingError, load_fy26_wacc_default
        _, _, meta = load_fy26_wacc_default()
        required_keys = (
            "rf_used_pct",
            "default_spread_pct",
            "erp_total_pct",
            "beta_industry_relevered",
            "kd_used_pct",
            "weight_equity",
        )
        missing_keys = [k for k in required_keys if meta.get(k) is None]
        if missing_keys:
            raise DCFInputMissingError(
                "fact_wacc_annual",
                f"Missing WACC component(s) in fact_wacc_annual FY26: {', '.join(missing_keys)}",
            )
        rf = float(meta["rf_used_pct"])
        spread = float(meta["default_spread_pct"])
        erp = float(meta["erp_total_pct"])
        beta_raw = float(meta["beta_industry_relevered"])
        beta_adj = round(0.67 * beta_raw + 0.33, 4)
        kd = float(meta["kd_used_pct"])
        if assumptions and hasattr(assumptions, "tax_rate_pct"):
            t = float(assumptions.tax_rate_pct.value)
        elif meta.get("tax_rate_pct") is not None:
            t = float(meta["tax_rate_pct"])
        else:
            raise DCFInputMissingError("fact_wacc_annual", "Missing tax_rate_pct in fact_wacc_annual FY26")
        we = float(meta["weight_equity"])
        wd = float(meta["weight_debt"]) if meta.get("weight_debt") is not None else (1.0 - we)
        ke = round(float(meta["ke_pct"]) if meta.get("ke_pct") is not None else (rf + beta_raw * erp), 4)
        kd_after_tax = round(kd * (1 - t / 100), 4)
        wacc = round(
            float(
                assumptions.wacc_pct.value
                if assumptions and hasattr(assumptions, "wacc_pct")
                else (meta["wacc_pct"] if meta.get("wacc_pct") is not None else (we * ke + wd * kd_after_tax))
            ),
            4,
        )
        ke_alt = (rf - spread) + beta_raw * erp
        wacc_alt = round(
            float(meta["wacc_alt_gsec_less_spread_pct"])
            if meta.get("wacc_alt_gsec_less_spread_pct") is not None
            else (we * ke_alt + wd * kd_after_tax),
            4,
        )

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
        "weight_debt": wd,
    }
