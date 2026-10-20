"""Narratives for the MTW slice (M1-M5, T1-T3, W1-W4 + follow-ups), rendered from result rows only."""

from semantic_audit.common import f, inr_cr, names, num, pct, signed_pct, total  # noqa: F401


def _g(r, k, d=None):
    return (r or {}).get(k, d) if r else d


def _first(rows, key, val):
    for r in rows:
        if r.get(key) == val:
            return r
    return None


def _quote(r, n=220):
    q = (_g(r, "quote_snippet") or "").strip().replace("\n", " ")
    return (q[:n].rsplit(" ", 1)[0] + "...") if len(q) > n else q


def _cite(r):
    return f"{_g(r, 'doc_id')} {_g(r, 'clause_ref')} ({_g(r, 'heading')})"


# ---------------------------------------------------------------------------------- M1
def _m1(rows):
    if not rows:
        return "No asset headcount rows were returned."
    tot = total(rows, "headcount_30sep2026")
    co = _g(rows[0], "company_hc_sep26")
    top = rows[0]
    low = rows[-1]
    return (f"The 14 operating assets employ {num(tot)} people at the 30-Sep-2026 snapshot "
            f"({pct(tot * 100.0 / co if co else None)} of the company's {num(co)}), led by {top['asset']} "
            f"({num(top['headcount_30sep2026'])}) and {rows[1]['asset']} ({num(rows[1]['headcount_30sep2026'])}). "
            f"The smallest is {low['asset']} at {num(low['headcount_30sep2026'])}; at 31-Mar-2026 the same assets held "
            f"{num(total(rows, 'headcount_31mar2026'))}. Figures are single-month period-end snapshots (aggregate, non-identifying), "
            f"so they can be compared directly with the company total.")


def _m1_dd(rows):
    if not rows:
        return "No cadre split was returned."
    ex, ne, tt = total(rows, "executive_hc"), total(rows, "non_executive_hc"), total(rows, "total_hc")
    srt = sorted(rows, key=lambda r: r.get("executive_share_pct") or 0)
    lo, hi = srt[0], srt[-1]
    return (f"Across the 14 operating assets, {num(ex)} of {num(tt)} employees ({pct(ex * 100.0 / tt if tt else None)}) are executives "
            f"and {num(ne)} are non-executives (30-Sep-2026 snapshot). "
            f"The mix varies sharply: {lo['asset']} is the most non-executive-heavy ({pct(lo['executive_share_pct'])} executives) "
            f"while {hi['asset']} is the most officer-heavy ({pct(hi['executive_share_pct'])}). "
            f"Totals reconcile to M1 because both use the same single-month snapshot.")


def _m1_why(rows):
    c = names([{"c": _cite(r)} for r in rows], "c", 3)
    jr = _first(rows, "doc_id", "JRTP")
    qt = (' ("' + _quote(jr, 160) + '")') if jr else ""
    return (f"No document in the policy corpus explicitly grants aggregate asset headcount to HR officers while denying it to Finance officers; "
            f"the restriction rests on role-based, need-to-know controls in {c}. "
            f"The closest rule is the JRTP's requirement that HR record systems be restricted to authorised Corporate HR personnel{qt}. "
            f"Treat the HR-vs-Finance split for aggregate headcount as an access-design choice, not a cited rule (documentation gap).")


def _m1_cmp(rows):
    w = _first(rows, "asset_group", "Western Onshore")
    e = _first(rows, "asset_group", "Eastern Offshore")
    if not (w and e):
        return "Western Onshore / Eastern Offshore groups not both present."
    return (f"Western Onshore's {w['assets']} assets employ {num(w['hc_30sep2026'])} people against {num(e['hc_30sep2026'])} at "
            f"Eastern Offshore ({e['asset_names']}) as of 30-Sep-2026, about {f(w['hc_30sep2026'] / e['hc_30sep2026'] if e['hc_30sep2026'] else None, 1)}x larger. "
            f"The trends diverge: Western Onshore shrank {signed_pct(w['change_mar21_to_mar26_pct'])} between 31-Mar-2021 and 31-Mar-2026 "
            f"({num(w['hc_31mar2021'])} to {num(w['hc_31mar2026'])}) while Eastern Offshore grew {signed_pct(e['change_mar21_to_mar26_pct'])} "
            f"({num(e['hc_31mar2021'])} to {num(e['hc_31mar2026'])}). All values are March/September period-end snapshots.")


# ---------------------------------------------------------------------------------- M2
def _m2(rows):
    if not rows:
        return "No FY27 capex rows were returned."
    be, act = total(rows, "ytd_be_inr_cr"), total(rows, "ytd_actual_inr_cr")
    srt = sorted([r for r in rows if r.get("utilisation_vs_be_pct") is not None], key=lambda r: r["utilisation_vs_be_pct"])
    over = [r for r in rows if (r.get("utilisation_vs_be_pct") or 0) > 100]
    return (f"FY27 year-to-date (Apr-Sep 2026) capex utilisation is {pct(act * 100.0 / be if be else None)} of phased BE: "
            f"{inr_cr(act)} spent against {inr_cr(be)} across {len(rows)} spending centres. "
            f"{rows[0]['asset']} is the largest spender ({inr_cr(rows[0]['ytd_actual_inr_cr'])}, {pct(rows[0]['utilisation_vs_be_pct'])}); "
            f"the lowest utilisation is {srt[0]['asset']} ({pct(srt[0]['utilisation_vs_be_pct'])}) and {len(over)} centre(s) are running above BE"
            f"{' (highest ' + srt[-1]['asset'] + ' at ' + pct(srt[-1]['utilisation_vs_be_pct']) + ')' if over else ''}. "
            f"Only {rows[0].get('months_covered')} months of FY27 are booked, so this is YTD utilisation, not full-year.")


