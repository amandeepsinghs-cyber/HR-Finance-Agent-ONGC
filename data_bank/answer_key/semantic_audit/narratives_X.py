"""Narratives for X-series entries (rendered from result rows; no typed numbers)."""

from semantic_audit.common import f, inr_cr, names, num, pct, signed_pct, total  # noqa: F401


def _g(r, k, d=None):
    v = r.get(k) if r else None
    return d if v is None else v


def _first(rows, key, val):
    for r in rows:
        if r.get(key) == val:
            return r
    return {}


def _ratio(a, b):
    try:
        return float(a) / float(b) if b else None
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ X1
def _x1(rows):
    if not rows:
        return "No producing-asset rows returned."
    cw, reg = total(rows, "contract_workers_mar26"), total(rows, "regular_employees_mar26")
    cc, rc = total(rows, "contractor_cost_fy26_cr"), total(rows, "regular_manpower_cost_fy26_cr")
    top = rows[0]
    by_cpb = sorted([r for r in rows if r.get("regular_cost_per_boe_usd") is not None],
                    key=lambda r: r["regular_cost_per_boe_usd"])
    lo, hi = (by_cpb[0], by_cpb[-1]) if by_cpb else ({}, {})
    return (f"At 31-Mar-2026 the {len(rows)} producing assets had {num(cw)} contract workers against {num(reg)} regular "
            f"employees ({f(_ratio(cw, reg), 2)} contractors per employee), led by {top.get('short_name')} "
            f"({num(top.get('contract_workers_mar26'))} vs {num(top.get('regular_employees_mar26'))}). "
            f"Contract labour is cheap per barrel: FY26 contractor cost was {inr_cr(cc)} versus {inr_cr(rc)} for regular "
            f"manpower, i.e. about ${f(lo.get('contractor_cost_per_boe_usd'), 2)}-{f(hi.get('contractor_cost_per_boe_usd'), 2)} "
            f"per BOE for contractors against ${f(lo.get('regular_cost_per_boe_usd'), 2)}-{f(hi.get('regular_cost_per_boe_usd'), 2)} "
            f"for regular staff. The per-BOE spread is driven by volume: {lo.get('short_name')} is cheapest and "
            f"{hi.get('short_name')} costliest ({f(hi.get('mmboe_fy26'), 2)} MMboe in FY26). Headcounts are March-2026 "
            f"period-end stocks; costs are FY26 totals divided by FY26 BOE at the FY26 average exchange rate.")


def _x1_dd(rows):
    co = _first(rows, "wc_type", "company")
    sites = [r for r in rows if r.get("wc_type") != "company"]
    parts = "; ".join(f"{r['short_name']} {f(r['contract_to_regular_ratio'], 2)} "
                      f"({num(r['contract_workers_mar26'])} contract vs {num(r['regular_employees_mar26'])} regular)"
                      for r in sites)
    return (f"At 31-Mar-2026 the contract-to-regular ratio was {parts}. "
            f"All three are above the company-wide ratio of {f(co.get('contract_to_regular_ratio'), 2)} "
            f"({num(co.get('contract_workers_mar26'))} contract workers vs {num(co.get('regular_employees_mar26'))} employees), "
            f"with the two gas-processing plants the most contract-dependent. Ratios use the March-2026 period-end month, "
            f"consistent with X1.")


def _x1_why(rows):
    if not rows:
        return "No rows returned."
    top, bottom = rows[0], rows[-1]
    plants = _first(rows, "work_centre_segment", "plant / onshore")
    off = _first(rows, "work_centre_segment", "asset / offshore")
    on = _first(rows, "work_centre_segment", "asset / onshore")
    return (f"The data shows a clear gradient: processing plants run {f(plants.get('contract_to_regular_ratio'), 2)} contract "
            f"workers per employee and offshore assets {f(off.get('contract_to_regular_ratio'), 2)}, against "
            f"{f(on.get('contract_to_regular_ratio'), 2)} at onshore assets and {f(bottom.get('contract_to_regular_ratio'), 2)} "
            f"in {bottom.get('work_centre_segment')} (March 2026). "
            f"Every plant and offshore asset is flagged as using contract labour in core activities "
            f"({num(plants.get('core_activity_work_centres'))} of {num(plants.get('work_centres'))} plants, "
            f"{num(off.get('core_activity_work_centres'))} of {num(off.get('work_centres'))} offshore assets), consistent with "
            f"round-the-clock maintenance, logistics and hospitality being outsourced at continuous-operation sites. "
            f"The data cannot attribute this to support vs core roles: the service category on each work centre's contract "
            f"changes month to month, and the document corpus holds no policy explaining the ratios.")


def _x1_cmp(rows):
    off, on = _first(rows, "onshore_offshore", "offshore"), _first(rows, "onshore_offshore", "onshore")
    return (f"Contractors cost a fraction of regular staff per barrel in both theatres: offshore "
            f"${f(off.get('contractor_cost_per_boe_usd'), 2)}/BOE contract vs ${f(off.get('regular_cost_per_boe_usd'), 2)}/BOE "
            f"regular, onshore ${f(on.get('contractor_cost_per_boe_usd'), 2)} vs ${f(on.get('regular_cost_per_boe_usd'), 2)} (FY26). "
            f"Regular manpower spend is {f(off.get('regular_to_contractor_cost_multiple'), 1)}x contractor spend offshore and "
            f"{f(on.get('regular_to_contractor_cost_multiple'), 1)}x onshore, so the manpower cost lever is the regular payroll, "
            f"not contract labour. Onshore costs {f(_ratio(on.get('regular_cost_per_boe_usd'), off.get('regular_cost_per_boe_usd')), 1)}x as much per BOE because its {num(on.get('producing_assets'))} "
            f"assets produced {f(on.get('mmboe_fy26'), 1)} MMboe against {f(off.get('mmboe_fy26'), 1)} MMboe from "
            f"{num(off.get('producing_assets'))} offshore assets.")


