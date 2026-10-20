"""Narratives for F-series entries (finance; rendered from result rows, no typed numbers)."""

from semantic_audit.common import f, inr_cr, names, num, pct, signed_pct, total  # noqa: F401


def _g(r, k, d=None):
    v = (r or {}).get(k)
    return d if v is None else v


def _first(rows, key, val):
    for r in rows:
        if r.get(key) == val:
            return r
    return {}


def _usd(x, dp=2):
    return "n/a" if x is None else f"${float(x):,.{dp}f}"


# ------------------------------------------------------------------ F1 lifting cost
def _f1(rows):
    if not rows:
        return "No producing-asset lifting cost rows were returned for FY26."
    avg = _g(rows[0], "company_avg_usd_boe")
    above = [r for r in rows if r.get("above_company_avg")]
    top = rows[0]
    low = rows[-1]
    return (f"In FY26, {len(above)} of {len(rows)} producing assets had lifting cost above the production-weighted "
            f"company average of {_usd(avg)}/BOE: {names(above, 'asset_name', len(above))}. "
            f"{top['asset_name']} is the clear outlier at {_usd(top['lifting_cost_usd_boe'])}/BOE "
            f"(₹{num(top['lifting_cost_inr_boe'])}/BOE on only {f(top['production_mmboe'], 2)} MMboe), against "
            f"{_usd(low['lifting_cost_usd_boe'])}/BOE at {low['asset_name']}. "
            "Lifting cost is opex divided by BOE produced, weighted by production (field lines only); the high-volume "
            "offshore assets therefore pull the company average down.")


def _f1_dd(rows):
    if not rows:
        return "No cost components were returned for the highest-cost asset."
    a = rows[0]
    asked = {"power_fuel": "power & fuel", "workover_repairs": "workover & repairs", "chemicals_consumables": "chemicals",
             "water_handling": "water handling"}
    asked_rows = [r for r in rows if r.get("component") in asked]
    asked_txt = ", ".join(f"{asked[r['component']]} {_usd(r['component_usd_boe'])}" for r in asked_rows)
    asked_share = total(asked_rows, "share_of_opex_pct")
    return (f"{a['asset_name']}, the highest-cost asset at {_usd(a['asset_lifting_cost_usd_boe'])}/BOE in FY26, spends most of its "
            f"{inr_cr(a['total_opex_inr_cr'], 1)} opex on {a['component'].replace('_', ' ')} "
            f"({inr_cr(a['cost_inr_cr'], 1)}, {pct(a['share_of_opex_pct'])}, {_usd(a['component_usd_boe'])}/BOE). "
            f"The operational components asked about are small by comparison - {asked_txt} per BOE - together only "
            f"{pct(asked_share)} of opex" + (", so the cost problem is fixed manpower spread over low volume, not field operations. " if a.get('component') == 'manpower_allocated' else ". ") +
            "There is no separate surface-repair line; repairs are included in workover & repairs.")


def _f1_why(rows):
    out = []
    for nm in sorted({r["short_name"] for r in rows}):
        rs = [r for r in rows if r["short_name"] == nm]
        a, b = rs[0], rs[-1]
        out.append((nm, a, b))
    if not out:
        return "No Cambay/Mehsana lifting cost rows were returned."
    parts = [f"{nm} ₹{num(a['lifting_cost_inr_boe'])}→₹{num(b['lifting_cost_inr_boe'])}/BOE "
             f"({signed_pct((b['lifting_cost_inr_boe'] - a['lifting_cost_inr_boe']) * 100 / a['lifting_cost_inr_boe'])})"
             for nm, a, b in out]
    drv = [f"{nm} production {f(a['production_mmboe'], 2)}→{f(b['production_mmboe'], 2)} MMboe "
           f"({signed_pct((b['production_mmboe'] - a['production_mmboe']) * 100 / a['production_mmboe'])}) while opex moved only "
           f"{inr_cr(a['total_opex_cr'], 0)}→{inr_cr(b['total_opex_cr'], 0)} and water cut rose {f(a['water_cut_pct'])}%→{f(b['water_cut_pct'])}%"
           for nm, a, b in out]
    usd = "; ".join(f"{nm} {_usd(a['lifting_cost_usd_boe'])}→{_usd(b['lifting_cost_usd_boe'])}" for nm, a, b in out)
    return (f"Lifting cost in rupee terms rose between {out[0][1]['fiscal_year']} and {out[0][2]['fiscal_year']}: {'; '.join(parts)}. "
            f"The cause is a largely fixed cost base spread over declining output - {'; '.join(drv)}. "
            f"In dollars the rise is masked by rupee depreciation ({usd} per BOE), so the trend should be tracked in ₹/BOE.")


def _f1_cmp(rows):
    mh = _first(rows, "segment", "1. Mumbai High")
    on = _first(rows, "segment", "3. Onshore assets")
    off = _first(rows, "segment", "2. Other offshore assets")
    co = _first(rows, "segment", "4. All fields (company)")
    if not mh:
        return "Mumbai High lifting cost was not returned."
    return (f"Mumbai High's FY26 lifting cost of {_usd(mh['lifting_cost_usd_boe'])}/BOE is "
            f"{_usd(abs(mh['gap_vs_benchmark_usd']))} below the {_usd(mh['benchmark_usd_boe'])} benchmark, roughly level with onshore assets "
            f"({_usd(_g(on, 'lifting_cost_usd_boe'))}) and above the other offshore assets ({_usd(_g(off, 'lifting_cost_usd_boe'))}). "
            f"The production-weighted field average is {_usd(_g(co, 'lifting_cost_usd_boe'))}/BOE, also under the benchmark, "
            f"so every segment beats it on a field basis. "
            f"Note the reported corporate lifting cost is {_usd(mh['reported_corporate_lifting_usd_boe'])}/BOE because it also carries "
            "plant, corporate and overhead costs not allocated to fields.")