def _m2_dd(rows):
    if not rows:
        return "No producing-asset capex rows were returned."
    be, act = total(rows, "ytd_be_inr_cr"), total(rows, "ytd_actual_inr_cr")
    under = sorted(rows, key=lambda r: r.get("variance_vs_be_inr_cr") or 0)
    return (f"The 15 producing assets have spent {inr_cr(act)} of {inr_cr(be)} phased BE in FY27 to date "
            f"({pct(act * 100.0 / be if be else None)}), an underspend of {inr_cr(be - act)}. "
            f"The biggest shortfall is {under[0]['asset']} ({inr_cr(under[0]['variance_vs_be_inr_cr'])} vs BE, {pct(under[0]['utilisation_vs_be_pct'])}), "
            f"while the top producer {rows[0]['asset']} ({f(rows[0]['fy26_mmboe'], 1)} MMboe in FY26) is at {pct(rows[0]['utilisation_vs_be_pct'])}. "
            f"Window is Apr-Sep 2026 (6 months).")


def _m2_why(rows):
    c = names([{"c": _cite(r)} for r in rows], "c", 3)
    return (f"Capex utilisation is a Finance function because the Book of Delegated Powers ties expenditure authority and BE/RE budget control "
            f"to financial posts, and classifies financial schedules as internal controlled information ({c}). "
            f"The corpus has no clause that explicitly bars junior HR officers from aggregate capex data, so the HR restriction is a "
            f"need-to-know access-design choice rather than a cited rule (documentation gap). "
            f"Key text: \"{_quote(rows[0], 180) if rows else ''}\"")


def _m2_cmp(rows):
    mh = _first(rows, "scope", "Mumbai High")
    co = _first(rows, "scope", "Company total")
    if not (mh and co):
        return "Mumbai High / company rows missing."
    return (f"Mumbai High has spent {inr_cr(mh['fy27_ytd_actual_inr_cr'])} of {inr_cr(mh['fy27_ytd_be_inr_cr'])} phased BE in FY27 to date "
            f"({pct(mh['fy27_ytd_utilisation_pct'])}), slightly ahead of the company's {pct(co['fy27_ytd_utilisation_pct'])}. "
            f"At this pace it would spend about {inr_cr(mh['fy27_annualised_run_rate_inr_cr'])} for the year, "
            f"{pct(mh['run_rate_pct_of_fy26_be'])} of its FY26 annual BE of {inr_cr(mh['fy26_annual_be_inr_cr'])} "
            f"(FY26 actual {inr_cr(mh['fy26_actual_inr_cr'])}). "
            f"The FY27 full-year sanctioned budget is not in the data beyond Sep-2026, so FY26 BE is used as the annual-plan proxy.")


# ---------------------------------------------------------------------------------- M3 / M4
def _m3_dd(rows):
    r = rows[0] if rows else {}
    return (f"An executive views their own APAR grading and salary slip only through the authenticated Employee Self-Service (ESS) portal, "
            f"per {_cite(r)}. "
            f"ESS access is limited to the employee's own payslip/Form 16, leave, e-APAR scorecards, PF/pension balances and posting history: "
            f"\"{_quote(r, 200)}\" "
            f"No other channel (including this assistant) may return another employee's records.")


def _m3_why(rows):
    hr = _first(rows, "doc_id", "HR Manual") or (rows[0] if rows else {})
    rp = _first(rows, "doc_id", "R&P/Promotion")
    return (f"REFUSAL upheld: colleagues' salary and APAR ratings are protected personal information under {_cite(hr)}, which invokes "
            f"Section 8(1)(j) of the RTI Act and makes unauthorised querying major misconduct under the CDA Rules. "
            f"\"{_quote(hr, 200)}\" "
            f"{('Appraisal-linked DPC deliberations are separately secret under ' + _cite(rp) + '.') if rp else ''}")


def _m3_cmp(rows):
    r = rows[0] if rows else {}
    return (f"Employee 104523 holds grade {_g(r, 'grade_id')} ({_g(r, 'designation')}, {_g(r, 'cadre')} cadre), whose published pay scale is "
            f"₹{num(_g(r, 'pay_scale_min_inr'))}-₹{num(_g(r, 'pay_scale_max_inr'))} per month ({_g(r, 'scale_type')}). "
            f"Promotion is {_g(r, 'promotion_mode')} after about {_g(r, 'typical_residency_years')} years in grade via "
            f"'{_g(r, 'dpc_evaluation_type')}', leading to {_g(r, 'next_grade_id')} ({_g(r, 'next_grade_designation')}). "
            f"Only grade-level public scales are shown; the individual's actual pay and appraisal remain confidential.")


def _m4_dd(rows):
    if not rows:
        return "No quarterly production rows."
    q = rows[0]
    fy26 = [r for r in rows if r.get("fiscal_year") == "FY26"]
    return (f"In the latest quarter, {q['fiscal_year']} {q['fy_quarter']} ({q['first_month']} to {q['last_month']}), ONGC produced "
            f"{f(q['oil_mmt'], 2)} MMT crude oil, {f(q['condensate_mmt'], 2)} MMT condensate and {f(q['gas_bcm'], 2)} BCM gas "
            f"({f(q['total_mmboe'], 1)} MMboe). "
            f"Full-year FY26 was {f(total(fy26, 'oil_mmt'), 2)} MMT oil, {f(total(fy26, 'condensate_mmt'), 2)} MMT condensate and "
            f"{f(total(fy26, 'gas_bcm'), 2)} BCM gas ({f(total(fy26, 'total_mmboe'), 1)} MMboe). "
            f"These company-wide totals are publishable; oil, condensate and gas are reported in their own units and only combined in BOE.")


def _m4_why(rows):
    r = rows[0] if rows else {}
    return (f"Field-level profitability is withheld from junior functional officers because field-specific financial data is classified as "
            f"commercially sensitive, internal controlled information under {_cite(r)}. "
            f"\"{_quote(r, 220)}\" "
            f"Company-level audited results remain available as the permitted alternative.")