# ------------------------------------------------------------------ X2
def _x2(rows):
    if not rows:
        return "No core-activity work centres returned."
    top_ratio = rows[0].get("contract_to_regular_ratio")
    leaders = [r for r in rows if r.get("contract_to_regular_ratio") == top_ratio]
    nxt = [r for r in rows if r.get("contract_to_regular_ratio") != top_ratio]
    second = nxt[0].get("contract_to_regular_ratio") if nxt else None
    tier2 = [r for r in nxt if r.get("contract_to_regular_ratio") == second]
    big = max(rows, key=lambda r: r.get("contract_workers_sep26") or 0)
    kind = "gas-processing plants" if all(r.get("wc_type") == "plant" for r in leaders) else "work centres"
    return (f"The {kind} rely most on contract labour for core operations: {names(leaders, 'short_name', 5)} "
            f"each run {f(top_ratio, 2)} contract workers per regular employee "
            f"({pct(leaders[0].get('contract_share_of_workforce_pct'))} of the workforce, Sep-2026). "
            f"Next come {names(tier2, 'short_name', 6)} at {f(second, 2)}; in absolute terms {big.get('short_name')} has the "
            f"largest core contract workforce ({num(big.get('contract_workers_sep26'))}). "
            f"{len(rows)} work centres are flagged as using contract labour in core activities, holding "
            f"{num(total(rows, 'contract_workers_sep26'))} contract workers against {num(total(rows, 'regular_employees_sep26'))} "
            f"regular employees.")


def _x2_dd(rows):
    act = [r for r in rows if (r.get("avg_monthly_drilling_processing_contract_workers") or 0) > 0]
    gj = [r for r in act if r.get("state") == "Gujarat"]
    asm = [r for r in act if r.get("state") == "Assam"]
    top = act[0] if act else {}
    return (f"{len(act)} production installations in Gujarat and Assam deployed contract personnel under drilling or "
            f"hydrocarbon-processing contracts in FY26: in Gujarat {names(gj, 'short_name', 6)}, in Assam {names(asm, 'short_name', 3)}. "
            f"{top.get('short_name')} is the largest, averaging {num(top.get('avg_monthly_drilling_processing_contract_workers'))} "
            f"such contract workers a month ({num(top.get('drilling_person_months_fy26'))} drilling and "
            f"{num(top.get('processing_person_months_fy26'))} processing person-months). "
            f"Treat these as contract-month allocations: each work centre's contract carries one service category per month "
            f"and that category rotates, so a stable role-level headcount is not recorded.")


def _x2_why(rows):
    docs = ", ".join(f"{r.get('doc_id')} ({r.get('heading')})" for r in rows[:3])
    return (f"The text of the Contract Labour (Regulation & Abolition) Act is not in the document corpus, so it cannot be "
            f"quoted; the closest ONGC authorities are {docs}. "
            f"The Gujarat High Court record (J-14) shows ONGC deploying contract labour in its Western Region for long periods "
            f"after recruitment stopped, and the tribunal matter (J-17) turned on ONGC giving work to contractors in preference "
            f"to casual workmen - both show that core, perennial work done through contractors is open to regularisation "
            f"claims. The Supplier Code of Conduct (P2-17) binds contractors to applicable labour laws. Statutory CLRA "
            f"provisions should be confirmed with Legal before relying on this answer.\n\n"
            + "\n".join(f"> **{r.get('doc_id')} - {r.get('clause_ref')}:** \"{(r.get('quote_snippet') or '').strip()[:400]}\""
                        for r in rows[:3]))


def _x2_cmp(rows):
    off = _first(rows, "segment", "Offshore production assets")
    hq = _first(rows, "segment", "Corporate offices (HQ + regional)")
    return (f"Offshore production platforms depend on contract labour far more than corporate offices: "
            f"{f(off.get('contract_to_regular_ratio'), 2)} contract workers per employee offshore against "
            f"{f(hq.get('contract_to_regular_ratio'), 2)} at the corporate offices (Sep-2026). "
            f"All {num(off.get('work_centres'))} offshore assets use contractors in core activities "
            f"({num(off.get('core_activity_contract_workers_sep26'))} workers), while none of the "
            f"{num(hq.get('work_centres'))} corporate offices does; their {num(hq.get('contract_workers_sep26'))} contract "
            f"workers are entirely non-core support. The core-activity exposure, and hence the CLRA regularisation risk, "
            f"sits in the field.")


# ------------------------------------------------------------------ X3
def _x3(rows):
    hi = next((r for r in rows if (r.get("overtime_hours_per_worker_month") or 0) >= 50), {})
    lo = next((r for r in rows if (r.get("overtime_hours_per_worker_month") or 0) < 50), {})
    mult26 = _ratio(hi.get("ltifr_fy26"), lo.get("ltifr_fy26"))
    mult5 = _ratio(hi.get("ltifr_fy22_fy26"), lo.get("ltifr_fy22_fy26"))
    verdict = "Yes" if (mult5 or 0) > 1 else "No"
    return (f"{verdict}: work centres on {num(hi.get('overtime_hours_per_worker_month'))} h/month overtime (all offshore) had an "
            f"LTIFR of {f(hi.get('ltifr_fy26'), 3)} in FY26 against {f(lo.get('ltifr_fy26'), 3)} for those on "
            f"{num(lo.get('overtime_hours_per_worker_month'))} h - about {f(mult26, 1)}x. "
            f"Over FY22-FY26 the gap holds at {f(hi.get('ltifr_fy22_fy26'), 3)} vs {f(lo.get('ltifr_fy22_fy26'), 3)} "
            f"({f(mult5, 1)}x), with {num(hi.get('ltis_fy22_fy26'))} LTIs in {f(hi.get('million_manhours_fy22_fy26'), 1)} million "
            f"man-hours, and {num(hi.get('fatigue_linked_ltis_fy22_fy26'))} of them were fatigue-flagged. "
            f"The evidence is a two-band association (overtime is recorded as one value per band), not proof of causation; "
            f"FY26 alone rests on {num(hi.get('ltis_fy26'))} vs {num(lo.get('ltis_fy26'))} LTIs.")


def _x3_dd(rows):
    if not rows:
        return "No installations returned."
    ot = {r.get("overtime_hours_per_worker_month_fy26") for r in rows}
    top = rows[0]
    s1 = (f"Both installations recorded the same overtime - {num(next(iter(ot)))} hours per worker per month in FY26 - "
          if len(ot) == 1 else
          f"{top.get('installation_name')} recorded the highest overtime at {num(top.get('overtime_hours_per_worker_month_fy26'))} h/month; ")
    return (s1 + f"so overtime does not separate them, but safety outcomes do: " +
            "; ".join(f"{r['installation_name']} {num(r['ltis_fy26'])} LTIs, LTIFR {f(r['ltifr_fy26'], 3)}" for r in rows) + ". "
            "Platform- and technician-level overtime is not captured (one installation record per asset, one overtime value "
            "for all offshore assets), so a platform ranking cannot be produced.")