# ------------------------------------------------------------------ F2 capex
def _f2(rows):
    if not rows:
        return "No FY27 capex rows were returned."
    be, re_, act = total(rows, "be_ytd_cr"), total(rows, "re_ytd_cr"), total(rows, "actual_ytd_cr")
    top = rows[0]
    over = [r for r in rows if (r.get("variance_vs_be_cr") or 0) > 0]
    months = max(int(r.get("months_covered") or 0) for r in rows)
    worst = sorted(rows, key=lambda r: r.get("variance_vs_be_cr") or 0)[0]
    return (f"FY27 year-to-date ({months} months to September 2026) capex is {inr_cr(act)} against a phased BE of {inr_cr(be)} "
            f"and RE of {inr_cr(re_)} - utilisation {pct(act * 100 / be if be else None)} of BE and {pct(act * 100 / re_ if re_ else None)} of RE. "
            f"{top['asset_name']} dominates spend ({inr_cr(top['actual_ytd_cr'])}, {pct(top['utilisation_vs_be_pct'])} of BE) and carries the largest "
            f"shortfall ({inr_cr(worst['variance_vs_be_cr'], 1)} vs BE). "
            f"Only {len(over)} of {len(rows)} asset/work centres are running above BE (including {names(over, 'asset_name', 4)}).")


def _f2_dd(rows):
    if not rows:
        return "No project variances were returned."
    off_u = [r for r in rows if r["segment"] == "offshore" and r["direction"] == "underspend"]
    on_u = [r for r in rows if r["segment"] == "onshore" and r["direction"] == "underspend"]
    ov = sorted([r for r in rows if r["direction"] == "overspend"], key=lambda r: -r["variance_vs_be_cr"])
    s1 = (f"The largest FY27 YTD deviation is an underspend: {off_u[0]['project_name']} ({off_u[0]['asset_name']}) is "
          f"{inr_cr(abs(off_u[0]['variance_vs_be_cr']), 1)} ({pct(off_u[0]['variance_vs_be_pct'])}) below BE.") if off_u else ""
    s2 = (f" Onshore, the biggest gap is {on_u[0]['project_name']} at {inr_cr(on_u[0]['variance_vs_be_cr'], 1)} "
          f"({pct(on_u[0]['variance_vs_be_pct'])}).") if on_u else ""
    s3 = (f" Overspends are marginal - the largest is {ov[0]['project_name']} at +{inr_cr(ov[0]['variance_vs_be_cr'], 1)} "
          f"({signed_pct(ov[0]['variance_vs_be_pct'])}) - so the portfolio risk is slow execution, not cost blow-outs.") if ov else ""
    return (s1 + s2 + s3).strip()


def _f2_why(rows):
    if not rows:
        return "No Eastern Offshore project progress rows were returned."
    p = rows[0]
    rc = sorted({str(r.get("delay_root_cause")) for r in rows})
    return (f"Eastern Offshore's capex slippage is concentrated in {p['project_name']}: recorded root cause "
            f"'{p['delay_root_cause']}', {num(p['slippage_months'])} months' slippage, {p['delayed_milestones']} milestones on the critical "
            f"path ({p['delayed_milestone_names']}) and a cost overrun of {inr_cr(p['cost_overrun_cr'], 1)} "
            f"({inr_cr(p['sanctioned_cost_cr'])} → {inr_cr(p['revised_cost_cr'], 1)}). "
            f"It has spent {pct(p['fy27_utilisation_vs_be_pct'])} of its FY27 YTD BE ({inr_cr(p['fy27_actual_ytd_cr'], 1)} of "
            f"{inr_cr(p['fy27_be_ytd_cr'], 1)}). "
            f"The data records only these root causes for the asset: {', '.join(rc)}; procurement delays, rig mobilisation and "
            "environmental clearances are not captured as causes, so they cannot be confirmed as drivers.")


def _f2_cmp(rows):
    cur = [r for r in rows if r.get("full_year_actual_cr") is None]
    hist = [r for r in rows if r.get("full_year_actual_cr") is not None]
    if not cur or not hist:
        return "Insufficient H1 history to compare the burn rate."
    c = cur[-1]
    last = hist[-1]
    shares = [r["h1_share_of_full_year_pct"] for r in hist]
    utils = [r["h1_utilisation_vs_be_pct"] for r in hist]
    return (f"FY27 capex at end-Q2 is {inr_cr(c['h1_actual_cr'])}, {pct(c['h1_utilisation_vs_be_pct'])} of the H1 BE - in line with the "
            f"historical curve, where H1 utilisation ran {pct(min(utils))}-{pct(max(utils))} in {hist[0]['fiscal_year']}-{last['fiscal_year']}. "
            f"H1 has consistently delivered {pct(min(shares))}-{pct(max(shares))} of full-year spend, so the current pace points to a full year "
            f"of roughly twice the H1 figure; FY27 H1 is also {signed_pct((c['h1_actual_cr'] - last['h1_actual_cr']) * 100 / last['h1_actual_cr'])} "
            f"vs {last['fiscal_year']} H1 ({inr_cr(last['h1_actual_cr'])}). "
            + ("The capex phasing in the data is nearly flat month to month, so there is no back-ended Q4 surge to plan around."
               if max(shares) - min(shares) < 5 else "Historical H1 shares vary, so the full-year outturn is uncertain."))


# ------------------------------------------------------------------ F3 field P&L
def _f3(rows):
    if not rows:
        return "No field P&L rows were returned."
    yrs = sorted({r["fiscal_year"] for r in rows})
    by = {y: [r for r in rows if r["fiscal_year"] == y] for y in yrs}
    y0, y1 = yrs[0], yrs[-1]
    r0, r1 = total(by[y0], "gross_revenue_inr_cr"), total(by[y1], "gross_revenue_inr_cr")
    e0, e1 = total(by[y0], "ebitda_inr_cr"), total(by[y1], "ebitda_inr_cr")
    o1 = total(by[y1], "total_opex_inr_cr")
    fields = sorted({r["field_name"] for r in rows})
    cum = {}
    for r in rows:
        cum[r["field_name"]] = cum.get(r["field_name"], 0) + (r.get("ebitda_inr_cr") or 0)
    best = max(cum, key=cum.get)
    neg = sorted([r for r in by[y1] if (r.get("ebitda_inr_cr") or 0) < 0], key=lambda r: r["ebitda_inr_cr"])
    s3 = (f" In {y1}, {len(neg)} fields had negative EBITDA (worst {neg[0]['field_name']}, {inr_cr(neg[0]['ebitda_inr_cr'], 1)})."
          if neg else f" No field had negative EBITDA in {y1}.")
    return (f"Across {len(fields)} producing fields, revenue moved from {inr_cr(r0)} in {y0} to {inr_cr(r1)} in {y1} and EBITDA from "
            f"{inr_cr(e0)} to {inr_cr(e1)} ({pct(e1 * 100 / r1 if r1 else None)} margin in {y1}, on opex of {inr_cr(o1)}). "
            f"{best} generated the most EBITDA over the five years ({inr_cr(cum[best])}).{s3} "
            "Field revenue excludes plant/VAP and corporate lines, so it is below the company's standalone revenue.")