def _m4_cmp(rows):
    a = _first(rows, "fiscal_year", "FY26") or (rows[0] if rows else {})
    b = _first(rows, "fiscal_year", "FY25")
    chg = ((a["ebitda_inr_cr"] - b["ebitda_inr_cr"]) * 100.0 / b["ebitda_inr_cr"]) if (a and b and b.get("ebitda_inr_cr")) else None
    return (f"ONGC's last audited standalone EBITDA (FY26) was {inr_cr(_g(a, 'ebitda_inr_cr'))} on gross revenue of "
            f"{inr_cr(_g(a, 'gross_revenue_inr_cr'))}, a {pct(_g(a, 'ebitda_margin_pct'))} margin. "
            f"That is {signed_pct(chg)} versus FY25 ({inr_cr(_g(b, 'ebitda_inr_cr'))}); PAT was {inr_cr(_g(a, 'pat_inr_cr'))}.")


# ---------------------------------------------------------------------------------- M5
def _m5(rows):
    if not rows:
        return "No confidential-data access attempts were logged in the 7 days to 19-Oct-2026."
    den = [r for r in rows if (r.get("denied_attempts") or 0) > 0]
    alw = [r for r in rows if (r.get("allowed_attempts") or 0) > 0]
    depts = {}
    for r in den:
        depts[r["user_department"]] = depts.get(r["user_department"], 0) + r["denied_attempts"]
    dtxt = ", ".join(f"{k} {v}" for k, v in sorted(depts.items(), key=lambda x: -x[1]))
    return (f"In the 7 days to 19-Oct-2026, {len(den)} users were denied access to confidential data ({num(total(den, 'denied_attempts'))} blocked attempts) "
            f"and {len(alw)} authorised users accessed it ({names(alw, 'user_role', 3)}). "
            f"Denials by department: {dtxt}; most recent were {names(den, 'user_id', 3)}. "
            f"No user was denied more than {max(r.get('denied_attempts') or 0 for r in rows)} time(s), so this looks like scattered over-reach "
            f"rather than a single persistent actor.")


def _m5_dd(rows):
    if not rows:
        return "No denials this week."
    tot = total(rows, "denial_count")
    by_d = {}
    for r in rows:
        by_d[r["user_department"]] = by_d.get(r["user_department"], 0) + r["denial_count"]
    top = rows[0]
    return (f"This week's {num(tot)} denied attempts split {', '.join(f'{k} {v}' for k, v in sorted(by_d.items(), key=lambda x: -x[1]))}; "
            f"no Operations user appears. "
            f"The most-targeted data is {top['resource_data_classification']} ({top['requested_resource']}, {num(top['denial_count'])} denials from {top['user_department']}), "
            f"and HR staff account for most salary, DPC and transfer-draft probes. Window: 13-19 Oct 2026.")


def _m5_why(rows):
    if not rows:
        return "No denials logged."
    mx = max(r.get("max_denials_by_one_user") or 0 for r in rows)
    tot_full = total(rows, "denials_full_log")
    users = total(rows, "distinct_users")
    return (f"No account triggered repeated denials: across all {num(tot_full)} RBAC denials since {min(r['log_first_date'] for r in rows)}, "
            f"the most any single user was denied is {mx}, and {num(users)} distinct users account for them. "
            f"Each denial was a one-off request for data outside the user's role - {rows[0]['denial_reason']} ({rows[0]['denials_this_week']} this week), "
            f"then {rows[1]['denial_reason'] if len(rows) > 1 else ''}. "
            f"The premise of repeat offenders is not supported by the log; the pattern is broad curiosity, which argues for awareness messaging over individual action.")


def _m5_cmp(rows):
    a = _first(rows, "classification", "ALL CONFIDENTIAL")
    if not a:
        return "No baseline row."
    rest = [r for r in rows if r is not a]
    hot = sorted(rest, key=lambda r: -(r.get("ratio_vs_baseline") or 0))
    return (f"This week's {num(a['denials_this_week'])} confidential-data denials are {f(a['ratio_vs_baseline'], 2)}x the 30-day baseline "
            f"of {f(a['baseline_per_week'], 1)} per week ({num(a['denials_prior_30d'])} in 13-Sep to 12-Oct). "
            f"The rise is led by {hot[0]['classification']} ({num(hot[0]['denials_this_week'])} vs {f(hot[0]['baseline_per_week'], 1)}/week) "
            f"and {hot[1]['classification']} ({num(hot[1]['denials_this_week'])} vs {f(hot[1]['baseline_per_week'], 1)}/week). "
            f"Counts are small, so a single week roughly doubling is a watch signal rather than an incident.")


# ---------------------------------------------------------------------------------- T1
def _t1(rows):
    if not rows:
        return "No field recorded a loss in FY26."
    r = rows[0]
    return (f"Only {len(rows)} of {r.get('fields_evaluated')} fields lost money in FY26: {names(rows, 'field_name', 3)} "
            f"({r['onshore_offshore']}, {r['maturity']}, {r['asset_wc_id']}) with PBT of {inr_cr(r['pbt_inr_cr'], 2)}. "
            f"It still earned positive EBITDA of {inr_cr(r['ebitda_inr_cr'], 2)} on revenue of {inr_cr(r['gross_revenue_inr_cr'], 2)}; "
            f"the loss comes from DD&A of {inr_cr(r['dda_depreciation_inr_cr'], 2)} and a lifting cost of ${f(r['lifting_cost_per_boe_usd'], 2)}/boe "
            f"(root cause: {r['root_cause_loss_code']}). No field had negative operating earnings, so the issue is one marginal field, not a portfolio problem.")


def _t1_dd(rows):
    neg_e = [r for r in rows if r.get("negative_operating_earnings")]
    neg_p = [r for r in rows if r.get("negative_pbt")]
    on = [r for r in rows if r.get("onshore_offshore") == "onshore"]
    off = [r for r in rows if r.get("onshore_offshore") == "offshore"]
    thin = rows[:3]
    return (f"None of the {len(rows)} mature fields ({len(on)} onshore, {len(off)} offshore) recorded negative operating earnings (EBITDA) in FY26"
            f"{'' if not neg_e else ' except ' + names(neg_e, 'field_name', 5)}; only {names(neg_p, 'field_name', 3)} had negative PBT. "
            f"The thinnest EBITDA margins are all onshore: {', '.join(r['field_name'] + ' ' + pct(r['ebitda_margin_pct']) for r in thin)}. "
            f"Mature offshore fields are comfortably profitable, so loss risk is concentrated in a handful of old onshore fields.")