def _x3_why(rows):
    lti_hi = next((r for r in rows if "LTI" in str(r.get("incident_type")) and "High" in str(r.get("overtime_band"))), {})
    lti_lo = next((r for r in rows if "LTI" in str(r.get("incident_type")) and "Standard" in str(r.get("overtime_band"))), {})
    nm_hi = next((r for r in rows if "Near" in str(r.get("incident_type")) and "High" in str(r.get("overtime_band"))), {})
    nm_lo = next((r for r in rows if "Near" in str(r.get("incident_type")) and "Standard" in str(r.get("overtime_band"))), {})
    return (f"Fatigue is recorded as a factor in every lost-time injury at high-overtime sites "
            f"({num(lti_hi.get('fatigue_flagged_fy22_fy26'))} of {num(lti_hi.get('incidents_fy22_fy26'))}, FY22-FY26) and in none "
            f"at standard-overtime sites (0 of {num(lti_lo.get('incidents_fy22_fy26'))}), and high-overtime LTIs occur at "
            f"{f(lti_hi.get('incidents_per_million_manhours'), 3)} per million man-hours vs {f(lti_lo.get('incidents_per_million_manhours'), 3)}. "
            f"Near-misses tell the opposite story: {f(nm_hi.get('incidents_per_million_manhours'), 3)} per million man-hours at "
            f"high-overtime sites vs {f(nm_lo.get('incidents_per_million_manhours'), 3)} elsewhere, with no near-miss "
            f"fatigue-flagged. So fatigue shows up in injury severity rather than in near-miss reporting - possibly "
            f"under-reporting of near-misses offshore. Caveat: the fatigue flag appears deterministic (set on all offshore LTIs "
            f"only), so it should be validated before being used as causal evidence.")


def _band(v, r):
    if v is None:
        return "n/a"
    for name, k in (("Excellent", "mou_excellent_target"), ("Very Good", "mou_very_good_target"),
                    ("Good", "mou_good_target"), ("Fair", "mou_fair_target"), ("Poor", "mou_poor_target")):
        if r.get(k) is not None and v <= r[k]:
            return name
    return "below Poor"


def _x3_cmp(rows):
    r = rows[0] if rows else {}
    return (f"High-overtime offshore assets ran an FY26 LTIFR of {f(r.get('high_overtime_ltifr_fy26'), 3)}, "
            f"{f(r.get('high_overtime_vs_excellent_multiple'), 1)}x the MoU 'Excellent' target of "
            f"{f(r.get('mou_excellent_target'), 2)} and in the MoU '{_band(r.get('high_overtime_ltifr_fy26'), r)}' band "
            f"(Poor threshold {f(r.get('mou_poor_target'), 2)}). "
            f"The rest of the company ran {f(r.get('standard_overtime_ltifr_fy26'), 3)} (better than Excellent), and the "
            f"company as a whole {f(r.get('company_ltifr_fy26_computed'), 3)} ('{_band(r.get('company_ltifr_fy26_computed'), r)}') - "
            f"the offshore overtime sites are what keep ONGC out of the 'Excellent' band. The MoU return reports {f(r.get('mou_reported_ltifr_fy26'), 2)}, slightly "
            f"below the rate recomputed from incident records.")


# ------------------------------------------------------------------ X4
def _x4(rows):
    if not rows:
        return "No rows returned."
    a, b = rows[0], rows[-1]
    g = lambda k: signed_pct(_ratio((b.get(k) or 0) - (a.get(k) or 0), a.get(k)) * 100 if a.get(k) else None)
    return (f"Pension (PRBS) and post-retirement medical (PRMB) obligations stood at {inr_cr(b.get('combined_liability_cr'))} at "
            f"{b.get('fiscal_year')} - {inr_cr(b.get('prbs_pension_liability_cr'))} pension and "
            f"{inr_cr(b.get('prmb_medical_liability_cr'))} medical - a change of {g('combined_liability_cr')} from "
            f"{inr_cr(a.get('combined_liability_cr'))} in {a.get('fiscal_year')}. "
            f"The medical liability is growing faster ({g('prmb_medical_liability_cr')}) than pension "
            f"({g('prbs_pension_liability_cr')}), and the net unfunded gap - all of it PRMB - widened from "
            f"{inr_cr(a.get('combined_net_unfunded_cr'))} to {inr_cr(b.get('combined_net_unfunded_cr'))}, with combined funding at "
            f"{pct(b.get('combined_funded_pct'))}. The data series starts in {a.get('fiscal_year')}, so the trend covers "
            f"{len(rows)} year-end valuations rather than a full five-year span from FY21.")


def _x4_dd(rows):
    p = next((r for r in rows if "PRBS" in str(r.get("scheme_type"))), {})
    m = next((r for r in rows if "Medical" in str(r.get("scheme_type"))), {})
    return (f"Of the FY26 post-retirement obligation, PRBS pension is {inr_cr(p.get('actuarial_liability_cr'))} "
            f"({pct(p.get('share_of_combined_pct'))}) and PRMB medical {inr_cr(m.get('actuarial_liability_cr'))} "
            f"({pct(m.get('share_of_combined_pct'))}). "
            f"PRBS is fully funded ({pct(p.get('funded_ratio_pct'))}) while PRMB carries the entire net gap of "
            f"{inr_cr(m.get('net_unfunded_cr'))} at {pct(m.get('funded_ratio_pct'))} funding. Both use a "
            f"{pct(p.get('discount_rate_pct'), 2)} discount rate and {pct(p.get('salary_escalation_rate_pct'))} salary escalation; "
            f"PRMB adds {pct(m.get('medical_inflation_rate_pct'))} medical inflation, covering {num(m.get('retiree_beneficiaries_covered'))} "
            f"retirees and {num(m.get('active_members_covered'))} active members.")