def _f3_dd(rows):
    if not rows:
        return "No field improved its EBITDA margin while production declined between FY22 and FY26."
    t = rows[0]
    big = sorted(rows, key=lambda r: -(r.get("ebitda_fy26_cr") or 0))[0]
    mature = [r for r in rows if r.get("maturity") == "mature"]
    return (f"{len(rows)} fields raised their EBITDA margin between FY22 and FY26 even though production fell, {len(mature)} of them "
            f"classed mature. The largest gain is {t['field_name']} ({t['asset_name']}): margin {pct(t['ebitda_margin_fy22_pct'])} → "
            f"{pct(t['ebitda_margin_fy26_pct'])} despite production {signed_pct(t['production_change_pct'])}; the biggest contributor in "
            f"absolute terms is {big['field_name']} ({inr_cr(big['ebitda_fy26_cr'], 1)} FY26 EBITDA, {signed_pct(big['margin_change_pp'])[:-1]} pp). "
            "Production decline is used as the proxy for reservoir-pressure decline (no pressure data exists).")


def _f3_why(rows):
    if len(rows) < 2:
        return "Insufficient mature onshore history."
    pk = max(rows, key=lambda r: r["ebitda_margin_pct"])
    after = [r for r in rows if r["fiscal_year"] > pk["fiscal_year"]]
    tr = min(after, key=lambda r: r["ebitda_margin_pct"]) if after else rows[-1]
    last = rows[-1]
    wo = [r["workover_cr"] for r in rows]
    return (f"Mature onshore EBITDA margin compressed from {pct(pk['ebitda_margin_pct'])} in {pk['fiscal_year']} to "
            f"{pct(tr['ebitda_margin_pct'])} in {tr['fiscal_year']}, driven by statutory levies and price, not workover. "
            f"Levies rose from {pct(pk['levies_pct_revenue'])} to {pct(tr['levies_pct_revenue'])} of revenue as windfall tax "
            f"({inr_cr(tr['saed_windfall_cr'])}) was added to cess ({inr_cr(tr['cess_cr'])}), while Brent eased from "
            f"{_usd(pk['brent_usd_bbl'], 1)} to {_usd(tr['brent_usd_bbl'], 1)} and opex per BOE rose ₹{num(pk['opex_inr_per_boe'])}→"
            f"₹{num(tr['opex_inr_per_boe'])} on lower volume. "
            f"Workover cost was flat at {inr_cr(min(wo))}-{inr_cr(max(wo))} a year; in {last['fiscal_year']} margin recovered to "
            f"{pct(last['ebitda_margin_pct'])} once SAED fell away, despite Brent at {_usd(last['brent_usd_bbl'], 1)}.")


def _f3_cmp(rows):
    wo = _first(rows, "segment", "Western Offshore")
    og = _first(rows, "segment", "Onshore Gujarat")
    if not wo or not og:
        return "Both segments were not returned."
    return (f"Over FY22-FY26 Western Offshore generated {inr_cr(wo['revenue_5yr_cr'])} revenue and {inr_cr(wo['ebitda_ocf_proxy_5yr_cr'])} "
            f"EBITDA, about {f(wo['revenue_5yr_cr'] / og['revenue_5yr_cr'], 1)}x Onshore Gujarat's {inr_cr(og['revenue_5yr_cr'])} and "
            f"{inr_cr(og['ebitda_ocf_proxy_5yr_cr'])}. "
            f"Onshore Gujarat is the more profitable per barrel - {pct(og['ebitda_margin_pct'])} margin and ₹{num(og['ebitda_inr_per_boe'])}/BOE "
            f"vs {pct(wo['ebitda_margin_pct'])} and ₹{num(wo['ebitda_inr_per_boe'])}/BOE offshore - while offshore wins on scale "
            f"({f(wo['production_5yr_mmboe'], 1)} vs {f(og['production_5yr_mmboe'], 1)} MMboe). "
            "Operating cash flow is proxied by EBITDA; field-level cash-flow data is not available.")


# ------------------------------------------------------------------ F4 levies
def _f4(rows):
    cur = rows[0] if rows else None
    if not cur:
        return "No realisation data returned."
    prev = rows[1] if len(rows) > 1 else {}
    saed_yr = next((r for r in rows if (r.get("saed_windfall_usd_bbl") or 0) > 0), None)
    s3 = (f" In {saed_yr['fiscal_year']}, windfall tax added {_usd(saed_yr['saed_windfall_usd_bbl'])}/bbl and total levies took "
          f"{pct(saed_yr['levies_pct_of_realisation'])}.") if saed_yr else ""
    return (f"In {cur['fiscal_year']} to date ({cur['months_covered']} months), royalty, OIDB cess and windfall tax cut ONGC's crude "
            f"realisation by {_usd(cur['total_levies_usd_bbl'])}/bbl (₹{num(cur['total_levies_inr_bbl'])}/bbl), from "
            f"{_usd(cur['gross_realisation_usd_bbl'])} to {_usd(cur['post_levy_realisation_usd_bbl'])} - {pct(cur['levies_pct_of_realisation'])} "
            f"of the barrel. "
            f"Cess is the larger levy ({_usd(cur['oidb_cess_usd_bbl'])}) ahead of royalty ({_usd(cur['royalty_usd_bbl'])}); windfall tax is "
            f"{_usd(cur['saed_windfall_usd_bbl'])} since its removal. "
            f"That is in line with {_g(prev, 'fiscal_year', 'last year')} ({_usd(_g(prev, 'total_levies_usd_bbl'))}/bbl).{s3}")


def _f4_dd(rows):
    if not rows:
        return "No FY27 monthly levy data returned."
    n = len(rows)
    cess = total(rows, "oidb_cess_usd_bbl") / n
    roy = total(rows, "royalty_usd_bbl") / n
    ref = total(rows, "cess_at_rs10000_per_mt_usd_bbl") / n
    cp = total(rows, "cess_pct_of_realisation") / n
    rp = total(rows, "royalty_pct_of_realisation") / n
    return (f"In FY27 to date ({rows[0]['month']} to {rows[-1]['month']}), OIDB cess averaged {_usd(cess)}/bbl ({pct(cp)} of gross crude "
            f"realisation) and royalty {_usd(roy)}/bbl ({pct(rp)}), together {_usd(cess + roy)} off every barrel. "
            f"A ₹10,000/MT specific cess would be {_usd(ref)}/bbl at the same exchange rates, so the ad-valorem cess in the data is "
            f"{_usd(ref - cess)}/bbl lighter at current prices. "
            "Conversion uses 7.33 bbl per tonne and each month's INR/USD rate.")