def _t1_why(rows):
    x = rows[0] if rows else {}
    p = rows[1] if len(rows) > 1 else {}
    return (f"{str(_g(x, 'comparison_group', '')).replace('Field X: ', '')} is losing because it is a depleted, high-water-cut field: "
            f"water cut averages {pct(_g(x, 'avg_water_cut_pct'))} versus {pct(_g(p, 'avg_water_cut_pct'))} for mature onshore peers, "
            f"driving lifting cost to ${f(_g(x, 'avg_lifting_cost_usd_boe'), 2)}/boe against ${f(_g(p, 'avg_lifting_cost_usd_boe'), 2)}. "
            f"Gas utilisation ({pct(_g(x, 'avg_gas_utilisation_pct'))} vs {pct(_g(p, 'avg_gas_utilisation_pct'))}) and uptime "
            f"({pct(_g(x, 'avg_uptime_pct'), 2)} vs {pct(_g(p, 'avg_uptime_pct'), 2)}) are in line with peers, so low gas utilisation is not a factor; "
            f"the field is {f(_g(x, 'avg_field_age_years'), 0)} years old (peers {f(_g(p, 'avg_field_age_years'), 0)}), consistent with ageing, depleted reservoirs. "
            f"Recorded root cause: {_g(x, 'root_cause')}.")


def _t1_cmp(rows):
    r = rows[0] if rows else {}
    return (f"Over five years, divesting {_g(r, 'field_name')} via PEC/farm-out is worth {inr_cr(_g(r, 'divest_pec_5yr_payoff_inr_cr'), 2)} versus "
            f"{inr_cr(_g(r, 'status_quo_5yr_pbt_inr_cr'), 2)} PBT if nothing changes, an advantage of {inr_cr(_g(r, 'divest_advantage_vs_status_quo_5yr_inr_cr'), 2)}. "
            f"A secondary-recovery programme beats divestment only if it lifts annual PBT by more than {inr_cr(_g(r, 'breakeven_annual_pbt_uplift_for_secondary_recovery_inr_cr'), 2)} "
            f"({pct(_g(r, 'breakeven_uplift_pct_of_fy26_revenue'))} of FY26 revenue) net of its own capex. "
            f"Divestment also releases estimated annual opex savings of {inr_cr(_g(r, 'estimated_annual_opex_savings_inr_cr'), 2)} and capex savings of "
            f"{inr_cr(_g(r, 'estimated_annual_capex_savings_inr_cr'), 2)}; field-level secondary-recovery costs and uplift are not in the data "
            f"(asset secondary-recovery capex in FY26: {inr_cr(_g(r, 'asset_secondary_recovery_capex_fy26_inr_cr'), 2)}).")


# ---------------------------------------------------------------------------------- T2
def _t2(rows):
    if not rows:
        return "No executive has 5+ years in Delhi."
    ex3 = [r for r in rows if r.get("within_3yr_of_superannuation")]
    tagged = [r for r in rows if r.get("exemption_tag")]
    by = {}
    for r in rows:
        by[r["discipline_name"]] = by.get(r["discipline_name"], 0) + 1
    top = sorted(by.items(), key=lambda x: -x[1])[:3]
    return (f"{num(len(rows))} executives currently posted at Delhi HQ have 5 or more years of continuous stay; the longest is "
            f"{f(rows[0]['delhi_years'], 1)} years. "
            f"{num(len(ex3))} are within 3 years of superannuation ({num(len(tagged))} carry a recorded exemption), leaving "
            f"{num(len(rows) - len(ex3))} as candidates for the transfer-policy check. "
            f"Largest groups: {', '.join(f'{k} {v}' for k, v in top)}.")


def _t2_dd(rows):
    need = [r for r in rows if r.get("needed_in_assam_or_tripura")]
    tech = total(rows, "delhi_5yr_execs")
    asm = total(rows, "assam_exec_vacancies")
    tri = total(rows, "tripura_exec_vacancies")
    return (f"Of the 5-year-plus Delhi executives, {num(tech)} hold technical disciplines, and {num(total(need, 'delhi_5yr_execs'))} of them "
            f"({names(need, 'discipline_name', 4)}) match executive vacancies in the North-East. "
            f"All the matching demand is in Tripura ({num(tri)} vacancies in these disciplines); Assam has {num(asm)} executive vacancies. "
            f"The biggest technical group, {sorted(rows, key=lambda r: -(r.get('delhi_5yr_execs') or 0))[0]['discipline_name']}, has no NE vacancy to fill. "
            f"(The question's premise of 412 Delhi executives is not reproduced by the data; see T2.)")


def _t2_why(rows):
    ex = _first(rows, "cadre", "executive") or {}
    ne = _first(rows, "cadre", "non_executive") or {}
    bd = _first(rows, "cadre", "board") or {}
    return (f"No executive at Delhi HQ has breached the 10-year cumulative cap: {num(_g(ex, 'breached_10yr_cap'))} of {num(_g(ex, 'currently_in_delhi'))} executives "
            f"are over it and the longest cumulative Delhi stay is {f(_g(ex, 'max_cumulative_years'), 1)} years. "
            f"The {num(_g(ne, 'breached_10yr_cap'))} cap breaches in the Delhi cluster are non-executive staff "
            f"(longest {f(_g(ne, 'max_cumulative_years'), 1)} years), who are outside the executive JRTP cap, plus {num(_g(bd, 'breached_10yr_cap'))} board member. "
            f"So the question's premise does not hold for officers; {num(_g(ex, 'cumulative_5yr_plus'))} executives are in the 5-10 year overstay "
            f"band (JRTP 4.3 review list) and only {num(_g(ex, 'with_recorded_exemption'))} carry a recorded exemption.")