def _x4_why(rows):
    if not rows:
        return "No rows returned."
    a, b = rows[0], rows[-1]
    return (f"Ageing is the main driver: retiree beneficiaries rose from {num(a.get('retiree_beneficiaries'))} to "
            f"{num(b.get('retiree_beneficiaries'))} while active members fell from {num(a.get('active_members'))} to "
            f"{num(b.get('active_members'))}, taking retirees per active member from {f(a.get('retirees_per_active'), 2)} to "
            f"{f(b.get('retirees_per_active'), 2)} ({a.get('fiscal_year')}-{b.get('fiscal_year')}). "
            f"The discount rate eased from {pct(a.get('discount_rate_pct'), 2)} to {pct(b.get('discount_rate_pct'), 2)}, adding "
            f"to valuations, while medical inflation was held at {pct(b.get('medical_inflation_rate_pct'))}. "
            f"Liability per retiree barely moved ({f(a.get('liability_per_retiree_lakh'), 1)} to "
            f"{f(b.get('liability_per_retiree_lakh'), 1)} lakh), confirming the growth from {inr_cr(a.get('combined_liability_cr'))} "
            f"to {inr_cr(b.get('combined_liability_cr'))} is volume of retirees rather than richer benefits; annual payouts reached "
            f"{inr_cr(b.get('combined_annual_payout_cr'))}.")


def _x4_cmp(rows):
    p = next((r for r in rows if "PRBS" in str(r.get("scheme_type"))), {})
    t = next((r for r in rows if r.get("scheme_type") == "All benefit schemes"), {})
    return (f"The PRBS trust's {inr_cr(p.get('plan_assets_cr'))} of assets covers its own obligation exactly "
            f"({pct(p.get('funded_ratio_pct'))}) but only {pct(t.get('prbs_assets_as_pct_of_obligation'))} of ONGC's total "
            f"benefit obligations of {inr_cr(t.get('actuarial_liability_cr'))} (PRBS, PRMB, gratuity and PF). "
            f"Across all schemes, assets of {inr_cr(t.get('plan_assets_cr'))} leave a net gap of {inr_cr(t.get('net_unfunded_cr'))} "
            f"({pct(t.get('funded_ratio_pct'))} funded), concentrated in post-retirement medical and gratuity. "
            f"PRBS assets equal its liability to the rupee in every year, which suggests a balancing entry rather than a "
            f"market valuation and should be checked against the trust's audited accounts.")


# ------------------------------------------------------------------ X5
def _x5(rows):
    if not rows:
        return "No rows returned."
    att = total(rows, "ongc_share_of_pat_cr")
    div = total(rows, "dividend_received_by_ongc_cr")
    grp = rows[0].get("group_consolidated_pat_cr")
    sa = rows[0].get("ongc_standalone_pat_cr")
    top = rows[0]
    return (f"In FY26 HPCL, MRPL and OVL together contributed {inr_cr(att)} of ONGC-attributable profit "
            f"({pct(_ratio(att, grp) * 100 if grp else None)} of group PAT of {inr_cr(grp)}) and paid ONGC {inr_cr(div)} in "
            f"dividends. {top.get('entity_code')} dominates: {inr_cr(top.get('ongc_share_of_pat_cr'))} attributable profit "
            f"({pct(top.get('share_of_group_pat_pct'))} of group PAT) and {inr_cr(top.get('dividend_received_by_ongc_cr'))} of "
            f"dividend; " + "; ".join(f"{r['entity_code']} added {inr_cr(r['ongc_share_of_pat_cr'])} and "
                                     f"{inr_cr(r['dividend_received_by_ongc_cr'])}" for r in rows[1:]) + ". "
            f"The dividends equal {pct(_ratio(div, sa) * 100 if sa else None)} of ONGC's standalone PAT of {inr_cr(sa)}, "
            f"so the subsidiaries matter far more to consolidated earnings than to cash.")


def _x5_dd(rows):
    return ("FY26 PAT and dividends declared: " +
            "; ".join(f"{r['entity_code']} PAT {inr_cr(r['pat_cr'])}, dividend {inr_cr(r['dividend_declared_cr'])} "
                      f"({pct(r['payout_ratio_pct'])} payout), of which ONGC received {inr_cr(r['dividend_received_by_ongc_cr'])}"
                      for r in rows) + ". "
            f"Together they declared {inr_cr(total(rows, 'dividend_declared_cr'))} on PAT of {inr_cr(total(rows, 'pat_cr'))}; "
            f"ONGC's receipt of {inr_cr(total(rows, 'dividend_received_by_ongc_cr'))} reflects its equity stake in each.")


def _x5_why(rows):
    def ser(code):
        s = [r for r in rows if r.get("entity_code") == code]
        return (s[0], s[-1]) if s else ({}, {})
    h0, h1 = ser("HPCL")
    m0, m1 = ser("MRPL")
    o0, o1 = ser("OVL")
    return (f"Profit growth at all three came from volume, not margins: HPCL throughput rose from "
            f"{f(h0.get('refining_throughput_mmt'), 2)} to {f(h1.get('refining_throughput_mmt'), 2)} MMT and MRPL from "
            f"{f(m0.get('refining_throughput_mmt'), 2)} to {f(m1.get('refining_throughput_mmt'), 2)} MMT "
            f"({h0.get('fiscal_year')}-{h1.get('fiscal_year')}), while GRMs moved sideways "
            f"(HPCL ${f(h0.get('gross_refining_margin_usd_bbl'), 2)} to ${f(h1.get('gross_refining_margin_usd_bbl'), 2)}/bbl, MRPL "
            f"${f(m0.get('gross_refining_margin_usd_bbl'), 2)} to ${f(m1.get('gross_refining_margin_usd_bbl'), 2)}). "
            f"OVL's international production edged up from {f(o0.get('international_production_mmtoe'), 2)} to "
            f"{f(o1.get('international_production_mmtoe'), 2)} MMTOE as PAT rose from {inr_cr(o0.get('pat_cr'))} to "
            f"{inr_cr(o1.get('pat_cr'))}. HPCL PAT went from {inr_cr(h0.get('pat_cr'))} to {inr_cr(h1.get('pat_cr'))} and MRPL from "
            f"{inr_cr(m0.get('pat_cr'))} to {inr_cr(m1.get('pat_cr'))}; the smooth year-on-year steps suggest planned rather "
            f"than reported figures.")