def _f4_why(rows):
    lev = [r for r in rows if (r.get("months_saed_levied") or 0) > 0]
    if not lev:
        return "No SAED levy months were found in the data."
    hi = max(lev, key=lambda r: r["avg_saed_usd_bbl"])
    lo = min(lev, key=lambda r: r["avg_saed_usd_bbl"])
    last = lev[-1]
    return (f"The data shows SAED tracking international crude prices: it averaged {_usd(hi['avg_saed_usd_bbl'])}/bbl (peak "
            f"{_usd(hi['max_saed_usd_bbl'])}) in {hi['fiscal_year']} when Brent averaged {_usd(hi['avg_brent_usd_bbl'], 1)}, and fell to "
            f"{_usd(lo['avg_saed_usd_bbl'])} in {lo['fiscal_year']} with Brent at {_usd(lo['avg_brent_usd_bbl'], 1)}, until the last levy "
            f"month {last['last_month_levied']}. "
            f"That pattern is consistent with a windfall levy reset periodically against benchmark prices; it cost "
            f"{inr_cr(hi['saed_booked_inr_cr'])} in {hi['fiscal_year']} ({pct(hi['saed_share_of_levies_pct'])} of statutory levies) and "
            f"{inr_cr(last['saed_booked_inr_cr'])} in {last['fiscal_year']}. "
            "The document corpus holds no SAED notification or statutory text, so the legal basis and revision rules cannot be cited.")


def _f4_cmp(rows):
    nom = next((r for r in rows if str(r.get("regime", "")).startswith("Nomination")), None)
    jv = next((r for r in rows if not str(r.get("regime", "")).startswith("Nomination")), None)
    if not nom:
        return "Nomination field data not returned."
    s2 = (f" The only non-nomination fields in the data, the {jv['fields']} Panna-Mukta joint-venture fields, paid "
          f"{pct(jv['govt_take_pct_fy26'])} ({pct(jv['govt_take_pct_fy22_fy26'])} over five years), mostly from a higher cess share "
          f"({pct(jv['cess_pct_fy26'])} vs {pct(nom['cess_pct_fy26'])}).") if jv else ""
    return (f"Statutory government take on ONGC nomination fields was {pct(nom['govt_take_pct_fy26'])} of gross revenue in FY26 "
            f"(royalty {pct(nom['royalty_pct_fy26'])} + cess {pct(nom['cess_pct_fy26'])}), and {pct(nom['govt_take_pct_fy22_fy26'])} over "
            f"FY22-FY26 including windfall tax.{s2} "
            "NELP/HELP blocks, profit petroleum and revenue-share payments are not in the data, so a true NELP/HELP comparison "
            "cannot be made; these figures cover royalty, cess and SAED only.")


# ------------------------------------------------------------------ F5 procurement
def _f5(rows):
    if not rows:
        return "No vendor spend rows returned."
    last = rows[-1]
    tot = _g(rows[0], "total_paid_all_vendors_cr")
    top80 = total(rows, "paid_fy26_cr")
    ov = total(rows, "cost_overrun_cr")
    tov = _g(rows[0], "total_overrun_all_vendors_cr")
    worst = sorted(rows, key=lambda r: -(r.get("cost_overrun_cr") or 0))[:3]
    return (f"{len(rows)} of {num(_g(rows[0], 'total_vendors'))} vendors account for the top 80% of FY26 contract spend "
            f"({inr_cr(top80)} of {inr_cr(tot)}; cumulative {pct(last['cum_share_pct'])} at the cut-off), led by "
            f"{names(rows, 'vendor_name', 3)}. "
            f"Spend is unusually flat - the largest vendor holds only {pct(rows[0]['cum_share_pct'])} - so there is no small set of dominant contracts. "
            f"Cost overruns (revised minus original PO) total {inr_cr(tov, 1)}, of which {inr_cr(ov, 1)} sits in this top-80% group; the largest are "
            f"{', '.join(w['vendor_name'] + ' ' + inr_cr(w['cost_overrun_cr'], 1) for w in worst)}.")


def _f5_dd(rows):
    if not rows:
        return "No category rows returned."
    top3 = rows[:3]
    rig = next((r for r in rows if "Drilling Rigs" in str(r["service_contract_category"])), None)
    osv = next((r for r in rows if "OSV" in str(r["service_contract_category"])), None)
    ovr = sorted(rows, key=lambda r: -(r.get("cost_overrun_cr") or 0))[:3]
    return (f"Within the top-80% vendor group, spend is spread almost evenly across {len(rows)} service categories (each "
            f"{pct(rows[-1]['share_of_top80_spend_pct'])}-{pct(rows[0]['share_of_top80_spend_pct'])}); the largest are "
            + ", ".join(f"{r['service_contract_category']} ({inr_cr(r['paid_fy26_cr'])})" for r in top3) + ". "
            f"Rig charter ({inr_cr(_g(rig, 'paid_fy26_cr'))}) and OSV hire ({inr_cr(_g(osv, 'paid_fy26_cr'))}) are not dominant by spend, but "
            f"overruns concentrate in {', '.join(r['service_contract_category'] for r in ovr)}. "
            "Directional drilling is not a separate category in the purchase-order data.")


def _f5_why(rows):
    if not rows:
        return "No FY26 overrun lines returned."
    big = [r for r in rows if "Subsea" in str(r.get("overrun_reason"))]
    small = [r for r in rows if r not in big]
    bo, so = total(big, "cost_overrun_cr"), total(small, "cost_overrun_cr")
    sb = total(rows, "standby_charges_cr")
    t = rows[0]
    return (f"FY26 contract overruns were driven by scope variations: '{t['overrun_reason']}' accounts for {inr_cr(bo, 1)} across "
            f"{len(big)} categories ({', '.join(r['service_contract_category'] for r in big)}), averaging ~{pct(t['overrun_pct_of_original_po'])} "
            f"of the original PO on affected lines, versus {inr_cr(so, 1)} from minor site-engineer scope changes (~{pct(sum(float(r.get('overrun_pct_of_original_po') or 0) for r in small) / len(small)) if small else 'n/a'}). "
            f"Standby charges add a further {inr_cr(sb, 1)} but are billed outside the revised PO value. "
            + ("The 'subsea route realignment' reason is recorded even for non-subsea categories, which suggests a coding "
               "default rather than a true cause." if any('Subsea' not in str(r['service_contract_category']) for r in big) else ""))