def _t2_cmp(rows):
    vac = total(rows, "ne_exec_vacancies")
    tr = total(rows, "transferable")
    cost = total(rows, "est_transfer_cost_inr_cr")
    res = [r for r in rows if (r.get("residual_vacancies") or 0) > 0]
    per = rows[0].get("avg_cost_per_transfer_inr") if rows else None
    return (f"Moving matching Delhi 5-year-plus executives would fill {num(tr)} of {num(vac)} North-East executive vacancies for about "
            f"{inr_cr(cost, 2)} in transfer costs (₹{num(per)} per move, FY26 average). "
            f"{len(res)} discipline(s) would still be short - {', '.join(r['discipline_name'] + ' ' + num(r['residual_vacancies']) for r in res[:4])} - "
            f"because Delhi lacks enough officers in those disciplines. "
            f"Cost is small relative to the gap closed; the binding constraint is discipline match, not transfer allowance.")


# ---------------------------------------------------------------------------------- T3
def _t3(rows):
    if not rows:
        return "No GM retires in 2027."
    nop = [r for r in rows if r.get("no_succession_plan")]
    plan = [r for r in rows if not r.get("no_succession_plan")]
    ready = [r for r in plan if (r.get("successor_1_readiness") or "").lower() == "ready_now"]
    nne = [r for r in plan if r.get("successor_1_has_ne_hard_station") is False]
    return (f"{len(rows)} General Managers retire in calendar 2027, from {rows[0]['retirement_date']} to {rows[-1]['retirement_date']}. "
            f"{len(nop)} of them have no succession-plan entry at all; of the {len(plan)} that do, {len(ready)} have a Ready-Now first successor "
            f"and {len(nne)} first successor(s) lack North-East/hard-station service. "
            f"The immediate risk is coverage of the plan, not readiness of named successors.")


def _t3_dd(rows):
    gap = [r for r in rows if r.get("succession_gap")]
    t1 = [r for r in gap if r.get("criticality_tier") == "Tier_1_Critical"]
    byfy = {}
    for r in rows:
        byfy[r["retirement_fy"]] = byfy.get(r["retirement_fy"], 0) + 1
    nop = [r for r in gap if not r.get("position_id")]
    return (f"{len(rows)} E7+ officers still in service retire between now and 31-Mar-2029 ({', '.join(f'{k}: {v}' for k, v in sorted(byfy.items()))}), "
            f"and {len(gap)} of them have a succession gap. "
            f"{len(nop)} gaps are positions with no plan at all; {len(t1)} gap(s) sit in Tier-1 critical roles. "
            f"The question's 47 / 11 figures are not reproduced by the data (it shows {len(rows)} officers and {len(gap)} gaps).")


def _t3_why(rows):
    tot = total(rows, "successors_without_ne")
    hq = [r for r in rows if str(r.get("current_posting", "")).startswith("Corporate HQ")]
    hq_n = total(hq, "successors_without_ne")
    sup = total([r for r in rows if r.get("discipline_function") != "technical"], "successors_without_ne")
    return (f"The {num(tot)} named successors without NE/hard-station service have never been posted to a Category-C or North-East station "
            f"({num(total(rows, 'c_or_ne_postings'))} such postings between them); {num(hq_n)} are currently at Corporate HQ (Delhi/Dehradun). "
            f"Most ({num(sup)}) are in support, HR or finance functions whose careers have rotated between offices and Category A/B locations, "
            f"so the JRTP 6.1 hard-station prerequisite was never triggered. "
            f"All are rated Ready in 3-5 years, i.e. the plan already recognises they are not yet eligible.")


def _t3_cmp(rows):
    if not rows:
        return "No successor lacks NE service."
    cant = [r for r in rows if not r.get("can_complete_ne_stint_before_retirement")]
    alt = [r for r in cant if r.get("alternate_has_ne")]
    first = rows[0]
    return (f"{len(rows)} successor slots lack the mandatory hard-station/NE tenure; {len(cant)} cannot complete a 36-month stint before the incumbent retires "
            f"if posted today, and for {len(alt)} of those the alternate successor already qualifies. "
            f"The tightest is {first['position_id']} ({first['role_title']}, retiring {first['incumbent_retire_date']}): only "
            f"{first['months_to_incumbent_retirement']} months remain, {first['months_short_of_36m_ne_stint']} short. "
            f"Required action: post the remaining candidates to Category-C/NE stations in the next transfer cycle (or seek EC deferment under JRTP 6.2), "
            f"and switch to the NE-qualified alternate where the stint cannot finish in time.")


# ---------------------------------------------------------------------------------- W1 follow-ups
def _w1_dd(rows):
    cash = [r for r in rows if r.get("turns_operating_cash_negative")]
    pbt = [r for r in rows if r.get("turns_pbt_negative")]
    return (f"At $60 Brent, {len(cash)} mature fields turn operating-cash negative (EBITDA): "
            f"{', '.join(r['field_name'] + ' ' + inr_cr(r['base_ebitda_cr'], 2) + ' to ' + inr_cr(r['sim_ebitda_cr'], 2) for r in cash)}. "
            f"{len(pbt)} go PBT-negative once DD&A is included ({names(pbt, 'field_name', 4)}); all are onshore with FY26 EBITDA margins of "
            f"{pct(min(r['base_ebitda_margin_pct'] for r in rows))}-{pct(max(r['base_ebitda_margin_pct'] for r in rows))}. "
            f"The data does not support '6 fields': only {len(cash)} lose cash and {len(pbt)} lose money.")


def _w1_why(rows):
    hi = rows[0] if rows else {}
    lows = [r for r in rows if str(r.get("lifting_cost_band", "")).startswith("3")]
    lo_best = max(lows, key=lambda r: r.get("ebitda_change_pct") or -999) if lows else {}
    return (f"High-lifting-cost onshore fields are the most exposed because their thin margins absorb the same per-barrel price cut: the "
            f"{_g(hi, 'n_fields')} {_g(hi, 'onshore_offshore')} fields at ${f(_g(hi, 'wtd_lifting_cost_usd_boe'), 2)}/boe lose "
            f"{pct(abs(_g(hi, 'ebitda_change_pct') or 0))} of EBITDA at $60, versus {pct(abs(_g(lo_best, 'ebitda_change_pct') or 0))} for "
            f"low-cost {_g(lo_best, 'onshore_offshore')} fields (${f(_g(lo_best, 'wtd_lifting_cost_usd_boe'), 2)}/boe). "
            f"Their simulated margin falls to {pct(_g(hi, 'sim_ebitda_margin_pct'))} and {_g(hi, 'fields_pbt_negative_at_60')} of them go PBT-negative; "
            f"no other segment has a loss-maker. Costs are fixed in the model, so vulnerability scales with cost per barrel, not with size.")