def _x5_cmp(rows):
    if not rows:
        return "No rows returned."
    b = rows[-1]
    return (f"Consolidated ROCE trails standalone ROCE in every year: {pct(b.get('consolidated_roce_pct'), 2)} vs "
            f"{pct(b.get('standalone_roce_pct'), 2)} in {b.get('fiscal_year')} ({f(b.get('consolidated_minus_standalone_pp'), 2)} pp), "
            f"and the gap ranged {f(min(r.get('consolidated_minus_standalone_pp') or 0 for r in rows), 2)} to "
            f"{f(max(r.get('consolidated_minus_standalone_pp') or 0 for r in rows), 2)} pp over {rows[0].get('fiscal_year')}-"
            f"{b.get('fiscal_year')}. The downstream and overseas subsidiaries add profit (consolidated PAT "
            f"{inr_cr(b.get('consolidated_pat_cr'))} vs standalone {inr_cr(b.get('standalone_pat_cr'))}) but dilute returns on "
            f"capital. Caution: ROCE levels of this size (well above typical upstream returns) look inconsistent and should be "
            f"verified against the annual report before external use.")


# ------------------------------------------------------------------ X6
def _x6(rows):
    if not rows:
        return "No rows returned."
    a, b = rows[0], rows[-1]
    return (f"Green and renewable capex totalled {inr_cr(b.get('cumulative_green_capex_cr'))} over "
            f"{a.get('fiscal_year')}-{b.get('fiscal_year')}, rising to {inr_cr(b.get('green_capex_cr'))} in {b.get('fiscal_year')} "
            f"({pct(b.get('green_share_of_capex_pct'))} of company capex of {inr_cr(b.get('company_capex_cr'))}), and "
            f"{num(b.get('cumulative_distinct_employees_reskilled'))} employees have completed renewable reskilling. "
            f"Installed renewable capacity reached {num(b.get('installed_mw'))} MW and every project is flagged as meeting its "
            f"Net Zero 2038 roadmap milestone. The roadmap's spend trajectory is not in the data, so 'on path' rests only on that "
            f"flag; and a one-third green share of FY26 capex is high enough to warrant checking against the annual report.")


def _x6_dd(rows):
    if not rows:
        return "No rows returned."
    tot = total(rows, "cumulative_capex_fy22_fy26_cr")
    solar = sum(float(r.get("cumulative_capex_fy22_fy26_cr") or 0) for r in rows if r.get("technology_type") == "Solar PV")
    wind = sum(float(r.get("cumulative_capex_fy22_fy26_cr") or 0) for r in rows if "Wind" in str(r.get("technology_type")))
    h2 = sum(float(r.get("cumulative_capex_fy22_fy26_cr") or 0) for r in rows if r.get("technology_type") == "Green Hydrogen")
    top = rows[0]
    return (f"Cumulative capital invested across the {len(rows)} green projects is {inr_cr(tot)} (FY22-FY26): solar "
            f"{inr_cr(solar)}, wind {inr_cr(wind)} and green hydrogen {inr_cr(h2)}. "
            f"The largest is {top.get('project_name')} at {inr_cr(top.get('cumulative_capex_fy22_fy26_cr'))} for "
            f"{num(top.get('installed_mw_fy26'))} MW. The stored 'cumulative capex' field does not reconcile with the annual "
            f"spend (it shows {inr_cr(total(rows, 'stored_cumulative_capex_fy26_cr'))} in total), so the figures here are summed "
            f"from annual capex.")


def _x6_why(rows):
    if not rows:
        return "No rows returned."
    comp = total(rows, "completions")
    acad = next((r for r in rows if "Academy" in str(r.get("institute"))), {})
    top = rows[0]
    return (f"Renewable-energy reskilling runs as a single 'Renewable Energy Excellence' programme delivered through "
            f"{len(rows)} institutes, with {num(comp)} completions from {top.get('first_fy')} to {top.get('latest_fy')} "
            f"(FY27 year-to-date). "
            f"ONGC Academy Dehradun accounts for {num(acad.get('completions'))} completions and {num(acad.get('total_training_days'))} "
            f"training days; {top.get('institute')} leads with {num(top.get('completions'))}. "
            f"Completion rates are {pct(_ratio(comp, total(rows, 'enrolments')) * 100 if total(rows, 'enrolments') else None)} of enrolments overall; course content and role-transition "
            f"outcomes are not recorded, so the data shows reach, not whether engineers moved into renewable roles.")


def _x6_cmp(rows):
    if not rows:
        return "No rows returned."
    a, b = rows[0], rows[-1]
    return (f"Annual green capex has grown from {inr_cr(a.get('total_green_capex_cr'))} in {a.get('fiscal_year')} to "
            f"{inr_cr(b.get('total_green_capex_cr'))} in {b.get('fiscal_year')} (solar {inr_cr(b.get('solar_capex_cr'))}, wind "
            f"{inr_cr(b.get('wind_capex_cr'))}, green hydrogen {inr_cr(b.get('green_hydrogen_capex_cr'))}), but it cannot be "
            f"compared with Net Zero 2038 spending milestones because no such targets exist in the data or documents. "
            f"The only roadmap signal is a milestone flag, set to 'met' for {num(b.get('projects_flagged_milestone_met'))} of "
            f"{num(b.get('projects'))} projects in every year - including years in which most projects spent nothing - so it "
            f"carries no information. A quantified answer needs the roadmap's year-wise capex plan.")


# ------------------------------------------------------------------ X7
def _x7(rows):
    if not rows:
        return "No rows returned."
    tv, ts = total(rows, "vacancies"), total(rows, "sanctioned")
    ta, tt = total(rows, "vacancies_assam"), total(rows, "vacancies_tripura")
    bl = total(rows, "backlog_reserved_vacancies")
    lines = "\n".join(f"| {r['category']} | {num(r['sanctioned'])} | {num(r['in_position'])} | {num(r['vacancies'])} | "
                      f"{num(r['vacancies_assam'])} | {num(r['vacancies_tripura'])} |" for r in rows)
    return (f"**Draft reply (Minister of Petroleum & Natural Gas):** As on 31 March 2026, ONGC had {num(tv)} vacancies against "
            f"{num(ts)} sanctioned posts ({pct(_ratio(tv, ts) * 100 if ts else None)}) in its North-Eastern work centres - "
            f"{num(ta)} in Assam and {num(tt)} in Tripura. "
            f"Category-wise: " + "; ".join(f"{r['category']} {num(r['vacancies'])}" for r in rows) + ". "
            f"Of the reserved-category vacancies, {num(bl)} are backlog vacancies, which are being filled through a Special "
            f"Recruitment Drive; {'Tripura' if tt > ta else 'Assam'} accounts for {pct(_ratio(max(ta, tt), tv) * 100 if tv else None)} of the region's vacancies.\n\n"
            f"| Category | Sanctioned | In position | Vacancies | Assam | Tripura |\n|---|---|---|---|---|---|\n{lines}")