def _f5_cmp(rows):
    a = _first(rows, "service_contract_category", "ALL CATEGORIES")
    if not a:
        return "No total row returned."
    return (f"FY26 contracts were committed {pct(a['po_vs_estimate_pct'], 2)} above the engineer's estimate ({inr_cr(a['original_po_cr'])} "
            f"vs {inr_cr(a['engineers_estimate_cr'])}), revised to {inr_cr(a['revised_po_cr'])}, and {inr_cr(a['actual_paid_cr'])} has been paid - "
            f"{pct(a['paid_pct_of_original_po'])} of the original commitment and {pct(a['paid_pct_of_estimate'])} of the estimate. "
            f"The PO-vs-estimate premium is {pct(min(r['po_vs_estimate_pct'] for r in rows), 2)} to {pct(max(r['po_vs_estimate_pct'] for r in rows), 2)} "
            f"in every one of the {len(rows) - 1} categories, so award premia rather than execution overruns are the main gap. "
            "All FY26 POs are still 'in execution', so paid-to-date understates final cost.")


# ------------------------------------------------------------------ F6 receivables
def _f6(rows):
    if not rows:
        return "No outstanding receivables returned."
    t = total(rows, "outstanding_cr")
    o90 = total(rows, "d91_180_cr") + total(rows, "d180_plus_cr")
    d30 = total(rows, "d0_30_cr")
    worst = max(rows, key=lambda r: r.get("over_90d_pct") or 0)
    omc = [r for r in rows if r["customer"] in ("IOCL", "BPCL", "HPCL")]
    return (f"Trade receivables of {inr_cr(t)} were outstanding at 31-Mar-2026 across {len(rows)} customers; {pct(d30 * 100 / t)} is under "
            f"30 days and {inr_cr(o90)} ({pct(o90 * 100 / t)}) is older than 90 days. "
            f"The largest balances are gas and fertiliser buyers ({names(rows, 'customer', 3)}); {worst['customer']} has the oldest mix "
            f"({pct(worst['over_90d_pct'])} beyond 90 days). "
            f"The three OMCs owe {inr_cr(total(omc, 'outstanding_cr'))}, of which {inr_cr(total(omc, 'd91_180_cr') + total(omc, 'd180_plus_cr'))} "
            "is over 90 days" + ("; every >90-day rupee is disputed." if abs(total(rows, 'disputed_cr') - o90) < 1 else
             f"; {inr_cr(total(rows, 'disputed_cr'))} is disputed."))


def _f6_dd(rows):
    if not rows:
        return "No dues beyond 90 days."
    t = total(rows, "over_90d_cr")
    gas = [r for r in rows if r["segment"].startswith("Gas")]
    omc = [r for r in rows if r["customer"] in ("IOCL", "BPCL", "HPCL")]
    return (f"{len(rows)} customers have dues beyond 90 days totalling {inr_cr(t, 1)}, led by {rows[0]['customer']} "
            f"({inr_cr(rows[0]['over_90d_cr'], 1)}), {rows[1]['customer']} and {rows[2]['customer']}. "
            f"Gas and other consumers hold {inr_cr(total(gas, 'over_90d_cr'), 1)} of it; the public-sector OMCs owe "
            + ", ".join(f"{r['customer']} {inr_cr(r['over_90d_cr'], 1)}" for r in omc) + ". "
            f"All of these balances are under dispute and {inr_cr(total(rows, 'over_180d_cr'), 1)} is older than 180 days.")


def _f6_why(rows):
    if not rows:
        return "No disputed receivables."
    t = rows[0]
    return (f"Billing disputes explain the aged receivables: gas GCV billing differentials and pipeline-metering reconciliation account for "
            f"{inr_cr(t['disputed_outstanding_cr'], 1)} ({pct(t['share_of_over_90d_pct'])} of >90-day dues) across {t['invoices']} invoices "
            f"and {t['customers']} customers, average age {num(t['avg_age_days'])} days. "
            + (f"Crude BS&W testing and transit-loss disputes add {inr_cr(rows[1]['disputed_outstanding_cr'], 1)} "
               f"({pct(rows[1]['share_of_over_90d_pct'])}). " if len(rows) > 1 else "")
            + "No subsidy-settlement or price-pooling reason is recorded, so those cannot be confirmed as causes.")


def _f6_cmp(rows):
    cur = rows[-1] if rows else None
    if not cur:
        return "No DSO data returned."
    hist = [r for r in rows[:-1] if r.get("avg_collection_days") is not None]
    hs = [r["avg_collection_days"] for r in hist]
    return (f"FY26 year-end DSO is {f(cur['dso_days'])} days ({inr_cr(cur['year_end_outstanding_cr'])} outstanding on "
            f"{inr_cr(cur['billed_cr'])} billed), about {f((cur['dso_days'] or 0) - cur['avg_collection_days'])} days above the actual "
            f"collection period of {f(cur['avg_collection_days'])} days. "
            + (f"Historically collections took {f(min(hs))}-{f(max(hs))} days against {num(cur['credit_terms_days'])}-day terms, so the "
               "FY26 balance reflects the disputed tail rather than slower routine payment. " if hs else "")
            + "Prior year-end balances were not retained and no treasury DSO target exists in the data, so the target comparison is a gap.")


# ------------------------------------------------------------------ F7 employee cost
def _f7(rows):
    if not rows:
        return "No asset employee-cost rows returned."
    t = rows[0]
    low = rows[-1]
    mp, rv = total(rows, "manpower_cost_fy26_cr"), total(rows, "revenue_fy26_cr")
    up = [r for r in rows if r.get("pct_fy24") is not None and r.get("pct_fy26") is not None and r["pct_fy26"] > r["pct_fy24"]]
    return (f"Allocated employee cost was {pct(mp * 100 / rv if rv else None)} of field revenue across producing assets in FY26, ranging "
            f"from {pct(t['pct_fy26'])} at {t['asset_name']} to {pct(low['pct_fy26'])} at {low['asset_name']}. "
            f"The ratio fell sharply after FY21 as oil prices recovered ({t['asset_name']} {pct(t['pct_fy21'])} → {pct(t['pct_fy26'])}), but "
            f"has crept up again since FY24 at {len(up)} of {len(rows)} assets as revenue softened. "
            + ("Small onshore assets carry the highest ratios; offshore assets stay in single digits."
               if all((r.get('pct_fy26') or 0) < 10 for r in rows if r.get('onshore_offshore') == 'offshore')
               else "Small onshore assets carry the highest ratios."))