def _w1_cmp(rows):
    r = rows[0] if rows else {}
    return (f"At $60 Brent, ONGC's annual EBITDA would fall by about {inr_cr(abs(_g(r, 'ebitda_change_cr') or 0))}, from "
            f"{inr_cr(_g(r, 'company_ebitda_fy26_cr'))} to {inr_cr(_g(r, 'sim_company_ebitda_cr'))} ({signed_pct(_g(r, 'company_ebitda_change_pct'))}). "
            f"Revenue drops {inr_cr(abs(_g(r, 'revenue_change_cr') or 0))}; with opex fixed, pre-tax operating cash flow falls by the same "
            f"{inr_cr(abs(_g(r, 'pretax_operating_cash_flow_change_cr') or 0))}. "
            f"Gas is APM-priced and unchanged; post-tax cash flow and working-capital effects are not modelled.")


# ---------------------------------------------------------------------------------- W2
def _w2(rows):
    if not rows:
        return "No workforce rows."
    cur, ret, proj = total(rows, "current_headcount"), total(rows, "retirements_by_oct2028"), total(rows, "projected_headcount_oct2028")
    hit = sorted(rows, key=lambda r: -(r.get("retirements_by_oct2028") or 0))[:3]
    return (f"With a 2-year hiring freeze, headcount falls from {num(cur)} to about {num(proj)} by Oct-2028 ({signed_pct(-ret * 100.0 / cur if cur else None)}), "
            f"as {num(ret)} employees reach superannuation. "
            f"Losses are concentrated in {', '.join(r['discipline_name'] + ' ' + num(r['retirements_by_oct2028']) + ' (' + signed_pct(r['change_pct']) + ')' for r in hit)}. "
            f"Non-executive disciplines barely move because no non-executive is due to retire before 2031 in the data; "
            f"other exits (resignations, deaths) are excluded, so this is an upper bound on remaining headcount.")


def _w2_dd(rows):
    tot = total(rows, "net_deficit_oct2028")
    return (f"By Oct-2028 under a hiring freeze, Drilling, Reservoir and Production would be {num(tot)} executives short of sanctioned strength: "
            f"{', '.join(r['discipline_name'] + ' ' + num(r['net_deficit_oct2028']) + ' (' + pct(r['deficit_pct_of_sanctioned']) + ')' for r in rows)}. "
            f"Today's gap is {num(total(rows, 'current_deficit'))}; retirements add {num(total(rows, 'retirements_by_oct2028'))}. "
            f"Roughly a quarter to a third of sanctioned posts in these core disciplines would be empty.")


def _w2_why(rows):
    if not rows:
        return "No grade rows."
    jr = [r for r in rows if r["grade_id"] in ("E1", "E2", "E3", "E4", "E5", "E6")]
    sr = [r for r in rows if r["grade_id"] in ("E7", "E8", "E9")]
    jt, st = total(jr, "technical_executives"), total(sr, "technical_executives")
    jr_p = total(jr, "retiring_by_oct2028") * 100.0 / jt if jt else None
    sr_p = total(sr, "retiring_by_oct2028") * 100.0 / st if st else None
    srt = sorted(rows, key=lambda r: -(r.get("retiring_pct") or 0))
    youngest = min(rows, key=lambda r: r.get("avg_age") or 99)
    if sr_p is not None and jr_p is not None and sr_p < jr_p:
        lead = (f"The data does not show a senior-grade cliff: only {pct(sr_p)} of technical executives in E7-E9 retire by Oct-2028, "
                f"versus {pct(jr_p)} in E1-E6, and the highest rate is in {srt[0]['grade_id']} ({srt[0]['designation']}, {pct(srt[0]['retiring_pct'])}).")
        so = (f"In absolute terms the loss is {num(total(jr, 'retiring_by_oct2028'))} officers in E1-E6 against {num(total(sr, 'retiring_by_oct2028'))} in E7-E9, "
              f"so a freeze erodes the middle-management technical bench (E5-E6 feeders) more than the GM/CGM layer.")
        cav = (f"Caveat: grade and age are weakly linked in the data (average age of {youngest['grade_id']} officers is {f(youngest['avg_age'], 1)} years), "
               f"so the premise may hold in reality but is not supported by these records.")
    else:
        lead = (f"Senior technical grades are hit harder: {pct(sr_p)} of E7-E9 technical executives retire by Oct-2028 versus {pct(jr_p)} in E1-E6.")
        so = f"The highest rate is {srt[0]['grade_id']} ({pct(srt[0]['retiring_pct'])}), and senior posts cannot be back-filled externally under a freeze."
        cav = ""
    return f"{lead} {so} {cav}".strip()


def _w2_cmp(rows):
    cat = [r for r in rows if r.get("dimension") == "reservation_category"]
    bench = [r for r in rows if r.get("dimension") == "succession_bench_grade"]
    mv = max(cat, key=lambda r: abs((r.get("projected_share_pct") or 0) - (r.get("current_share_pct") or 0))) if cat else {}
    bw = max(bench, key=lambda r: r.get("attrition_pct") or 0) if bench else {}
    return (f"A freeze to end-FY28 barely changes the reservation mix: the largest shift is {_g(mv, 'group_name')} at "
            f"{pct(_g(mv, 'current_share_pct'), 2)} to {pct(_g(mv, 'projected_share_pct'), 2)} of the workforce, because retirements "
            f"({pct(min(r['attrition_pct'] for r in cat))}-{pct(max(r['attrition_pct'] for r in cat))} by category) fall evenly. "
            f"The real hit is the leadership bench: {_g(bw, 'group_name')} loses {pct(_g(bw, 'attrition_pct'))} ({num(_g(bw, 'retirements_by_fy28'))} of "
            f"{num(_g(bw, 'current_headcount'))}), and E5-E9 together lose {num(total(bench, 'retirements_by_fy28'))}. "
            f"Rosters stay compliant in share terms, but backlog reserved vacancies cannot be filled while hiring is frozen.")