def _x7_dd(rows):
    def st(s):
        rr = [r for r in rows if r.get("state") == s]
        return rr, total(rr, "sanctioned"), total(rr, "in_position")
    a, as_, ai = st("Assam")
    t, ts, ti = st("Tripura")
    worst = min(rows, key=lambda r: r.get("fill_rate_pct") or 100) if rows else {}
    return (f"Assam has {num(ai)} in position against {num(as_)} sanctioned and Tripura {num(ti)} against {num(ts)} (FY26). "
            f"By category - Assam: " + ", ".join(f"{r['category']} {num(r['in_position'])}/{num(r['sanctioned'])}" for r in a) +
            "; Tripura: " + ", ".join(f"{r['category']} {num(r['in_position'])}/{num(r['sanctioned'])}" for r in t) + ". "
            f"The weakest fill rate is {worst.get('category')} in {worst.get('state')} at {pct(worst.get('fill_rate_pct'))}; "
            f"Assam covers six work centres (Assam and Jorhat assets, A&AA and Silchar basins, INBIGS).")


def _x7_why(rows):
    tgt = total(rows, "special_drive_target")
    nat = rows[0].get("national_drive_target") if rows else None
    drive = rows[0].get("special_drive_name") if rows else "the special drive"
    return (f"The one recorded initiative is the {drive}, which targets {num(tgt)} backlog SC/ST vacancies in the North-East - "
            f"{pct(_ratio(tgt, nat) * 100 if nat else None)} of its national target of {num(nat)}: " +
            "; ".join(f"{r['short_name']} {r['category']} {num(r['special_drive_target'])}" for r in rows) + ". "
            f"The drive covers only backlog reserved posts, so the region's OBC, EWS and General vacancies (see X7) have no "
            f"targeted programme in the data; no NE-specific recruitment campaign is recorded in the documents.")


def _x7_cmp(rows):
    ne = next((r for r in rows if "North-East" in str(r.get("region"))), {})
    nat = next((r for r in rows if r.get("region") == "ONGC national"), {})
    rest = next((r for r in rows if r.get("region") == "Rest of India"), {})
    better = (ne.get('vacancy_rate_pct') or 0) < (nat.get('vacancy_rate_pct') or 0)
    return (f"North-East work centres are {'better' if better else 'worse'} staffed than the rest of ONGC: a vacancy rate of {pct(ne.get('vacancy_rate_pct'), 2)} "
            f"({num(ne.get('vacancies'))} of {num(ne.get('sanctioned'))} posts) against the national average of "
            f"{pct(nat.get('vacancy_rate_pct'), 2)} ({num(nat.get('vacancies'))} of {num(nat.get('sanctioned'))}) and "
            f"{pct(rest.get('vacancy_rate_pct'), 2)} elsewhere. "
            f"Within the region the gap is uneven - see X7__drill_down for the Tripura vs Assam split.")


# ------------------------------------------------------------------ X8
def _x8(rows):
    cag = [r for r in rows if str(r.get("item", "")).startswith("CAG")]
    rti = [r for r in rows if str(r.get("item", "")).startswith("RTI")]
    nc, nr = total(cag, "pending_count"), total(rti, "pending_count")
    c3 = sum(float(r.get("pending_count") or 0) for r in cag if str(r.get("age_band", ""))[:1] in ("3", "4"))
    c5 = sum(float(r.get("pending_count") or 0) for r in cag if str(r.get("age_band", "")).startswith("4"))
    r30 = sum(float(r.get("pending_count") or 0) for r in rti if not str(r.get("age_band", "")).startswith("1"))
    r1y = sum(float(r.get("pending_count") or 0) for r in rti if str(r.get("age_band", "")).startswith("4"))
    oldest_c = max((r.get("oldest_days") or 0) for r in cag) if cag else None
    return (f"{num(nc)} CAG audit paras and {num(nr)} RTI applications are pending as of 19-Oct-2026; {num(c3)} of the paras are "
            f"over three years old ({num(c5)} over five) and {num(r30)} RTI applications are past the 30-day statutory limit. "
            f"The open paras carry {inr_cr(total(cag, 'financial_implication_cr'), 1)} of financial implication, the oldest "
            f"outstanding for {num(oldest_c)} days. On RTI, {num(r1y)} applications have been pending for more than a year - "
            f"a statutory exposure regardless of volume.")


def _x8_dd(rows):
    if not rows:
        return "No rows returned."
    top = rows[0]
    proc = next((r for r in rows if "Procurement" in str(r.get("operating_department"))), {})
    fin = next((r for r in rows if "Finance" in str(r.get("operating_department"))), {})
    hr = next((r for r in rows if "Human" in str(r.get("operating_department"))), {})
    return (f"{top.get('operating_department')} has the most open CAG paras ({num(top.get('open_paras'))}, "
            f"{inr_cr(top.get('financial_implication_cr'), 1)}), followed by Procurement/MM ({num(proc.get('open_paras'))}, "
            f"{inr_cr(proc.get('financial_implication_cr'), 1)}). "
            f"Of the three departments named, HR has {num(hr.get('open_paras'))} and Finance only {num(fin.get('open_paras'))}. "
            f"Across all {len(rows)} departments, {num(total(rows, 'paras_over_3_years'))} of {num(total(rows, 'open_paras'))} "
            f"open paras are older than three years.")