def _f7_dd(rows):
    if not rows:
        return "No mature onshore field exceeds 25% employee cost to revenue in FY26."
    assets = {}
    for r in rows:
        assets.setdefault(r["asset_name"], r)
    over_asset = [a for a, r in assets.items() if (r.get("asset_manpower_pct_revenue") or 0) > 25]
    return (f"{len(rows)} mature onshore fields exceed the 25% threshold in FY26: "
            + ", ".join(f"{r['field_name']} ({r['asset_name']}, {pct(r['manpower_pct_revenue'])})" for r in rows) + ". "
            f"At asset level only {', '.join(over_asset) if over_asset else 'none'} breach{'es' if len(over_asset) == 1 else ''} it "
            f"({pct(assets[over_asset[0]]['asset_manpower_pct_revenue']) if over_asset else ''} on {inr_cr(assets[over_asset[0]]['asset_revenue_fy26_cr']) if over_asset else ''} revenue). "
            "These are the low-revenue fields where manpower redeployment would move the ratio most.")


def _f7_why(rows):
    on0 = next((r for r in rows if r["onshore_offshore"] == "onshore" and r["fiscal_year"] == "FY22"), None)
    on1 = next((r for r in rows if r["onshore_offshore"] == "onshore" and r["fiscal_year"] == "FY26"), None)
    of0 = next((r for r in rows if r["onshore_offshore"] == "offshore" and r["fiscal_year"] == "FY22"), None)
    of1 = next((r for r in rows if r["onshore_offshore"] == "offshore" and r["fiscal_year"] == "FY26"), None)
    if not all([on0, on1, of0, of1]):
        return "Insufficient onshore/offshore data."
    return (f"Per barrel, onshore manpower cost rose from ₹{num(on0['manpower_inr_per_boe'])} to ₹{num(on1['manpower_inr_per_boe'])}/BOE "
            f"between FY22 and FY26 while offshore fell from ₹{num(of0['manpower_inr_per_boe'])} to ₹{num(of1['manpower_inr_per_boe'])}, because "
            f"onshore production dropped {f(on0['production_mmboe'])}→{f(on1['production_mmboe'])} MMboe while offshore held at "
            f"~{f(of1['production_mmboe'])} MMboe. "
            f"Offshore platforms produce {num(of1['boe_per_employee'])} BOE per employee against {num(on1['boe_per_employee'])} onshore, so the "
            f"same pay increases weigh about {f(of1['boe_per_employee'] / on1['boe_per_employee'], 1)}x as heavily on onshore barrels. "
            f"Measured against revenue the ratio actually fell in both segments (onshore {pct(on0['manpower_pct_revenue'])}→"
            f"{pct(on1['manpower_pct_revenue'])}, offshore {pct(of0['manpower_pct_revenue'])}→{pct(of1['manpower_pct_revenue'])}) as prices rose, "
            "so the 'faster rise' holds per BOE, not per rupee of revenue.")


def _f7_cmp(rows):
    if not rows:
        return "No corporate ratio data."
    cur = rows[-1]
    hi = max(rows, key=lambda r: r["employee_cost_ratio_pct"])
    lo = min(rows, key=lambda r: r["employee_cost_ratio_pct"])
    return (f"ONGC's standalone employee cost was {pct(cur['employee_cost_ratio_pct'], 2)} of gross revenue in {cur['fiscal_year']}, near the "
            f"bottom of its own {rows[0]['fiscal_year']}-{cur['fiscal_year']} range ({pct(lo['employee_cost_ratio_pct'], 2)} in {lo['fiscal_year']} to "
            f"{pct(hi['employee_cost_ratio_pct'], 2)} in {hi['fiscal_year']}). "
            "The ratio moves mainly with oil-price-driven revenue rather than headcount. "
            "No global national oil company benchmark is held in the data, so the external comparison cannot be made from the warehouse.")


# ------------------------------------------------------------------ F8 reserves
def _f8(rows):
    allb = _first(rows, "basin_name", "ALL BASINS")
    b = [r for r in rows if r.get("basin_name") != "ALL BASINS"]
    if not b:
        return "No basin reserve rows returned."
    t = b[0]
    low = min(b, key=lambda r: r["fd_cost_usd_boe"])
    return (f"In FY26 ONGC replaced {f(_g(allb, 'rrr_2p'), 2)}x its production with 2P reserves ({f(_g(allb, 'reserve_accretion_2p_mmtoe'), 2)} "
            f"MMTOE accreted vs {f(_g(allb, 'production_mmtoe'), 2)} produced) at a finding & development cost of "
            f"{_usd(_g(allb, 'fd_cost_usd_boe'))}/BOE. "
            f"{t['basin_name']} is the most expensive basin at {_usd(t['fd_cost_usd_boe'])}/BOE (finding {_usd(t['finding_cost_usd_boe'])} + "
            f"development {_usd(t['development_cost_usd_boe'])}); {low['basin_name']} is cheapest at {_usd(low['fd_cost_usd_boe'])}. "
            f"Every basin's RRR sits between {f(min(r['rrr_2p'] for r in b), 2)} and {f(max(r['rrr_2p'] for r in b), 2)}, all above 1.0.")


def _f8_dd(rows):
    if not rows:
        return "No basin finding-cost rows returned."
    kg = next((r for r in rows if "Krishna" in r["basin_name"]), None)
    wo = next((r for r in rows if "Western" in r["basin_name"]), None)
    aa = next((r for r in rows if "Assam" in r["basin_name"]), None)
    return (f"On a 3-year trailing basis (FY24-FY26) Krishna-Godavari's finding cost is {_usd(_g(kg, 'trailing_3yr_finding_cost_usd_boe'))}/BOE, "
            f"versus {_usd(_g(wo, 'trailing_3yr_finding_cost_usd_boe'))} for Western Offshore and {_usd(_g(aa, 'trailing_3yr_finding_cost_usd_boe'))} "
            "for Assam-Arakan. "
            f"KG is falling fast ({_usd(_g(kg, 'fc_fy24_usd_boe'))} → {_usd(_g(kg, 'fc_fy26_usd_boe'))}) as accretion scales up, while Western "
            f"Offshore ({_usd(_g(wo, 'fc_fy24_usd_boe'))} → {_usd(_g(wo, 'fc_fy26_usd_boe'))}) and Assam-Arakan are creeping up. "
            "Western Offshore wells are classified shallow-offshore in the drilling data; KG is the deepwater basin.")