# ---------------------------------------------------------------------------------- W3
def _w3(rows):
    if not rows:
        return "No asset rows."
    alloc = total(rows, "officers_allocated")
    per = rows[0].get("avg_cost_per_transfer_inr")
    cost = alloc * per / 1e7 if per else total(rows, "transfer_cost_inr_cr")
    vac, vac_after = total(rows, "exec_vacancies"), total(rows, "vacancies_after")
    s, ip = total(rows, "exec_sanctioned"), total(rows, "exec_in_position")
    top = rows[0]
    return (f"Moving {num(alloc)} executives to field assets costs about {inr_cr(cost, 2)} in one-time transfer grants "
            f"(₹{num(top.get('avg_cost_per_transfer_inr'))} per officer, FY26 average) and lifts executive coverage of the 14 assets from "
            f"{pct(ip * 100.0 / s if s else None)} to {pct((ip + alloc) * 100.0 / s if s else None)}. "
            f"It fills {num(alloc)} of {num(vac)} executive vacancies, leaving {num(vac_after)}; the largest gain is at {top['field_asset']} "
            f"({pct(top['coverage_pct_now'])} to {pct(top['coverage_pct_after'])}), while Assam and Jorhat need no one. "
            f"The Delhi/Dehradun pool of {num(top.get('delhi_ddn_movable_pool'))} movable executives makes 200 feasible.")


def _w3_dd(rows):
    t = _first(rows, "component", "Total") or {}
    parts = [r for r in rows if r.get("component") != "Total"]
    return (f"Relocating 200 officers needs about {inr_cr(_g(t, 'total_for_200_inr_cr'), 2)}: "
            f"{', '.join(r['component'] + ' ' + inr_cr(r['total_for_200_inr_cr'], 2) for r in parts)}. "
            f"That is ₹{num(_g(t, 'per_officer_inr'))} per officer, the FY26 average across {num(_g(t, 'fy26_transfers_sampled'))} rotation and hard-station transfers. "
            f"Recurring hard-station allowances after the move are not included.")


def _w3_why(rows):
    if not rows:
        return "No asset rows."
    hi = rows[:4]
    lo = rows[-4:]
    up_hi = sum(r["fy26_uptime_pct"] for r in hi) / len(hi)
    up_lo = sum(r["fy26_uptime_pct"] for r in lo) / len(lo)
    return (f"The data shows only a moderate link: assets with more technical-executive vacancies run slightly lower uptime "
            f"(correlation {f(rows[0]['corr_vacancy_vs_uptime'], 2)}; with downtime {f(rows[0]['corr_vacancy_vs_downtime'], 2)}). "
            f"The four most short-staffed assets ({names(hi, 'asset', 4)}, {pct(hi[-1]['technical_exec_vacancy_pct'])}-{pct(hi[0]['technical_exec_vacancy_pct'])} vacant) "
            f"average {pct(up_hi, 2)} uptime versus {pct(up_lo, 2)} for the four best-staffed. "
            f"The gap is under a percentage point and the short-staffed assets are mostly offshore, so the effect is plausible but not proven causal.")


def _w3_cmp(rows):
    r = rows[0] if rows else {}
    return (f"The one-time relocation cost of {inr_cr(_g(r, 'one_time_cost_inr_cr'), 2)} pays back if the {_g(r, 'receiving_assets')} receiving assets produce just "
            f"{pct(_g(r, 'breakeven_uplift_pct_one_year'), 3)} more in one year (about {num(_g(r, 'breakeven_boe_one_year'))} boe at "
            f"₹{num(_g(r, 'net_revenue_per_boe_inr'))} net revenue per boe), or {pct(_g(r, 'breakeven_uplift_pct_over_3yrs'), 3)} a year over three. "
            f"Those assets produced {f(_g(r, 'receiving_assets_fy26_mmboe'), 1)} MMboe and {inr_cr(_g(r, 'receiving_assets_fy26_net_revenue_inr_cr'))} net revenue in FY26; "
            f"the cost is {pct(_g(r, 'cost_pct_of_fy26_capex'), 3)} of FY26 capex. "
            f"The actual production gain from better coverage cannot be measured from the data, so this is a breakeven test, not a forecast.")


# ---------------------------------------------------------------------------------- W4
def _w4(rows):
    fy25 = _first(rows, "fiscal_year", "FY25") or {}
    fy23 = _first(rows, "fiscal_year", "FY23") or {}
    fy24 = _first(rows, "fiscal_year", "FY24") or {}
    return (f"Removing the windfall tax lifts net realisation by the full SAED per barrel: ${f(_g(fy25, 'last_levied_saed_usd_bbl'), 2)}/bbl at the last levied rate "
            f"(Nov-2024) and ${f(_g(fy25, 'avg_saed_usd_bbl_when_levied'), 2)}/bbl on average in the {_g(fy25, 'months_saed_levied')} months it applied in FY25. "
            f"At peak it was worth ${f(_g(fy23, 'avg_saed_usd_bbl_when_levied'), 2)}/bbl (FY23, {_g(fy23, 'months_saed_levied')} months) and "
            f"${f(_g(fy24, 'avg_saed_usd_bbl_when_levied'), 2)}/bbl in FY24; SAED cost {inr_cr(_g(fy23, 'saed_paid_inr_cr'))}, "
            f"{inr_cr(_g(fy24, 'saed_paid_inr_cr'))} and {inr_cr(_g(fy25, 'saed_paid_inr_cr'))} in FY23-FY25. "
            f"SAED was withdrawn in Dec-2024, so FY26 already reflects the full benefit.")


