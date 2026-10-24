# fcff.py
def compute_fcff(assumptions):
    if assumptions.forecast_fcff:
        fcff_list = assumptions.forecast_fcff
        res = []
        for i, f in enumerate(fcff_list, 1):
            res.append({
                "period": f"FY{26+i}",
                "fcff": f,
                "t": i,
                "discount_factor": 1 / ((1 + assumptions.wacc_pct.value / 100) ** i),
                "pv_fcff": f / ((1 + assumptions.wacc_pct.value / 100) ** i)
            })
        return {"forecast": res, "historical": []}

    res = []
    w = assumptions.wacc_pct.value / 100
    for i in range(1, 11):
        crude_vol = assumptions.vol_crude_mmt.value * ((1 - assumptions.production_decline_pct.value/100)**i)
        gas_vol = assumptions.vol_gas_bcm.value * ((1 - assumptions.production_decline_pct.value/100)**i)
        rev_crude = crude_vol * assumptions.bbl_per_tonne.value * assumptions.brent_usd.value * assumptions.fx_inr_usd.value / 10
        rev_gas = gas_vol * 100.0 * assumptions.gcv_mmbtu_per_scm.value * assumptions.gas_price_usd_mmbtu.value * assumptions.fx_inr_usd.value
        rev_vap = (rev_crude + rev_gas) * assumptions.vap_revenue_ratio.value
        rev = rev_crude + rev_gas + rev_vap
        
        levy = rev * assumptions.effective_levy_rate.value
        boe = (crude_vol * 7.33 + gas_vol * 6.29) * 1e6
        opex = (boe * assumptions.opex_per_boe.value * assumptions.fx_inr_usd.value / 1e7) * ((1 + assumptions.inflation_pct.value/100)**i)
        
        capex = assumptions.capex_base_inr_cr.value * (assumptions.capex_scale_pct.value/100)
        dda = capex * assumptions.dd_a_ratio.value
        expl = capex * assumptions.exploration_writeoff_ratio.value
        
        ebit = rev - levy - opex - dda - expl
        tax = ebit * (assumptions.tax_rate_pct.value / 100)
        nwc = rev * assumptions.nwc_pct.value - (rev / (1+assumptions.inflation_pct.value/100)) * assumptions.nwc_pct.value
        
        fcff = ebit - tax + dda - capex - nwc
        
        res.append({
            "period": f"FY{26+i}",
            "crude_mmt": crude_vol,
            "gas_bcm": gas_vol,
            "rev_crude": rev_crude,
            "rev_gas": rev_gas,
            "rev_vap": rev_vap,
            "rev": rev,
            "levy": levy,
            "opex": opex,
            "capex": capex,
            "dda": dda,
            "expl": expl,
            "ebit": ebit,
            "tax": tax,
            "nwc": nwc,
            "fcff": fcff,
            "t": i,
            "discount_factor": 1 / ((1+w)**i),
            "pv_fcff": fcff / ((1+w)**i)
        })

    return {"forecast": res, "historical": []}