def _f8_why(rows):
    if not rows:
        return "No exploratory wells returned."
    t = rows[0]
    tot_dry = total(rows, "dry_hole_cost_cr")
    wo = next((r for r in rows if "Western" in r["basin_name"]), {})
    return (f"Exploration cost is highest where wells are deepest and dry-hole rates highest: in {t['basin_name']} ({t['terrain']}) an "
            f"exploratory well averaged {inr_cr(t['avg_cost_per_well_cr'], 1)} at {num(t['avg_depth_m'])} m, and {pct(t['dry_hole_rate_pct'])} of "
            f"{t['exploratory_wells']} wells in FY24-FY26 were dry, writing off {inr_cr(t['dry_hole_cost_cr'])}. "
            f"Across all basins dry holes cost {inr_cr(tot_dry)}, the largest share in Western Offshore ({inr_cr(_g(wo, 'dry_hole_cost_cr'))}). "
            "There is no HP-HT flag in the well data, so the HP-HT effect cannot be isolated; depth and terrain are the available proxies.")


def _f8_cmp(rows):
    if not rows:
        return "No RRR history."
    cur = rows[-1]
    below = total(rows, "basins_below_target")
    return (f"ONGC's 2P reserve replacement ratio has stayed above the 1.0 target every year from {rows[0]['fiscal_year']} to "
            f"{cur['fiscal_year']}, reaching {f(cur['company_rrr_2p'], 2)} in {cur['fiscal_year']}. "
            f"{'No basin' if below == 0 else num(below) + ' basin-years'} fell below 1.0; the weakest basin in {cur['fiscal_year']} was "
            f"{cur['min_basin']} at {f(cur['min_basin_rrr'], 2)}. "
            + ("RRR is so uniform across basins and years that it looks modelled rather than observed; treat it as indicative."
               if max(r['max_basin_rrr'] - r['min_basin_rrr'] for r in rows) < 0.1 else ""))


# ------------------------------------------------------------------ F9 forex
def _f9(rows):
    a = _first(rows, "currency_pair", "ALL CURRENCIES")
    usd = _first(rows, "currency_pair", "USD/INR")
    if not a:
        return "No hedge book returned."
    ccy = [r for r in rows if r.get("currency_pair") not in ("ALL CURRENCIES",)]
    weak = min(ccy, key=lambda r: r["hedge_ratio_pct"])
    return (f"ONGC's FY26 active forex book is ${f(a['gross_exposure_usd_mn'], 1)} mn of exposure, {pct(a['hedge_ratio_pct'])} hedged, leaving "
            f"${f(a['unhedged_usd_mn'], 1)} mn open. "
            f"Dollar exposure (${f(_g(usd, 'gross_exposure_usd_mn'), 1)} mn) is {pct(_g(usd, 'hedge_ratio_pct'))} covered, mostly by the natural hedge "
            f"of dollar crude sales (${f(_g(usd, 'natural_hedge_usd_mn'), 1)} mn) rather than derivatives (${f(_g(usd, 'derivative_hedged_usd_mn'), 1)} mn). "
            f"The weakest cover is {weak['currency_pair']} at {pct(weak['hedge_ratio_pct'])}; the book's MTM is {inr_cr(a['mtm_gain_loss_inr_cr'], 1)}.")


def _f9_dd(rows):
    t = _first(rows, "contract_category", "TOTAL (3 categories)")
    cats = [r for r in rows if r is not t]
    if not t:
        return "No USD contract exposure returned."
    w = cats[0] if cats else {}
    return (f"Net unhedged USD liability across charter hire, EPC and equipment imports is ${f(t['unhedged_usd_mn'], 1)} mn "
            f"({inr_cr(t['unhedged_inr_cr'])} at ₹{f(t['fx_rate_used'], 2)}/$), on ${f(t['gross_exposure_usd_mn'], 1)} mn gross exposure "
            f"({pct(t['hedge_ratio_pct'])} hedged). "
            f"Almost all of it sits in {w.get('contract_category')} contracts - ${f(w.get('unhedged_usd_mn'), 1)} mn unhedged, only "
            f"{pct(w.get('hedge_ratio_pct'))} covered - while "
            + " and ".join(f"{r['contract_category']} (${f(r['unhedged_usd_mn'], 1)} mn open)" for r in cats[1:]) + " are well covered.")


def _f9_why(rows):
    if not rows:
        return "No governing document found."
    docs = ", ".join(str(r.get("doc_id")) for r in rows)
    return (f"No Board-approved hedging policy or treasury risk-limit document exists in the corpus; the only governing provision found ({docs}) "
            f"is the DPE corporate-governance requirement that '{str(rows[0].get('quote_snippet', '')).strip()}' be placed before the Board. "
            "That makes quarterly Board reporting of forex exposure and mitigation steps the documented control, but hedge-ratio "
            "bands, tenor limits and approved instruments are not specified anywhere in the available documents.")


def _f9_cmp(rows):
    r = rows[0] if rows else None
    if not r:
        return "No data."
    return (f"Dollar crude sales of about ${num(r['crude_revenue_fy26_usd_mn'])} mn in FY26 ({inr_cr(r['crude_revenue_fy26_inr_cr'])}) are "
            f"{f(r['crude_usd_cover_of_exposure_x'], 1)}x the entire ${num(r['fx_exposure_usd_mn'])} mn forex exposure book, so the natural "
            f"hedge comfortably exceeds the ${num(r['natural_hedge_designated_usd_mn'])} mn formally designated against it. "
            f"INR/USD moved only {f(r['fx_min_fy26'], 2)}-{f(r['fx_max_fy26'], 2)} in FY26 (volatility {pct(r['fx_volatility_pct'], 2)}): that range "
            f"swings the ${num(r['unhedged_usd_mn'])} mn unhedged book by about {inr_cr(r['unhedged_impact_of_fy26_fx_range_inr_cr'])}, against "
            f"{inr_cr(r['crude_revenue_swing_of_fy26_fx_range_inr_cr'])} on crude revenue. "
            "The USD content of opex and capex is not recorded, so exposure is measured from the hedge book only.")


# ------------------------------------------------------------------ F10 quarterly P&L
def _quarters(rows):
    qs = {}
    for r in rows:
        q = qs.setdefault(r["quarter"], {"rev": 0.0, "ebitda": 0.0, "pbt": 0.0})
        q["rev"] += r.get("gross_revenue_cr") or 0
        q["ebitda"] += r.get("ebitda_cr") or 0
        q["pbt"] += r.get("pbt_cr") or 0
    return qs