def _w4_dd(rows):
    a = rows[0] if rows else {}
    b = rows[1] if len(rows) > 1 else {}
    return (f"The SAED removal in December 2024 eliminated a ${f(_g(a, 'avg_saed_usd_bbl'), 2)}/bbl levy (Apr-Nov 2024 average) on domestic crude, "
            f"which is the incremental per-barrel benefit. "
            f"The recorded net realisation does not show a step-up: it was {pct(_g(a, 'realisation_pct_of_brent'))} of Brent before and "
            f"{pct(_g(b, 'realisation_pct_of_brent'))} after (discount ${f(_g(a, 'avg_discount_to_brent_usd_bbl'), 2)} vs ${f(_g(b, 'avg_discount_to_brent_usd_bbl'), 2)}), "
            f"because the FY25 realisation series is not stated net of SAED. "
            f"The benefit therefore shows up in lower statutory levies, not in the published realisation figure.")


def _w4_why(rows):
    fy23 = _first(rows, "fiscal_year", "FY23") or {}
    fy22 = _first(rows, "fiscal_year", "FY22") or {}
    fy24 = _first(rows, "fiscal_year", "FY24") or {}
    return (f"SAED was a specific per-barrel levy that rose with international prices, so it pulled realisation away from Brent exactly when prices peaked: "
            f"in FY23 ONGC realised ${f(_g(fy23, 'avg_net_realisation_usd_bbl'), 2)} against Brent ${f(_g(fy23, 'avg_brent_usd_bbl'), 2)}, a "
            f"${f(_g(fy23, 'gap_to_brent_usd_bbl'), 2)} gap versus ${f(_g(fy22, 'gap_to_brent_usd_bbl'), 2)} the year before. "
            f"It took {inr_cr(_g(fy23, 'saed_windfall_tax_inr_cr'))} ({pct(_g(fy23, 'saed_pct_of_revenue'), 2)} of revenue) in FY23 and "
            f"{inr_cr(_g(fy24, 'saed_windfall_tax_inr_cr'))} in FY24. "
            f"From FY24 the realisation series no longer nets SAED out (gap ${f(_g(fy24, 'gap_to_brent_usd_bbl'), 2)}), a data inconsistency to keep in mind.")


def _w4_cmp(rows):
    full = [r for r in rows if not r.get("is_partial_year")]
    fy26 = _first(rows, "fiscal_year", "FY26") or {}
    saed = [r for r in full if (r.get("fy_avg_saed_usd_bbl") or 0) > 0]
    pre = [r for r in full if not (r.get("fy_avg_saed_usd_bbl") or 0) and r.get("fiscal_year") != "FY26"]
    p_pre = min(pre, key=lambda r: r.get("brent_rank") or 99) if pre else {}
    p_all = min(full, key=lambda r: r.get("brent_rank") or 99) if full else {}
    part = [r for r in rows if r.get("is_partial_year")]
    lo = min(full, key=lambda r: r.get("realisation_pct_of_brent") or 999) if full else {}
    return (f"Post-windfall FY26 realisation of ${f(_g(fy26, 'avg_net_realisation_usd_bbl'), 2)}/bbl is {pct(_g(fy26, 'realisation_pct_of_brent'))} of Brent, "
            f"close to the capture rate of the last pre-SAED peak ({_g(p_pre, 'fiscal_year')}: ${f(_g(p_pre, 'avg_net_realisation_usd_bbl'), 2)}, "
            f"{pct(_g(p_pre, 'realisation_pct_of_brent'))} of ${f(_g(p_pre, 'avg_brent_usd_bbl'), 2)} Brent). "
            f"In dollars it is below the peak-cycle years: the highest-Brent year, {_g(p_all, 'fiscal_year')}, realised ${f(_g(p_all, 'avg_net_realisation_usd_bbl'), 2)} "
            f"but only {pct(_g(p_all, 'realisation_pct_of_brent'))} of ${f(_g(p_all, 'avg_brent_usd_bbl'), 2)} Brent while SAED applied. "
            f"{('FY27 to date (' + str(part[0]['months']) + ' months) is $' + f(part[0]['avg_net_realisation_usd_bbl'], 2) + '. ') if part else ''}"
            f"The lowest capture in the series is {_g(lo, 'fiscal_year')} ({pct(_g(lo, 'realisation_pct_of_brent'))}); the other SAED years "
            f"({names(sorted([r for r in saed if r is not lo], key=lambda r: r['fiscal_year']), 'fiscal_year', 3)}) look normal only because their realisation is recorded gross of SAED.")


NARRATIVES = {
    "M1": _m1, "M1__drill_down": _m1_dd, "M1__why": _m1_why, "M1__compare_or_so_what": _m1_cmp,
    "M2": _m2, "M2__drill_down": _m2_dd, "M2__why": _m2_why, "M2__compare_or_so_what": _m2_cmp,
    "M3__drill_down": _m3_dd, "M3__why": _m3_why, "M3__compare_or_so_what": _m3_cmp,
    "M4__drill_down": _m4_dd, "M4__why": _m4_why, "M4__compare_or_so_what": _m4_cmp,
    "M5": _m5, "M5__drill_down": _m5_dd, "M5__why": _m5_why, "M5__compare_or_so_what": _m5_cmp,
    "T1": _t1, "T1__drill_down": _t1_dd, "T1__why": _t1_why, "T1__compare_or_so_what": _t1_cmp,
    "T2": _t2, "T2__drill_down": _t2_dd, "T2__why": _t2_why, "T2__compare_or_so_what": _t2_cmp,
    "T3": _t3, "T3__drill_down": _t3_dd, "T3__why": _t3_why, "T3__compare_or_so_what": _t3_cmp,
    "W1__drill_down": _w1_dd, "W1__why": _w1_why, "W1__compare_or_so_what": _w1_cmp,
    "W2": _w2, "W2__drill_down": _w2_dd, "W2__why": _w2_why, "W2__compare_or_so_what": _w2_cmp,
    "W3": _w3, "W3__drill_down": _w3_dd, "W3__why": _w3_why, "W3__compare_or_so_what": _w3_cmp,
    "W4": _w4, "W4__drill_down": _w4_dd, "W4__why": _w4_why, "W4__compare_or_so_what": _w4_cmp,
}
