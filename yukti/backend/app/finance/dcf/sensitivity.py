# sensitivity.py
def compute_sensitivity(assumptions, fcff_res, val_res):
    w_base = assumptions.wacc_pct.value
    g_base = assumptions.terminal_g_pct.value
    
    w_axis = [w_base + i*0.5 for i in range(-4, 5)]
    g_axis = [g_base + i*0.5 for i in range(-4, 5)]
    
    grid = []
    
    net_debt = assumptions.borrowings_inr_cr.value + assumptions.lease_liab_inr_cr.value + assumptions.decom_provision_inr_cr.value - assumptions.cash_and_equivalents_inr_cr.value - assumptions.srf_deposits_inr_cr.value
    investments = assumptions.listed_investments_inr_cr.value + assumptions.unlisted_investments_inr_cr.value
    shares = assumptions.shares_outstanding.value
    if shares == 0: shares = 1.0
    
    f_list = fcff_res.get("forecast", [])
    
    for w in w_axis:
        row = []
        for g in g_axis:
            if w - g < 1.0:
                row.append(None)
            else:
                w_d = w / 100
                g_d = g / 100
                spv = sum(f["fcff"] / ((1+w_d)**f["t"]) for f in f_list)
                last_fcff = f_list[-1]["fcff"] if f_list else 0
                tv = last_fcff * (1 + g_d) / (w_d - g_d)
                pv_tv = tv / ((1+w_d)**len(f_list))
                ev = spv + pv_tv
                eq = (ev - net_debt + investments) * (1 - assumptions.holdco_discount_pct.value/100)
                row.append(eq / shares)
        grid.append(row)
        
    return {
        "wacc_axis_pct": w_axis,
        "g_axis_pct": g_axis,
        "values_inr": grid
    }

def compute_tornado(assumptions, base_ps):
    from copy import deepcopy
    from app.finance.dcf.fcff import compute_fcff
    from app.finance.dcf.valuation import compute_valuation
    
    def eval_ps(asm):
        f = compute_fcff(asm)
        v = compute_valuation(asm, f)
        return v.get("per_share", {}).get("intrinsic_inr", 0.0)

    res = []
    drivers = [
        ("brent_usd", "brent", lambda v: (v - 10, v + 10)),
        ("opex_per_boe", "opex", lambda v: (v * 0.85, v * 1.15)),
        ("capex_scale_pct", "capex", lambda v: (v - 20, v + 20)),
        ("production_decline_pct", "prod", lambda v: (v - 10, v + 10)),
        ("wacc_pct", "wacc", lambda v: (v - 1, v + 1)),
        ("terminal_g_pct", "g", lambda v: (v - 1, v + 1)),
        ("fx_inr_usd", "fx", lambda v: (v * 0.95, v * 1.05)),
        ("holdco_discount_pct", "holdco", lambda v: (0.0, 30.0))
    ]
    
    asm_dict = assumptions.model_dump() if hasattr(assumptions, "model_dump") else assumptions.dict()
    
    for field, name, mutator in drivers:
        val = asm_dict[field]["value"]
        low_val, high_val = mutator(val)
        
        # low
        a_low = deepcopy(asm_dict)
        a_low[field]["value"] = low_val
        from app.finance.dcf.assumptions import DCFAssumptions
        ps_low = eval_ps(DCFAssumptions(**a_low))
        
        # high
        a_high = deepcopy(asm_dict)
        a_high[field]["value"] = high_val
        ps_high = eval_ps(DCFAssumptions(**a_high))
        
        res.append({
            "driver": name,
            "low_inr": ps_low,
            "high_inr": ps_high
        })
        
    res.sort(key=lambda x: abs(x["high_inr"] - x["low_inr"]), reverse=True)
    return res