def _f10(rows):
    if not rows:
        return "No quarterly P&L rows returned."
    qs = _quarters(rows)
    order = sorted(qs)
    assets = []
    for r in rows:
        if r["asset_name"] not in assets:
            assets.append(r["asset_name"])
    best = max(order, key=lambda q: qs[q]["ebitda"])
    worst = min(order, key=lambda q: qs[q]["ebitda"])
    tot_e = sum(qs[q]["ebitda"] for q in order)
    tot_r = sum(qs[q]["rev"] for q in order)
    return (f"The FY26 quarterly asset-wise P&L covers {len(assets)} producing assets: field revenue of {inr_cr(tot_r)} and EBITDA of "
            f"{inr_cr(tot_e)} for the year, with quarterly EBITDA between {inr_cr(qs[worst]['ebitda'])} ({worst}) and "
            f"{inr_cr(qs[best]['ebitda'])} ({best}). "
            f"{assets[0]} is the largest contributor ({inr_cr(rows[0]['ebitda_fy26_annual_cr'])} EBITDA for the year). "
            "No quarterly P&L exists in the warehouse, so the annual field P&L is phased into quarters using monthly production x "
            "realised prices for revenue and the cost-ledger profile for opex; quarters reconcile exactly to the annual figures.")


def _f10_dd(rows):
    if not rows:
        return "No rows."
    cn, gn = total(rows, "crude_net_cr"), total(rows, "gas_net_cr")
    cl, gl = total(rows, "crude_levies_cr"), total(rows, "gas_levies_cr")
    cg, gg = total(rows, "crude_gross_cr"), total(rows, "gas_gross_cr")
    a = rows[0]["asset_name"]
    ar = [r for r in rows if r["asset_name"] == a]
    gas_led = {}
    for r in rows:
        x = gas_led.setdefault(r["asset_name"], [0.0, 0.0])
        x[0] += r.get("crude_net_cr") or 0
        x[1] += r.get("gas_net_cr") or 0
    gl_assets = [k for k, v in gas_led.items() if v[1] > v[0]]
    return (f"Net of statutory levies, FY26 crude revenue was {inr_cr(cn)} and gas revenue {inr_cr(gn)} across the producing assets; levies "
            f"took {pct(cl * 100 / cg if cg else None)} of crude but only {pct(gl * 100 / gg if gg else None)} of gas because OIDB cess applies to crude only. "
            f"{a} earns the most, {inr_cr(min(r['crude_net_cr'] for r in ar))}-{inr_cr(max(r['crude_net_cr'] for r in ar))} of net crude revenue a quarter. "
            f"{len(gl_assets)} assets are gas-led on a net basis ({names([{'n': k} for k in gl_assets], 'n', 5)}). "
            "Quarterly values are phased from the annual field P&L by monthly volumes and prices.")


def _f10_why(rows):
    if not rows:
        return "No rows."
    t = rows[0]
    hi_opex = max(rows, key=lambda r: r.get("opex_swing_pct_of_avg_quarter") or 0)
    return (f"Quarterly EBITDA swings are driven by revenue, not operating expense: at {t['asset_name']}, the largest swing "
            f"({inr_cr(t['ebitda_swing_cr'], 1)} between {t['best_quarter']} and {t['worst_quarter']}), net revenue moved "
            f"{inr_cr(t['net_revenue_swing_cr'], 1)} while opex moved only {inr_cr(t['opex_swing_cr'], 1)}. "
            f"The largest opex variation is at {hi_opex['asset_name']}, just {pct(hi_opex['opex_swing_pct_of_avg_quarter'], 2)} of an average quarter "
            f"({inr_cr(hi_opex['opex_swing_cr'], 1)}). "
            "Opex is only available annually and is phased by the cost-ledger profile, so genuine intra-year opex events cannot be seen in the data.")


def _f10_cmp(rows):
    if not rows:
        return "No rows."
    dn = [r for r in rows if (r.get("change_vs_fy25_pct") or 0) < 0]
    up = [r for r in rows if (r.get("change_vs_fy25_pct") or 0) > 0]
    t = rows[0]
    best = max(rows, key=lambda r: r.get("change_vs_fy25_pct") or -1e9)
    return (f"No sanctioned operating plan (BE) for asset operating profit exists in the data, so the comparison cannot be made against BE. "
            f"Against the prior year, {len(dn)} of {len(rows)} assets earned less EBITDA in FY26 than FY25 - e.g. {t['asset_name']} "
            f"{inr_cr(t['ebitda_fy26_cr'])} vs {inr_cr(t['ebitda_fy25_cr'])} ({signed_pct(t['change_vs_fy25_pct'])}), quarters "
            f"{inr_cr(t['ebitda_q1_cr'])}-{inr_cr(t['ebitda_q4_cr'])} - while {len(up)} grew, led by {best['asset_name']} "
            f"({signed_pct(best['change_vs_fy25_pct'])}). "
            "An asset-wise operating budget would need to be loaded to answer the BE question directly.")


NARRATIVES = {
    "F1": _f1, "F1__drill_down": _f1_dd, "F1__why": _f1_why, "F1__compare_or_so_what": _f1_cmp,
    "F2": _f2, "F2__drill_down": _f2_dd, "F2__why": _f2_why, "F2__compare_or_so_what": _f2_cmp,
    "F3": _f3, "F3__drill_down": _f3_dd, "F3__why": _f3_why, "F3__compare_or_so_what": _f3_cmp,
    "F4": _f4, "F4__drill_down": _f4_dd, "F4__why": _f4_why, "F4__compare_or_so_what": _f4_cmp,
    "F5": _f5, "F5__drill_down": _f5_dd, "F5__why": _f5_why, "F5__compare_or_so_what": _f5_cmp,
    "F6": _f6, "F6__drill_down": _f6_dd, "F6__why": _f6_why, "F6__compare_or_so_what": _f6_cmp,
    "F7": _f7, "F7__drill_down": _f7_dd, "F7__why": _f7_why, "F7__compare_or_so_what": _f7_cmp,
    "F8": _f8, "F8__drill_down": _f8_dd, "F8__why": _f8_why, "F8__compare_or_so_what": _f8_cmp,
    "F9": _f9, "F9__drill_down": _f9_dd, "F9__why": _f9_why, "F9__compare_or_so_what": _f9_cmp,
    "F10": _f10, "F10__drill_down": _f10_dd, "F10__why": _f10_why, "F10__compare_or_so_what": _f10_cmp,
}