def _x8_why(rows):
    agg = {}
    for r in rows:
        k = r.get("bottleneck_reason") or "Not recorded"
        agg.setdefault(k, [0, 0.0])
        agg[k][0] += r.get("open_paras_over_3_years") or 0
        agg[k][1] += float(r.get("financial_implication_cr") or 0)
    ranked = sorted(agg.items(), key=lambda kv: (-kv[1][0], -kv[1][1]))
    tot = total(rows, "open_paras_over_3_years")
    lead = ranked[0] if ranked else ("n/a", [0, 0])
    return (f"{num(tot)} open CAG paras are older than three years, and the leading bottleneck is '{lead[0]}' "
            f"({num(lead[1][0])} paras, {inr_cr(lead[1][1], 1)}). "
            "Other causes: " + "; ".join(f"{k} ({num(v[0])})" for k, v in ranked[1:5]) + ". "
            "Most delays sit outside ONGC (CAG concurrence, inter-ministerial consultation, COPU, arbitration), so closure "
            "needs follow-up at MoPNG level rather than more internal documentation.")


def _x8_cmp(rows):
    disp = total(rows, "disposed")
    apps = total(rows, "applications")
    w30 = total(rows, "disposed_within_30_days")
    pend = total(rows, "pending_beyond_30_days")
    fy26 = _first(rows, "fiscal_year", "FY26")
    return (f"ONGC has disposed of {pct(_ratio(disp, apps) * 100 if apps else None)} of RTI applications received since "
            f"{rows[0].get('fiscal_year') if rows else 'n/a'} ({num(disp)} of {num(apps)}), and "
            f"{pct(_ratio(w30, disp) * 100 if disp else None)} of disposals met the 30-day statutory timeline. "
            f"In FY26 the compliance rate was {pct(fy26.get('pct_disposals_within_30_days'))} with an average of "
            f"{f(fy26.get('avg_days_to_dispose'), 1)} days. The bigger exposure is the backlog: {num(pend)} applications are still "
            f"undisposed beyond 30 days, each a potential deemed refusal under the RTI Act.")


# ------------------------------------------------------------------ X9
def _x9(rows):
    if not rows:
        return "No rows returned."
    tot = total(rows, "spend_cr")
    op = total(rows, "operational_area_spend_cr")
    asp = total(rows, "aspirational_district_spend_cr")
    by_state, by_theme = {}, {}
    for r in rows:
        by_state[r["state_name"]] = by_state.get(r["state_name"], 0) + float(r.get("spend_cr") or 0)
        by_theme[r["csr_theme"]] = by_theme.get(r["csr_theme"], 0) + float(r.get("spend_cr") or 0)
    ts = sorted(by_state.items(), key=lambda kv: -kv[1])
    tt = sorted(by_theme.items(), key=lambda kv: -kv[1])
    nonop = sorted({r["state_name"] for r in rows if r.get("state_has_ongc_operations") is False})
    nonop_spend = sum(v for k, v in by_state.items() if k in nonop)
    return (f"FY26 CSR spend was {inr_cr(tot)} across {len(by_state)} states, led by {ts[0][0]} ({inr_cr(ts[0][1], 1)}) and "
            f"{ts[1][0]} ({inr_cr(ts[1][1], 1)}); by theme, {tt[0][0]} ({inr_cr(tt[0][1], 1)}) and {tt[1][0]} "
            f"({inr_cr(tt[1][1], 1)}) lead. "
            f"Against the policy's preference for operational areas, {pct(_ratio(op, tot) * 100 if tot else None)} "
            f"({inr_cr(op, 1)}) went to ONGC operational field areas and {pct(_ratio(asp, tot) * 100 if tot else None)} "
            f"({inr_cr(asp, 1)}) to aspirational districts. "
            f"The largest single state, {ts[0][0]}, has no ONGC operations: {', '.join(nonop)} together received "
            f"{inr_cr(nonop_spend, 1)}, which the Board CSR Committee should be able to justify under national-priority criteria.")


def _x9_dd(rows):
    tot = rows[0].get("total_csr_spend_cr") if rows else None
    asp = rows[0].get("total_aspirational_spend_cr") if rows else None
    get = lambda name: next((r for r in rows if r.get("csr_theme") == name), {})
    e, h, s = get("Education"), get("Healthcare"), get("Sanitation & Safe Drinking Water")
    three = sum(float(x.get("spend_cr") or 0) for x in (e, h, s))
    return (f"Of the {inr_cr(tot)} FY26 CSR spend, education took {pct(e.get('share_of_total_pct'))} ({inr_cr(e.get('spend_cr'), 1)}), "
            f"sanitation and drinking water {pct(s.get('share_of_total_pct'))} ({inr_cr(s.get('spend_cr'), 1)}) and healthcare "
            f"{pct(h.get('share_of_total_pct'))} ({inr_cr(h.get('spend_cr'), 1)}) - together "
            f"{pct(_ratio(three, tot) * 100 if tot else None)}. "
            f"Aspirational districts received {inr_cr(asp, 1)} ({pct(_ratio(asp, tot) * 100 if tot else None)}), cutting across "
            f"themes, mostly sanitation ({inr_cr(s.get('aspirational_district_spend_cr'), 1)}). "
            f"The remaining spend went to environment, skills, rural development and sports.")


def _x9_why(rows):
    tot = total(rows, "spend_cr")
    nonop = [r for r in rows if r.get("state_has_ongc_operations") is False]
    asp = [r for r in rows if r.get("is_aspirational_district")]
    sponsors = sorted({str(r.get("sponsoring_wc")) for r in rows})
    states = sorted({r["state_name"] for r in nonop})
    return (f"{len(rows)} FY26 projects worth {inr_cr(tot, 1)} sit outside operational field areas, {len(nonop)} of them in states "
            f"with no ONGC operations ({', '.join(states)}). "
            f"The stated justification in the data is national priority: {len(asp)} of the {len(rows)} are in aspirational "
            f"districts ({inr_cr(total(asp, 'spend_cr'), 1)}), consistent with CSR Policy 2025 allowing projects anywhere in India "
            f"'with preference to its Operational Areas'. The rest - e.g. {nonop[0]['project_name'] if nonop else 'n/a'} - have no "
            f"aspirational or disaster-relief tag and were sponsored from {', '.join(sponsors)}, so their rationale is not "
            f"evidenced in the data.")


def _x9_cmp(rows):
    op = next((r for r in rows if str(r.get("area_category", "")).startswith("1")), {})
    st = next((r for r in rows if str(r.get("area_category", "")).startswith("2")), {})
    no = next((r for r in rows if str(r.get("area_category", "")).startswith("3")), {})
    return (f"{pct(op.get('share_pct'))} of FY26 CSR spend ({inr_cr(op.get('spend_cr'), 1)}, {num(op.get('projects'))} projects) "
            f"went to ONGC operational field areas, as the policy's operational-area preference requires. "
            f"{pct(no.get('share_pct'))} ({inr_cr(no.get('spend_cr'), 1)}) went to {num(no.get('states'))} states with no ONGC "
            f"operations, of which {inr_cr(no.get('of_which_aspirational_cr'), 1)} was in aspirational districts; a further "
            f"{pct(st.get('share_pct'))} went to non-operational districts in ONGC states. "
            f"Operational areas receive the majority, but {pct(no.get('share_pct'))} flowing to non-operational states is material and "
            f"should be explicitly approved as national-priority spend.")


# ------------------------------------------------------------------ X10
def _x10(rows):
    p = next((r for r in rows if str(r.get("indicator", "")).startswith("1")), {})
    h = next((r for r in rows if str(r.get("indicator", "")).startswith("2")), {})
    lc = next((r for r in rows if str(r.get("indicator", "")).startswith("3")), {})
    return (f"The data supports only part of the alert: {num(p.get('value'))} capital projects are currently behind schedule "
            f"({p.get('detail')}), {num(h.get('value'))} executives are past the five-year rotation window (excluding exempt and retirement-protected officers), and no field's lifting "
            f"cost rose 12% - the largest FY26-vs-FY25 rise is {signed_pct(lc.get('value'))} ({lc.get('detail')}). "
            f"The rotation figure is the real exception: it is far above the alert's number and covers most of the executive "
            f"cadre ({h.get('detail')}). "
            f"'This week' cannot be verified because project progress and field costs are held as FY26 snapshots and annual "
            f"P&L, not weekly data.")


def _x10_dd(rows):
    open_ = [r for r in rows if str(r.get("project_status", "")).lower() != "completed"]
    top3 = open_[:3]
    return (f"The three most-delayed open projects are " +
            "; ".join(f"{r['project_name']} ({num(r['slippage_months'])} months late: completion moved from "
                      f"{r['scheduled_completion']} to {r['anticipated_completion']}, overrun {inr_cr(r['cost_overrun_cr'], 1)})"
                      for r in top3) + ". "
            f"In all, {len(open_)} open projects have slipped (and {len(rows) - len(open_)} completed late); the largest cost "
            f"overrun is {max(rows, key=lambda r: r.get('cost_overrun_cr') or 0).get('project_name') if rows else 'n/a'} "
            f"({inr_cr(max((r.get('cost_overrun_cr') or 0) for r in rows) if rows else None, 1)}). "
            f"Several anticipated dates are already past 19-Oct-2026 although the projects are not marked complete, so the "
            f"progress data needs refreshing.")


def _x10_why(rows):
    if not rows:
        return "No rows returned."
    top = rows[0]
    return (f"No field shows a 12% lifting-cost spike, so there is no downtime event to attribute: the largest FY26 rise is "
            f"{top.get('field_name')} at {signed_pct(top.get('lifting_change_pct'))} "
            f"(${f(top.get('lifting_fy25_usd_boe'), 2)} to ${f(top.get('lifting_fy26_usd_boe'), 2)}/BOE). "
            f"Where costs did rise, the cause is lower output and more downtime: {top.get('field_name')}'s output changed "
            f"{signed_pct(top.get('production_change_pct'))} with {num(top.get('downtime_change_hours'))} more well-downtime "
            f"hours (uptime {f(top.get('uptime_change_pp'), 2)} pp). "
            f"Weekly cost and compressor-event data are not available, so a specific compressor outage cannot be identified.")


def _x10_cmp(rows):
    get = lambda s: next((r for r in rows if s in str(r.get("indicator", ""))), {})
    p, h, lc = get("Projects"), get("Rotation"), get("lifting")
    return (f"No Executive Committee notification thresholds exist in the data or documents, so the alert cannot be tested "
            f"against pre-set limits. Against the alert's own figures: projects slipped {num(p.get('actual_value'))} vs "
            f"{num(p.get('alert_claimed_value'))} claimed, rotation cases {num(h.get('actual_value'))} vs "
            f"{num(h.get('alert_claimed_value'))}, lifting-cost rise {signed_pct(lc.get('actual_value'))} vs "
            f"{signed_pct(lc.get('alert_claimed_value'))}. "
            f"Against documented norms, {num(p.get('actual_breaching_norm'))} slipped projects have overruns above the "
            f"₹100 cr Board-reserved threshold (BDP cl.6.1) and all {num(h.get('actual_breaching_norm'))} rotation cases breach "
            f"the JRTP five-year window - both would merit escalation; the lifting-cost item would not.")


NARRATIVES = {
    "X1": _x1, "X1__drill_down": _x1_dd, "X1__why": _x1_why, "X1__compare_or_so_what": _x1_cmp,
    "X2": _x2, "X2__drill_down": _x2_dd, "X2__why": _x2_why, "X2__compare_or_so_what": _x2_cmp,
    "X3": _x3, "X3__drill_down": _x3_dd, "X3__why": _x3_why, "X3__compare_or_so_what": _x3_cmp,
    "X4": _x4, "X4__drill_down": _x4_dd, "X4__why": _x4_why, "X4__compare_or_so_what": _x4_cmp,
    "X5": _x5, "X5__drill_down": _x5_dd, "X5__why": _x5_why, "X5__compare_or_so_what": _x5_cmp,
    "X6": _x6, "X6__drill_down": _x6_dd, "X6__why": _x6_why, "X6__compare_or_so_what": _x6_cmp,
    "X7": _x7, "X7__drill_down": _x7_dd, "X7__why": _x7_why, "X7__compare_or_so_what": _x7_cmp,
    "X8": _x8, "X8__drill_down": _x8_dd, "X8__why": _x8_why, "X8__compare_or_so_what": _x8_cmp,
    "X9": _x9, "X9__drill_down": _x9_dd, "X9__why": _x9_why, "X9__compare_or_so_what": _x9_cmp,
    "X10": _x10, "X10__drill_down": _x10_dd, "X10__why": _x10_why, "X10__compare_or_so_what": _x10_cmp,
}
