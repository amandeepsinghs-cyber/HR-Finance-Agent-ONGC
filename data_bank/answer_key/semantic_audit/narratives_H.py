"""Narratives for H-series entries (HR: rotation, hard stations, vacancies, attrition, DPC, reservation,
gender, training, grievances, transfer proposal). Rendered from result rows; no typed numbers except
definitional constants from the questions/policy (3 years, 15%, 60 days, statutory norms are in the rows)."""

from semantic_audit.common import f, inr_cr, names, num, pct, signed_pct, total  # noqa: F401


def _g(r, k, default=None):
    return r.get(k, default) if r else default


def _first(rows, key, value):
    for r in rows:
        if r.get(key) == value:
            return r
    return None


def _ratio(a, b):
    return (float(a) * 100.0 / float(b)) if a is not None and b else None


# ----------------------------------------------------------------------------------------- H1
def _h1(rows):
    if not rows:
        return "No active executive has been at the current station for more than 3 years."
    tot = _g(rows[0], "company_total_over_3y")
    act = _g(rows[0], "company_active_executives")
    wc_tot = {}
    for r in rows:
        wc_tot[r["work_centre"]] = r.get("work_centre_total_over_3y") or 0
    top = sorted(wc_tot.items(), key=lambda kv: -kv[1])[:3]
    grade_tot = {}
    for r in rows:
        grade_tot[r["grade_id"]] = grade_tot.get(r["grade_id"], 0) + (r.get("executives_over_3y") or 0)
    tg = sorted(grade_tot.items(), key=lambda kv: -kv[1])[:2]
    exempt = total(rows, "with_recorded_exemption")
    lead = (f"{num(tot)} of {num(act)} active executives ({pct(_ratio(tot, act))}) have been at their current station "
            f"for more than 3 years as of 19-Oct-2026, spread over {len(wc_tot)} work centres.")
    s2 = ("The largest pools are " + ", ".join(f"{k} ({num(v)})" for k, v in top) +
          "; by grade, " + " and ".join(f"{k} ({num(v)})" for k, v in tg) + " dominate — this is the raw "
          "transfer-list universe, far above what one annual transfer cycle can absorb.")
    s3 = (f" Only {num(exempt)} of them carry a recorded exemption; station tenure is measured as the continuous stay at "
          f"the current work centre (in-place promotions do not reset it).")
    return f"{lead} {s2}{s3}"


def _h1_drill(rows):
    if not rows:
        return "No executives exceed 3 years at station."
    jr = next((r for r in rows if "E1-E4" in str(r.get("grade_band"))), None)
    sr = next((r for r in rows if "E6-E9" in str(r.get("grade_band"))), None)
    e5 = next((r for r in rows if "E5" in str(r.get("grade_band")) and "E1" not in str(r.get("grade_band"))), None)
    parts = []
    if jr:
        parts.append(f"{num(jr['executives_over_3y'])} are in E1–E4 ({pct(jr['share_of_over_3y_pct'])} of the over-3-year group)")
    if sr:
        parts.append(f"{num(sr['executives_over_3y'])} in senior management E6–E9 ({pct(sr['share_of_over_3y_pct'])})")
    lead = "Of the executives beyond 3 years at station, " + " versus ".join(parts) + "."
    s2 = ""
    if jr and sr:
        s2 = (f" Overstay is not a junior-grade phenomenon: {pct(jr['pct_of_band_over_3y'])} of all active E1–E4 executives and "
              f"{pct(sr['pct_of_band_over_3y'])} of E6–E9 are past the 3-year norm")
        if e5:
            s2 += f", with E5 at {pct(e5['pct_of_band_over_3y'])} ({num(e5['executives_over_3y'])} officers)"
        s2 += "."
    s3 = (" Non-executive grades are outside the executive rotation policy and are excluded; "
          "there are no active E0 trainees in the population.")
    return lead + s2 + s3


def _h1_why(rows):
    if not rows:
        return "No retention basis could be derived."
    tot = total(rows, "executives")
    nojust = [r for r in rows if "no justification" in str(r.get("retention_basis"))]
    nj = total(nojust, "executives")
    rec = [r for r in rows if str(r.get("retention_basis", "")).startswith("Recorded exemption")]
    age = next((r for r in rows if "Age 57+" in str(r.get("retention_basis"))), None)
    tech = next((r for r in rows if "Critical technical" in str(r.get("retention_basis"))), None)
    beyond = next((r for r in rows if "Beyond 5" in str(r.get("retention_basis"))), None)
    lead = (f"There is no recorded operational justification for {num(nj)} of the {num(tot)} executives beyond 3 years "
            f"({pct(_ratio(nj, tot))}); only {num(total(rec, 'executives'))} carry a formal exemption.")
    s2 = ""
    if age:
        s2 += (f" A further {num(age['executives'])} ({pct(age['share_pct'])}) are aged 57+ and fall under the JRTP 7.1 "
               f"pre-retirement protection although no exemption is tagged")
    if tech:
        s2 += (f"; {num(tech['executives'])} are Drilling/Reservoir/Production specialists within the 5-year technical "
               f"extension window (JRTP 3.3)")
    s2 += "."
    s3 = (f" The bulk — {num(beyond['executives'])} executives averaging {f(beyond['avg_station_years'])} years — are beyond "
          f"even the 5-year outer limit, pointing to stalled transfer cycles rather than documented dependencies.") if beyond else ""
    return lead + s2 + s3


def _h1_cmp(rows):
    comp = _first(rows, "work_centre", "All work centres")
    named = [r for r in rows if r.get("work_centre") != "All work centres"]
    if not named:
        return "No executives found at the named work centres."
    best = max(named, key=lambda r: r.get("tenure_compliance_pct") or 0)
    worst = min(named, key=lambda r: r.get("tenure_compliance_pct") or 0)
    dl = _first(rows, "work_centre", "Delhi HQ")
    lead = (f"Corporate HQ Delhi has the best tenure compliance of the three at {pct(_g(dl, 'tenure_compliance_pct'))} of executives "
            f"within 3 years at station, against {', '.join(f'{r['work_centre']} {pct(r['tenure_compliance_pct'])}' for r in named if r is not dl)}."
            if dl and dl is best else
            f"{best['work_centre']} has the best tenure compliance at {pct(best['tenure_compliance_pct'])}, "
            f"{worst['work_centre']} the worst at {pct(worst['tenure_compliance_pct'])}.")
    s2 = (f" All three are far from compliant — company-wide only {pct(_g(comp, 'tenure_compliance_pct'))} of "
          f"{num(_g(comp, 'active_executives'))} active executives are within the 3-year norm — so HQ is not a privileged "
          f"exception: {num(_g(dl, 'over_3y'))} Delhi executives are past 3 years.") if comp else ""
    s3 = f" {worst['work_centre']} is the weakest, with {num(worst['over_3y'])} of {num(worst['active_executives'])} executives overdue."
    return lead + s2 + s3


# ----------------------------------------------------------------------------------------- H2
def _h2(rows):
    if not rows:
        return "Every active employee has served in a hard station."
    r0 = rows[0]
    tot, act, ex = r0.get("company_never_hard"), r0.get("company_active"), r0.get("executives_never_hard")
    exec_rows = [r for r in rows if str(r.get("cadre")).lower() == "executive"]
    exec_act = total(exec_rows, "active_employees")
    non = [r for r in rows if str(r.get("cadre")).lower() == "non_executive"]
    worst_non = max(non, key=lambda r: r.get("pct_of_grade") or 0) if non else None
    worst_ex = max(exec_rows, key=lambda r: r.get("pct_of_grade") or 0) if exec_rows else None
    lead = (f"{num(tot)} of {num(act)} active employees ({pct(_ratio(tot, act))}) have never served in a Category C "
            f"(hard/remote) station, of whom {num(ex)} are executives ({pct(_ratio(ex, exec_act))} of active executives).")
    s2 = ""
    if worst_non:
        s2 = (f" The gap is concentrated in the non-executive cadre — {worst_non['grade_id']} has "
              f"{num(worst_non['never_served_hard_station'])} never-hard employees ({pct(worst_non['pct_of_grade'])} of the grade)")
    if worst_ex:
        s2 += (f"; among executives the highest share is {worst_ex['grade_id']} at {pct(worst_ex['pct_of_grade'])} "
               f"({num(worst_ex['never_served_hard_station'])} officers), mostly recent entrants yet to be rotated.")
    s3 = " Hard station = any Category C work centre (North-East, offshore, Bokaro CBM, Rajasthan) in the full posting history."
    return lead + s2 + s3


def _h2_drill(rows):
    e4 = _first(rows, "grade_id", "E4")
    e5 = _first(rows, "grade_id", "E5")
    zone = total(rows, "in_zone_of_consideration")
    nh = total(rows, "never_hard_executives")
    lead = (f"Only {num(zone)} of the {num(nh)} never-hard-station E4–E5 executives are currently in the zone of consideration "
            f"(residency in grade completed): {num(_g(e4, 'in_zone_of_consideration'))} E4s for E5 and "
            f"{num(_g(e5, 'in_zone_of_consideration'))} E5s for E6.")
    s2 = (f" The rest are recent promotees averaging {f(_g(e4, 'avg_years_in_grade'))} (E4) and {f(_g(e5, 'avg_years_in_grade'))} (E5) "
          f"years in grade against a {num(_g(e4, 'residency_norm_years'))}-year residency norm, so the issue will bite in the "
          f"coming DPC cycles.")
    s3 = (f" Under JRTP 6.2 the E4s cannot be empanelled for E5 without Category C tenure — {num(_g(e4, 'with_pending_dpc'))} of "
          f"them already sits in a pending DPC — so they should be prioritised for hard-station postings now.")
    return lead + s2 + s3


def _h2_why(rows):
    if not rows:
        return "No posting history found for never-hard executives."
    tot = rows[0].get("never_hard_execs_total")
    tech = rows[0].get("never_hard_technical")
    top = rows[:4]
    lead = (f"The {num(tot)} never-hard executives have rotated within a few non-hard clusters: "
            + ", ".join(f"{r['cluster_name']} ({pct(r['pct_of_never_hard_execs'])} have served there)" for r in top) + ".")
    s2 = (f" {num(tech)} of them ({pct(_ratio(tech, tot))}) are in technical disciplines that JRTP 6.1 requires to complete "
          f"a 3-year Category C stint, so the pattern reflects transfers kept inside home clusters rather than a policy carve-out.")
    s3 = (f" The data records no exemption or deferment for this group; the largest current concentration is "
          f"{rows[0]['cluster_name']} ({num(rows[0]['currently_posted'])} posted there today).")
    return lead + s2 + s3


def _h2_cmp(rows):
    hr = _first(rows, "discipline", "Human Resources (HR)")
    fa = _first(rows, "discipline", "Finance & Accounts (F&A)")
    dr = _first(rows, "discipline", "Drilling")
    pr = _first(rows, "discipline", "Production")
    al = _first(rows, "discipline", "All executives")
    sup = [r for r in (hr, fa) if r]
    ops = [r for r in (dr, pr) if r]
    sup_pct = _ratio(total(sup, "never_hard"), total(sup, "active_executives"))
    ops_pct = _ratio(total(ops, "never_hard"), total(ops, "active_executives"))
    mult = (sup_pct / ops_pct) if sup_pct and ops_pct else None
    lead = (f"HR and Finance executives are far more likely never to have served a hard station — {pct(_g(hr, 'pct_never_hard'))} (HR) "
            f"and {pct(_g(fa, 'pct_never_hard'))} (F&A) versus {pct(_g(dr, 'pct_never_hard'))} (Drilling) and "
            f"{pct(_g(pr, 'pct_never_hard'))} (Production), about {f(mult)} times the rate.")
    s2 = (f" In absolute terms HR and F&A account for {num((_g(hr, 'never_hard') or 0) + (_g(fa, 'never_hard') or 0))} "
          f"never-hard executives versus {num((_g(dr, 'never_hard') or 0) + (_g(pr, 'never_hard') or 0))} in Drilling and "
          f"Production combined, despite having far fewer officers.")
    s3 = (f" The company average is {pct(_g(al, 'pct_never_hard'))} of {num(_g(al, 'active_executives'))} executives — "
          f"a fair-rotation drive should start with corporate support cadres.")
    return lead + s2 + s3


# ----------------------------------------------------------------------------------------- H3
def _h3(rows):
    if not rows:
        return "No sanctioned-post data for FY26."
    cs, cv = rows[0].get("company_sanctioned"), rows[0].get("company_vacancies")
    wc = {}
    for r in rows:
        a = wc.setdefault(r["work_centre"], [0, 0])
        a[0] += r.get("sanctioned") or 0
        a[1] += r.get("vacancies") or 0
    topwc = sorted(wc.items(), key=lambda kv: -kv[1][1])[:3]
    top = rows[0]
    lead = (f"FY26 vacancy position: {num(cs)} sanctioned posts against {num(cs - cv)} in position, leaving {num(cv)} vacancies "
            f"({pct(_ratio(cv, cs))}).")
    s2 = (" The gap is concentrated offshore: " +
          ", ".join(f"{k} {num(v[1])} vacancies ({pct(_ratio(v[1], v[0]))})" for k, v in topwc) +
          f"; the single largest cell is {top['discipline']} at {top['work_centre']} "
          f"({num(top['vacancies'])} of {num(top['sanctioned'])}, {pct(top['vacancy_rate_pct'])}).")
    zero = [k for k, v in wc.items() if v[1] == 0]
    s3 = f" {len(zero)} work centres have no vacancies at all; rates are weighted (vacancies ÷ sanctioned), not averaged across cells."
    return lead + s2 + s3


def _h3_drill(rows):
    over = [r for r in rows if r.get("exceeds_15pct")]
    if over:
        lead = f"{len(over)} critical discipline(s) exceed a 15% vacancy deficit: {names(over, 'discipline', 5)}."
    else:
        mx = rows[0] if rows else None
        lead = (f"None of the critical disciplines exceeds a 15% vacancy deficit company-wide; the highest is "
                f"{_g(mx, 'discipline')} at {pct(_g(mx, 'vacancy_rate_pct'))}.")
    hot = [r for r in rows if (r.get("work_centres_above_15pct") or 0) > 0]
    s2 = (" Pockets do breach 15% locally: " +
          ", ".join(f"{r['discipline']} in {num(r['work_centres_above_15pct'])} work centre(s), worst {pct(r['worst_work_centre_rate_pct'])}"
                    for r in hot) + ".") if hot else " No individual work centre breaches 15% for these disciplines either."
    prod = _first(rows, "discipline", "Production")
    inst = _first(rows, "discipline", "Instrumentation")
    s3 = (f" Production ({pct(_g(prod, 'vacancy_rate_pct'))}, {num(_g(prod, 'vacancies'))} posts) is the largest absolute gap; "
          f"Instrumentation is at {pct(_g(inst, 'vacancy_rate_pct'))}. 'Petroleum' is mapped to Production, Drilling and Reservoir; "
          f"'Chemical' to Chemistry.")
    return lead + s2 + s3


def _h3_why(rows):
    ne = next((r for r in rows if "North-East" in str(r.get("region"))), None)
    eo = next((r for r in rows if "Eastern Offshore" in str(r.get("region"))), None)
    wo = next((r for r in rows if "Western offshore" in str(r.get("region"))), None)
    rest = next((r for r in rows if "Rest" in str(r.get("region"))), None)
    lead = (f"The data does not show a persistent North-East gap — NE vacancy is {pct(_g(ne, 'vacancy_rate_pct'))} versus "
            f"{pct(_g(rest, 'vacancy_rate_pct'))} for the rest of the company — the real shortfall is offshore: Eastern Offshore "
            f"(KG deepwater) {pct(_g(eo, 'vacancy_rate_pct'))} and Western offshore {pct(_g(wo, 'vacancy_rate_pct'))}.")
    s2 = (f" Exits are not the driver (separations run at {f(_g(eo, 'separations_per_100_posts'))}–{f(_g(wo, 'separations_per_100_posts'))} "
          f"per 100 posts offshore, similar to {f(_g(rest, 'separations_per_100_posts'))} elsewhere); Western offshore received only "
          f"{f(_g(wo, 'transfer_ins_per_100_posts'))} transfer-ins per 100 posts in FY26 against {num(_g(wo, 'vacancies'))} open posts.")
    s3 = (f" NE inflow was the weakest at {f(_g(ne, 'transfer_ins_per_100_posts'))} per 100 posts, but low NE vacancies "
          f"({num(_g(ne, 'vacancies'))}) more likely reflect long incumbent stays than successful replenishment.")
    return lead + s2 + s3


def _h3_cmp(rows):
    asm = _first(rows, "work_centre", "Assam Asset")
    meh = _first(rows, "work_centre", "Mehsana Asset")
    ahm = _first(rows, "work_centre", "Ahmedabad Asset")
    al = _first(rows, "work_centre", "All work centres")
    lead = (f"Assam Asset's executive vacancy rate is {pct(_g(asm, 'exec_vacancy_rate_pct'))} ({num(_g(asm, 'exec_in_position'))} in "
            f"position against {num(_g(asm, 'exec_sanctioned'))} sanctioned), well below Mehsana {pct(_g(meh, 'exec_vacancy_rate_pct'))} "
            f"and Ahmedabad {pct(_g(ahm, 'exec_vacancy_rate_pct'))}.")
    s2 = (f" Western Onshore therefore carries {num((_g(meh, 'exec_vacancies') or 0) + (_g(ahm, 'exec_vacancies') or 0))} executive "
          f"vacancies between the two assets, at or above the company executive rate of {pct(_g(al, 'exec_vacancy_rate_pct'))}.")
    s3 = " The hard-station premise does not hold for executives at Assam in FY26; any transfer drive should target Western Onshore and offshore."
    return lead + s2 + s3


# ----------------------------------------------------------------------------------------- H4
def _h4(rows):
    mid = [r for r in rows if r.get("is_mid_career")]
    def rate(rs, fy):
        v = total(rs, f"voluntary_{fy}")
        h = total(rs, f"opening_hc_{fy}")
        return v, _ratio(v, h)
    v24, r24 = rate(mid, "fy24")
    v25, r25 = rate(mid, "fy25")
    v26, r26 = rate(mid, "fy26")
    t24, t25, t26 = total(rows, "total_exits_fy24"), total(rows, "total_exits_fy25"), total(rows, "total_exits_fy26")
    a24, a25, a26 = total(rows, "voluntary_fy24"), total(rows, "voluntary_fy25"), total(rows, "voluntary_fy26")
    rising = r26 is not None and r24 is not None and r26 > r24
    lead = (f"Yes — mid-career (E3–E5) voluntary attrition is rising sharply: {num(v24)} exits in FY24 ({pct(r24, 2)} of opening headcount), "
            f"{num(v25)} in FY25 ({pct(r25, 2)}) and {num(v26)} in FY26 ({pct(r26, 2)})." if rising else
            f"Mid-career (E3–E5) voluntary attrition is not rising: {num(v24)} (FY24), {num(v25)} (FY25), {num(v26)} (FY26).")
    s2 = (f" Total separations were {num(t24)}, {num(t25)} and {num(t26)} in FY24–FY26, overwhelmingly superannuation; voluntary "
          f"exits (resignation + VRS) were {num(a24)}, {num(a25)} and {num(a26)}.")
    e4 = _first(rows, "grade_id", "E4")
    e5 = _first(rows, "grade_id", "E5")
    first = e4 and e5 and not (e4.get("voluntary_fy24") or e4.get("voluntary_fy25") or e5.get("voluntary_fy24") or e5.get("voluntary_fy25"))
    s3 = ((f" FY26 is the first year in the window that E4/E5 officers resigned at all ({num(_g(e4, 'voluntary_fy26'))} E4 and "
           f"{num(_g(e5, 'voluntary_fy26'))} E5 exits), signalling a new leak of experienced managers") if first else
          f" E4 voluntary exits reached {num(_g(e4, 'voluntary_fy26'))} in FY26") + \
        f"; FY25's very low voluntary count ({num(a25)}) looks anomalous and should be verified."
    return lead + s2 + s3


def _h4_drill(rows):
    if not rows:
        return "No mid-career voluntary exits recorded."
    tot = total(rows, "mid_career_voluntary_exits")
    top = rows[:3]
    named = {r["discipline"]: r for r in rows}
    it = named.get("Information Technology")
    res = named.get("Reservoir")
    lead = (f"Over FY24–FY26, {names(top, 'discipline', 3)} account for the largest shares of the {num(tot)} E3–E5 voluntary "
            f"resignations ({', '.join(pct(r['share_pct']) for r in top)}).")
    fa = named.get("Finance & Accounts (F&A)")
    dr = named.get("Drilling")
    s2 = (f" Of the four named disciplines: Finance {pct(_g(fa, 'share_pct'))}, Drilling {pct(_g(dr, 'share_pct'))}, "
          f"IT {pct(_g(it, 'share_pct'))} ({num(_g(it, 'mid_career_voluntary_exits'))} exits) and "
          + (f"Reservoir {pct(_g(res, 'share_pct'))}." if res else "Reservoir none."))
    fy = rows[0]
    s3 = f" The FY26 surge is broad-based: {fy['discipline']} alone lost {num(fy['exits_fy26'])} mid-career officers in FY26."
    return lead + s2 + s3


def _h4_why(rows):
    if not rows:
        return "No exit-interview reasons recorded."
    top = rows[0]
    tot = total(rows, "voluntary_exits")
    comp = _first(rows, "exit_interview_reason", "compensation_gap_private_ep")
    lead = (f"Career progression is the dominant exit reason, cited in {num(top['voluntary_exits'])} of {num(tot)} voluntary exits "
            f"FY24–FY26 ({pct(top['share_pct'])}); compensation gap with private E&P accounts for "
            f"{num(_g(comp, 'voluntary_exits'))} ({pct(_g(comp, 'share_pct'))}).") if top.get("exit_interview_reason") == "career_progression" else \
        f"The leading exit reason is {top['exit_interview_reason']} ({pct(top['share_pct'])} of {num(tot)})."
    s2 = ((f" The compensation reason is new and mid-career-heavy: "
           + ("all " if _g(comp, "exits_fy26") == _g(comp, "voluntary_exits") else "")
           + f"{num(_g(comp, 'exits_fy26'))} such cases occurred in FY26 and {num(_g(comp, 'mid_career_e3_e5'))} were E3–E5 officers.")
          if comp else "")
    s3 = (" Location hardship is not a coded reason in the exit data; reasons are reported as recorded (no imputation of missing values).")
    return lead + s2 + s3


def _h4_cmp(rows):
    if not rows:
        return "No mid-career exits."
    top = rows[0]
    on = next((r for r in rows if "Onshore" in str(r.get("location_class"))), None)
    co = next((r for r in rows if "Corporate" in str(r.get("location_class"))), None)
    off = next((r for r in rows if "Offshore" in str(r.get("location_class"))), None)
    lead = (f"Mid-career (E3–E5) executives in corporate offices leave at a higher rate than those in onshore field postings: "
            f"{pct(_g(co, 'avg_annual_voluntary_rate_pct'), 2)} versus {pct(_g(on, 'avg_annual_voluntary_rate_pct'), 2)} a year "
            f"(FY24–FY26 average)." if co and on and (co.get("avg_annual_voluntary_rate_pct") or 0) > (on.get("avg_annual_voluntary_rate_pct") or 0)
            else f"Highest mid-career attrition: {top['location_class']} at {pct(top['avg_annual_voluntary_rate_pct'], 2)} a year.")
    s2 = (f" Offshore sits in between at {pct(_g(off, 'avg_annual_voluntary_rate_pct'), 2)}; in absolute terms onshore lost the most "
          f"officers ({num(_g(on, 'mid_career_voluntary_exits'))}) because it is the largest pool.")
    s3 = " Rates divide FY24–FY26 voluntary exits by the sum of the three opening March headcounts (E3–E5) at those work centres."
    return lead + s2 + s3


# ----------------------------------------------------------------------------------------- H5
def _h5(rows):
    if not rows:
        return "No DPC cases are pending."
    tp = rows[0].get("total_pending")
    e4 = _first(rows, "from_grade_id", "E4")
    e5 = _first(rows, "from_grade_id", "E5")
    lead = (f"{num(tp)} executives are awaiting DPCs that have not been held: {num(_g(e4, 'pending_candidates'))} for E4→E5 and "
            f"{num(_g(e5, 'pending_candidates'))} for E5→E6, the earliest due on {_g(e4, 'earliest_due_date')}.") if e4 else f"{num(tp)} DPC candidates are pending."
    s2 = (f" As of 19-Oct-2026 they are on average {f(_g(e4, 'avg_months_overdue_asof_2026_10_19'))} months overdue (maximum "
          f"{num(_g(e4, 'max_months_overdue_asof_2026_10_19'))}), about "
          f"{f((_g(e4, 'avg_months_overdue_asof_2026_10_19') or 0) / (_g(e4, 'avg_recorded_delay_months') or 1))}x the "
          f"{f(_g(e4, 'avg_recorded_delay_months'))} months recorded in the (stale) delay_months field.")
    s3 = " Every pending case is in the merit-based E4→E5/E5→E6 steps, which gate the DGM/GM pipeline."
    return lead + s2 + s3


def _h5_drill(rows):
    if not rows:
        return "No delayed DPCs."
    tot = total(rows, "pending_candidates")
    disc = sorted({r["discipline"] for r in rows})
    lead = (f"All {num(tot)} DPC cases delayed beyond 6 months are in {' and '.join(disc)}, across the E4→E5 and E5→E6 steps; "
            f"the largest block is {rows[0]['promotion_step']} {rows[0]['discipline']} ({num(rows[0]['pending_candidates'])} candidates).")
    s2 = " " + "; ".join(f"{r['promotion_step']} {r['discipline']}: {num(r['pending_candidates'])}" for r in rows[1:]) + "."
    s3 = (f" These are the core operating cadres, so the delay directly affects field leadership succession; cases are "
          f"{f(min(r['avg_months_overdue_asof_2026_10_19'] for r in rows))}–{f(max(r['avg_months_overdue_asof_2026_10_19'] for r in rows))} "
          f"months past due on average.")
    return lead + s2 + s3


def _h5_why(rows):
    if not rows:
        return "No delay reasons recorded."
    a = rows[0]
    b = rows[1] if len(rows) > 1 else None
    lead = (f"Two bottlenecks explain every delayed DPC: {a['delay_bottleneck_reason']} ({num(a['case_count'])} cases, "
            f"{pct(a['share_pct'])})" + (f" and {b['delay_bottleneck_reason']} ({num(b['case_count'])}, {pct(b['share_pct'])})." if b else "."))
    s2 = (f" Both hit the E4→E5 and E5→E6 steps roughly evenly ({num(a['e4_to_e5'])}/{num(a['e5_to_e6'])} for the first), so "
          f"clearing them would release the whole backlog.")
    s3 = " APAR grading appeals do not appear as a coded reason in the data; the litigation route (CAT stay) is the larger lever."
    return lead + s2 + s3


def _h5_cmp(rows):
    if not rows:
        return "No pending candidates."
    done = total(rows, "residency_completed_awaiting")
    tot = total(rows, "pending_candidates")
    e4 = next((r for r in rows if str(r.get("promotion_step")).startswith("E4")), None)
    e5 = next((r for r in rows if str(r.get("promotion_step")).startswith("E5")), None)
    lead = (f"{num(done)} of the {num(tot)} executives awaiting a DPC ({pct(_ratio(done, tot))}) have already completed the required "
            f"residency in grade and are waiting only for the committee/notification.")
    s2 = (f" By step: {num(_g(e4, 'residency_completed_awaiting'))} of {num(_g(e4, 'pending_candidates'))} E4→E5 candidates "
          f"({pct(_g(e4, 'pct_residency_completed'))}, averaging {f(_g(e4, 'avg_years_in_grade'))} years in grade) and "
          f"{num(_g(e5, 'residency_completed_awaiting'))} of {num(_g(e5, 'pending_candidates'))} E5→E6 "
          f"({pct(_g(e5, 'pct_residency_completed'))}).")
    s3 = (f" Residency norm = {num(_g(e4, 'residency_norm_years'))} years in grade (dim_grade); every month of delay is "
          f"pure entitlement slippage for these officers and a litigation risk.")
    return lead + s2 + s3


# ----------------------------------------------------------------------------------------- H6
def _h6(rows):
    if not rows:
        return "No reservation data."
    miss = [r for r in rows if r.get("meets_norm") is False]
    cats = {}
    for r in miss:
        cats.setdefault(r["category"], []).append(r["grade_id"])
    grades = sorted({r["grade_id"] for r in rows})
    ews_miss = len(cats.get("EWS", []))
    pwd_miss = len(cats.get("PwD", []))
    sc_miss = cats.get("SC", [])
    st_miss = cats.get("ST", [])
    lead = (f"{'Not fully' if miss else 'Yes'}: representation falls short of the statutory norm in {len(miss)} of {len(rows)} grade-category cells "
            f"across {len(grades)} grades, driven by EWS (below 10% in {ews_miss} grades) and PwD (below 4% in {pwd_miss}).")
    s2 = (f" SC is below 15% in {len(sc_miss)} grade(s)" + (f" ({', '.join(sc_miss)})" if sc_miss else "") +
          f" and ST below 7.5% in {len(st_miss)}" + (f" ({', '.join(st_miss)})" if st_miss else "") +
          "")
    obc = [r for r in rows if r["category"] == "OBC"]
    if obc:
        wo = min(obc, key=lambda r: r.get("gap_vs_norm_pp") or 0)
        s2 += f"; OBC's worst cell is {wo['grade_id']} at {pct(wo['representation_pct'])} ({f(wo['gap_vs_norm_pp'])} pp)."
    else:
        s2 += "."
    bl = total([r for r in rows if r["category"] in ("SC", "ST")], "backlog_vacancies")
    s3 = (f" {num(bl)} SC/ST backlog reserved vacancies remain (PwD backlog is a subset). Representation = in-position category strength ÷ grade "
          f"in-position (FY26 sanctioned-posts roster); EWS is a post-2019 quota, so stock representation lags by construction.")
    return lead + s2 + s3


def _h6_drill(rows):
    if not rows:
        return "No E1–E7 data."
    def agg(cat):
        rs = [r for r in rows if r["category"] == cat]
        return rs, total(rs, "backlog_vacancies")
    sc, scb = agg("SC")
    st, stb = agg("ST")
    pw, pwb = agg("PwD")
    ew, _ = agg("EWS")
    ob, _ = agg("OBC")
    def rng(rs):
        v = [r["representation_pct"] for r in rs if r.get("representation_pct") is not None]
        return f"{pct(min(v))}–{pct(max(v))}" if v else "n/a"
    lead = (f"Across E1–E7, representation ranges SC {rng(sc)}, ST {rng(st)}, OBC {rng(ob)}, EWS {rng(ew)} and PwD {rng(pw)}, "
            f"with {num(scb + stb)} SC/ST backlog vacancies (SC {num(scb)}, ST {num(stb)}; PwD {num(pwb)}, overlapping).")
    worst = max((r for r in rows if r["category"] in ("SC", "ST")), key=lambda r: r.get("backlog_vacancies") or 0)
    s2 = (f" The largest backlog is {worst['category']} in {worst['grade_id']} ({num(worst['backlog_vacancies'])} posts, "
          f"representation {pct(worst['representation_pct'])} vs {pct(worst['norm_pct'])} norm).")
    ewb = total(ew, "backlog_vacancies")
    s3 = (f" EWS ({num(ewb)} backlog) and PwD ({num(pwb)}) sit below norm in every grade with little or no backlog, so their "
          f"shortfall is a recruitment-intake issue rather than unfilled reserved posts.")
    return lead + s2 + s3


def _h6_why(rows):
    comp_sc = next((r for r in rows if r.get("discipline") == "All disciplines" and r.get("social_category") == "SC"), None)
    comp_st = next((r for r in rows if r.get("discipline") == "All disciplines" and r.get("social_category") == "ST"), None)
    spec = [r for r in rows if r.get("discipline") != "All disciplines"]
    sb = total(spec, "backlog_vacancies")
    share = total(spec, "share_of_company_backlog_pct")
    discs = sorted({r["discipline"] for r in spec})
    lead = (f"Geoscience is not where the backlog sits: {', '.join(discs)} together hold {num(sb)} SC/ST backlog vacancies, "
            f"{pct(share)} of the company total of {num((_g(comp_sc, 'backlog_vacancies') or 0) + (_g(comp_st, 'backlog_vacancies') or 0))}.")
    s2 = (f" Their backlog runs at a similar share of category vacancies to the company (company SC {pct(_g(comp_sc, 'backlog_pct_of_vacancies'))}, "
          f"ST {pct(_g(comp_st, 'backlog_pct_of_vacancies'))}), i.e. clearance is lagging uniformly, not specifically in specialist disciplines.")
    has_marine = any("Marine" in str(r.get("discipline")) for r in rows)
    s3 = "" if has_marine else " Marine / Naval Architecture has no sanctioned posts in the FY26 roster, so no backlog can be attributed to it."
    return lead + s2 + s3


def _h6_cmp(rows):
    if not rows:
        return "No roster data."
    below = [r for r in rows if (r.get("gap_vs_norm_pp") or 0) < -0.05]
    above = [r for r in rows if (r.get("gap_vs_norm_pp") or 0) > 0.05]
    at = [r for r in rows if abs(r.get("gap_vs_norm_pp") or 0) <= 0.05]
    lead = ("Company-wide, " + "; ".join(f"{r['category']} is at {pct(r['representation_pct'], 2)} vs the {pct(r['norm_pct'])} norm"
                                          for r in rows) + ".")
    s2 = (f" Below the DoPT benchmark: {names(below, 'category', 5)}; at norm: {names(at, 'category', 5)}; above: {names(above, 'category', 5)}.")
    ews = _first(rows, "category", "EWS")
    s3 = (f" The EWS gap ({f(_g(ews, 'gap_vs_norm_pp'), 2)} pp) is structural to a recent quota; the actionable gap is PwD "
          f"and the {num(total([r for r in rows if r['category'] in ('SC', 'ST')], 'backlog_vacancies'))} SC/ST backlog posts.")
    return lead + s2 + s3


# ----------------------------------------------------------------------------------------- H7
def _h7(rows):
    comp = _first(rows, "dimension", "1. Company")
    loc = {r["label"]: r for r in rows if r.get("dimension") == "3. Location class"}
    trend = [r for r in rows if str(r.get("dimension", "")).startswith("4.")]
    grades = [r for r in rows if r.get("dimension") == "2. Grade"]
    assets = [r for r in rows if r.get("dimension") == "5. Asset"]
    off = loc.get("offshore")
    lead = (f"Women are {pct(_g(comp, 'women_pct'))} of active employees ({num(_g(comp, 'women'))} of {num(_g(comp, 'total'))}), "
            f"but only {pct(_g(off, 'women_pct'))} offshore ({num(_g(off, 'women'))} of {num(_g(off, 'total'))}).")
    s2 = ""
    if trend:
        a, b = trend[0].get("women_pct") or 0, trend[-1].get("women_pct") or 0
        verb = "has fallen" if b < a - 0.2 else ("has risen" if b > a + 0.2 else "has stayed flat")
        s2 = (f" Offshore representation {verb}: {pct(trend[0]['women_pct'])} in {trend[0]['label']} ({num(trend[0]['women'])} women) to "
              f"{pct(trend[-1]['women_pct'])} in {trend[-1]['label']} ({num(trend[-1]['women'])}); corporate locations are at "
              f"{pct(_g(loc.get('corporate'), 'women_pct'))} and onshore {pct(_g(loc.get('onshore'), 'women_pct'))}.")
    s3 = ""
    if grades:
        gmax = max(grades, key=lambda r: r.get("women_pct") or 0)
        gmin = min(grades, key=lambda r: r.get("women_pct") or 0)
        s3 = f" By grade the share ranges from {pct(gmin['women_pct'])} ({gmin['label']}) to {pct(gmax['women_pct'])} ({gmax['label']})"
        if assets:
            amin = min(assets, key=lambda r: r.get("women_pct") or 0)
            amax = max(assets, key=lambda r: r.get("women_pct") or 0)
            s3 += (f"; by asset from {pct(amin['women_pct'])} ({amin['label']}) to {pct(amax['women_pct'])} ({amax['label']}, "
                   f"{num(amax['women'])} women — an outlier worth verifying)")
        s3 += "."
    return lead + s2 + s3


def _h7_drill(rows):
    if not rows:
        return "No executives are posted offshore."
    w = total(rows, "women_executives")
    t = total(rows, "executives")
    mh = _first(rows, "work_centre", "Mumbai High")
    zero = [r for r in rows if (r.get("women_executives") or 0) == 0]
    lead = (f"{num(_g(mh, 'women_executives'))} women executives are posted to Mumbai High ({pct(_g(mh, 'women_pct'))} of its "
            f"{num(_g(mh, 'executives'))} executives), and {num(w)} across all offshore work centres ({pct(_ratio(w, t))} of {num(t)}).")
    s2 = " " + ", ".join(f"{r['work_centre']} {num(r['women_executives'])}" for r in rows if r is not mh and (r.get('women_executives') or 0) > 0) + "."
    s3 = (f" {names(zero, 'work_centre', 3)} {'has' if len(zero) == 1 else 'have'} none. Rotational shift rosters are not in the data, "
          f"so this is current offshore posting, not verified 14/14 deployment.") if zero else \
        " Rotational shift rosters are not in the data, so this is current offshore posting, not verified 14/14 deployment."
    return lead + s2 + s3


def _h7_why(rows):
    q = [r for r in rows if r.get("quote_snippet")]
    lead = ("The document corpus contains no policy on offshore accommodation or deployment facilities for women officers, so "
            "the barriers cannot be evidenced from policy (data gap).")
    s2 = ""
    if q:
        s2 = (f" The only facility-related provision found is in {q[0]['heading']}: \"{q[0]['quote_snippet']}\"")
        if len(q) > 1:
            s2 += f" ({q[1]['doc_id']} {q[1]['clause_ref']} repeats the requirement.)"
    s3 = " Combined with women's very low offshore share (see H7 drill-down), female medical cover at remote sites is the one documented dependency to check first."
    return lead + s2 + s3


def _h7_cmp(rows):
    tech = _first(rows, "segment", "Function: technical")
    hr = _first(rows, "segment", "Function: hr")
    fin = _first(rows, "segment", "Function: finance")
    sup = _first(rows, "segment", "Function: support")
    med = _first(rows, "segment", "Discipline: Medical Services")
    comp = _first(rows, "segment", "Company")
    lead = (f"Women are {pct(_g(tech, 'women_pct'))} of technical-discipline staff versus {pct(_g(hr, 'women_pct'))} in HR, "
            f"{pct(_g(fin, 'women_pct'))} in F&A and {pct(_g(sup, 'women_pct'))} in support functions.")
    s2 = (f" Because technical disciplines employ {num(_g(tech, 'employees'))} people, they still hold {num(_g(tech, 'women'))} of the "
          f"{num(_g(comp, 'women'))} women, but at about {f((_g(tech, 'women_pct') or 0) / (_g(hr, 'women_pct') or 1) * 100, 0)}% of HR's representation rate.")
    s3 = f" Medical Services is at {pct(_g(med, 'women_pct'))}; the company average is {pct(_g(comp, 'women_pct'))}."
    return lead + s2 + s3


# ----------------------------------------------------------------------------------------- H8
def _h8(rows):
    if not rows:
        return "No FY26 training data."
    comp = rows[0].get("company_hours_per_executive")
    ex = total(rows, "executives")
    tr = total(rows, "trained_executives")
    hrs = total(rows, "total_hours")
    below = [r for r in rows if r.get("below_company_average")]
    lo, hi = rows[0], rows[-1]
    lead = (f"In FY26 executives received {f(comp)} training hours each on average ({num(hrs)} hours across {num(ex)} executives on rolls); "
            f"{len(below)} of {len(rows)} disciplines are below that average, lowest {lo['discipline']} at {f(lo['hours_per_executive'])} hours.")
    s2 = (f" The spread is narrow ({f(lo['hours_per_executive'])}–{f(hi['hours_per_executive'])} hours, highest {hi['discipline']}); the "
          f"bigger issue is coverage — only {num(tr)} executives ({pct(_ratio(tr, ex))}) attended any programme, and those who did "
          f"averaged {f(hrs / tr if tr else None)} hours.")
    s3 = " No discipline-level training-hour target exists in the data, so 'below target' is measured against the company executive average."
    return lead + s2 + s3


def _h8_drill(rows):
    if not rows:
        return "No FY26 records at these institutes."
    inst = {}
    for r in rows:
        a = inst.setdefault(r["institute"], [0, 0])
        a[0] += r.get("man_days") or 0
        a[1] += r.get("participants") or 0
    parts = [f"{k.replace('_', ' ')} {f(v[0] / v[1] if v[1] else None, 2)} man-days per participant ({num(v[1])} executives)" for k, v in inst.items()]
    top = max(rows, key=lambda r: r.get("man_days_per_participant") or 0)
    low = min(rows, key=lambda r: r.get("man_days_per_participant") or 0)
    lead = "FY26 average man-days at the three institutes: " + "; ".join(parts) + "."
    s2 = (f" By discipline the range is {f(low['man_days_per_participant'], 2)} ({low['discipline']}, {low['institute'].replace('_', ' ')}) to "
          f"{f(top['man_days_per_participant'], 2)} ({top['discipline']}, {top['institute'].replace('_', ' ')}) — programme lengths are "
          f"essentially uniform, so discipline gaps come from participation, not course duration.")
    return lead + s2


def _h8_why(rows):
    if not rows:
        return "No Drilling/Production data."
    comp = rows[0].get("company_hours_per_executive")
    low = rows[0]
    off = [r for r in rows if r.get("location_class") == "offshore"]
    corp = [r for r in rows if r.get("location_class") == "corporate"]
    lead = (f"Field-posted Drilling and Production executives train slightly less than the {f(comp)}-hour company average — lowest "
            f"{low['discipline']} ({low['location_class']}) at {f(low['hours_per_executive'])} hours — while their colleagues in "
            f"corporate locations get {', '.join(f(r['hours_per_executive']) for r in corp)} hours.")
    s2 = (" The gap is driven by participation (" + ", ".join(f"{r['discipline']} {r['location_class']} {pct(r['pct_trained'])} trained" for r in rows[:3]) +
          ") consistent with release constraints at operating sites.")
    s3 = (" Offshore Production is the exception (" + ", ".join(f"{f(r['hours_per_executive'])} hours" for r in off if r['discipline'] == 'Production') +
          "), so the 14/14 shift pattern alone does not explain the shortfall; all differences are within a couple of hours.")
    return lead + s2 + s3


def _h8_cmp(rows):
    if not rows:
        return "No MoU data."
    r26 = _first(rows, "fiscal_year", "FY26") or rows[-1]
    r25 = _first(rows, "fiscal_year", "FY25")
    lead = (f"Against the DPE MoU, ONGC reported {num(r26['mou_reported_person_days'])} training person-days in FY26 — rated "
            f"'{r26['achieved_rating']}' versus the {num(r26['very_good_target'])} Very Good / {num(r26['excellent_target'])} Excellent "
            f"targets — or {f(r26['mou_person_days_per_employee'], 2)} days per employee on the 31-Mar-2026 headcount of "
            f"{num(r26['fy_end_headcount'])}.")
    s2 = (f" The underlying training records support only {num(r26['records_person_days'])} person-days "
          f"({f(r26['records_person_days_per_employee'], 2)} per employee), "
          + (f"below even the {num(r26['good_target'])} Good target" if (r26['records_person_days'] or 0) < (r26['good_target'] or 0)
             else f"short of the reported figure by {num((r26['mou_reported_person_days'] or 0) - (r26['records_person_days'] or 0))}")
          + ", so the MoU claim is not reconcilable to the transaction data.")
    s3 = (f" FY25 shows the same gap ({num(_g(r25, 'mou_reported_person_days'))} reported vs {num(_g(r25, 'records_person_days'))} recorded). "
          f"Rupee training investment per employee is not captured in the data, so the comparison is in person-days.") if r25 else ""
    return lead + s2 + s3


# ----------------------------------------------------------------------------------------- H9
def _h9(rows):
    if not rows:
        return "No open grievances or litigation."
    to = rows[0].get("total_open")
    o3 = rows[0].get("total_over_3y")
    st = total(rows, "of_which_stayed")
    fut = total(rows, "future_dated_filings")
    g = _first(rows, "case_type", "grievance_internal")
    lit = [r for r in rows if r.get("case_type") != "grievance_internal"]
    lead = (f"{num(to)} grievances and service cases are open (pending or stayed): {num(total(lit, 'open_cases'))} litigations and "
            f"{num(_g(g, 'open_cases'))} internal grievances; {num(o3)} are more than 3 years old.")
    s2 = (" Litigation is old — " + ", ".join(f"{r['case_type']} {num(r['open_cases'])} (avg {f(r['avg_age_years'])} yrs, {num(r['aged_over_3y'])} over 3 yrs)"
                                             for r in lit) +
          f" — and {num(st)} cases are under court stay, while internal grievances average {f(_g(g, 'avg_age_years'))} years.")
    s3 = f" {num(fut)} cases carry filing dates after 19-Oct-2026 (data defect) and are excluded from the age figures."
    return lead + s2 + s3


def _h9_drill(rows):
    if not rows:
        return "No open cases."
    cat = total(rows, "cat_benches")
    hc = total(rows, "high_court")
    sc = total(rows, "supreme_court")
    ig = total(rows, "internal_grievance_cell")
    tot = total(rows, "open_cases")
    named = {r["case_category"]: r for r in rows}
    lead = (f"CAT benches carry {num(cat)} of the {num(tot)} open cases, High Courts {num(hc)}, the Supreme Court {num(sc)} and the "
            f"internal grievance cell {num(ig)}; the largest categories are {names(rows, 'case_category', 2)} "
            f"({num(rows[0]['open_cases'])} and {num(rows[1]['open_cases']) if len(rows) > 1 else 'n/a'}).")
    s2 = (" For the four named categories: " + "; ".join(
        f"{k.replace('_', ' ')} {num(named[k]['open_cases'])} (CAT {num(named[k]['cat_benches'])}, HC {num(named[k]['high_court'])})"
        for k in ("promotion_dispute", "transfer_challenge", "disciplinary_action", "pay_anomaly") if k in named) + ".")
    asked = {"promotion_dispute", "transfer_challenge", "disciplinary_action", "pay_anomaly"}
    extra = [r for r in rows[:2] if r["case_category"] not in asked]
    s3 = (f" {' and '.join(r['case_category'].replace('_', ' ') for r in extra).capitalize()} — not in the question's list — "
          f"{'is' if len(extra) == 1 else 'are'} actually the biggest driver{'s' if len(extra) > 1 else ''}.") if extra else ""
    return lead + s2 + s3


def _h9_why(rows):
    q = rows[0] if rows else {}
    lead = ("The corpus has no general employee-grievance redressal policy, so institutional delays cannot be traced to a written "
            "timeline breach except for transfers (partial data gap).")
    s2 = (f" The applicable provision is {q.get('doc_id')} {q.get('clause_ref')} ({q.get('heading')}): \"{q.get('quote_snippet')}\"") if q else ""
    s3 = (" Transfer challenges reaching CAT/High Courts (see H9 drill-down) therefore indicate representations not disposed "
          "within the 30-day TGRC window or stays not granted in writing.")
    return lead + s2 + s3


def _h9_cmp(rows):
    op = _first(rows, "status_group", "open")
    cl = _first(rows, "status_group", "closed")
    lead = ("Average disposal time cannot be measured: the grievance table has no disposal date, so the 60-day charter "
            "cannot be tested directly (data gap).")
    s2 = (f" What the data does show: {num(_g(op, 'older_than_60_days'))} of {num(_g(op, 'grievances'))} open internal grievances are "
          f"already older than {num(_g(op, 'charter_target_days'))} days (average {num(_g(op, 'avg_days_since_filing'))} days since filing), "
          f"i.e. they have breached the charter whatever their eventual outcome.")
    s3 = (f" {num(_g(cl, 'grievances'))} internal grievances are closed but their recorded age is time since filing, not time to disposal; "
          f"{num(_g(op, 'future_dated_filings'))} open grievances have future filing dates and are excluded.")
    return lead + s2 + s3


# ----------------------------------------------------------------------------------------- H10
def _h10(rows):
    if not rows:
        return "No executives due for rotation."
    r0 = rows[0]
    due, act = r0.get("company_due_for_rotation"), r0.get("company_active_executives")
    elig = r0.get("company_eligible_3_to_5y")
    cens, dcens = r0.get("company_stay_starts_2020_07_01"), r0.get("company_due_stay_starts_2020_07_01")
    ge5 = total(rows, "stay_ge_5y")
    ret = total(rows, "protected_retiring_3y")
    exm = total(rows, "protected_exemption_only")
    nh = total(rows, "due_never_served_cat_c")
    c = [r for r in rows if r.get("hard_station_cat") == "C"]
    cvac = total(c, "exec_vacancies_fy26")
    top = sorted(rows, key=lambda r: -(r.get("due_for_rotation") or 0))[:3]
    dl = _first(rows, "work_centre", "Delhi HQ")
    lead = (f"FY27 transfer proposal: {num(due)} of {num(act)} active executives are due for rotation — continuous stay of 5 years "
            f"or more ({num(ge5)}), less {num(ret)} within 3 years of superannuation and {num(exm)} with a valid exemption; a further "
            f"{num(elig)} are in the 3–5-year window and eligible but not yet due.")
    s2 = (f" Caveat: {num(cens)} executives' current stay starts exactly on 1-Jul-2020 (left-censored posting history), and they make "
          f"up {num(dcens)} of the {num(due)} due ({pct(_ratio(dcens, due))}), so the true overdue pool is likely much smaller and the list "
          f"must be validated against service books before issue.")
    s3 = (f" Category C stations need {num(cvac)} executives for FY26 vacancies; {num(nh)} due officers have never served Category C "
          f"(first call under JRTP 6.1). Largest release pools: " + ", ".join(f"{r['work_centre']} ({num(r['due_for_rotation'])})" for r in top) +
          (f"; Delhi HQ {num(_g(dl, 'due_for_rotation'))} due of {num(_g(dl, 'stay_ge_5y'))} with 5+ years "
           f"({num(_g(dl, 'protected_retiring_3y'))} retiring, {num(_g(dl, 'protected_exemption_only'))} exempt)." if dl else ".") +
          " Approval: Director (HR) for E1–E5, CMD for E6+.")
    return lead + s2 + s3


def _h10_drill(rows):
    if not rows:
        return "No Delhi/Dehradun executives meet the transfer criteria."
    n_ = rows[0].get("total_candidates") or len(rows)
    cz = rows[0].get("candidates_stay_starts_2020_07_01")
    wcs, disc = {}, {}
    for r in rows:
        wcs[r["current_work_centre"]] = wcs.get(r["current_work_centre"], 0) + 1
        disc[r["discipline"]] = disc.get(r["discipline"], 0) + 1
    td = sorted(disc.items(), key=lambda kv: -kv[1])[:3]
    lead = (f"{num(n_)} executives at New Delhi/Dehradun work centres meet the criteria for an Assam/Tripura posting: 5+ years "
            f"continuous stay, no valid exemption, not within 3 years of superannuation, technical discipline and no Category C service.")
    s2 = (" By location: " + ", ".join(f"{k} {num(v)}" for k, v in sorted(wcs.items(), key=lambda kv: -kv[1])) +
          "; by discipline: " + ", ".join(f"{k} {num(v)}" for k, v in td) + ".")
    s3 = (f" {num(cz)} of them have a stay recorded as starting 1-Jul-2020 (censored history) and need verification; the longest-serving "
          f"is {rows[0]['name']} ({rows[0]['emp_id']}, {rows[0]['grade_id']} {rows[0]['discipline']}, {f(rows[0]['station_years'])} years at "
          f"{rows[0]['current_work_centre']}).")
    return lead + s2 + s3


def _h10_cmp(rows):
    if not rows:
        return "No transfer data."
    due = total(rows, "due_for_rotation")
    cost = total(rows, "est_cost_if_all_due_moved_inr_cr")
    spend = total(rows, "fy26_spend_inr_cr")
    tr = total(rows, "fy26_transfers_in")
    vac = total(rows, "exec_vacancies_fy26")
    c = _first(rows, "station_category", "Category C")
    lead = (f"There is no approved transfer budget in the data; moving all {num(due)} due executives would cost about "
            f"{inr_cr(cost, 2)}, roughly {f(cost / spend if spend else None)}x the FY26 transfer spend of {inr_cr(spend, 2)} "
            f"({num(tr)} transfers).")
    unit = _g(c, "avg_cost_per_transfer_inr_lakh")
    cvac = _g(c, "exec_vacancies_fy26")
    ccost = (cvac * unit / 100.0) if cvac is not None and unit is not None else None
    s2 = (f" Deficit clearance needs far fewer moves: executive vacancies total {num(vac)}, of which {num(cvac)} are at Category C "
          f"stations — filling those at ₹{f(unit, 2)} lakh per transfer would cost about {inr_cr(ccost, 2)}, "
          f"{'within' if ccost is not None and ccost <= spend else 'above'} the FY26 run-rate.")
    s3 = (f" A further {num(total(rows, 'eligible_3_to_5y'))} executives in the 3–5-year window are eligible but not due. Recommendation: "
          f"cap the FY27 list at the deficit-driven moves plus verified longest overstayers, using FY26 spend as the budget proxy until a BE figure is provided.")
    return lead + s2 + s3


NARRATIVES = {
    "H1": _h1, "H1__drill_down": _h1_drill, "H1__why": _h1_why, "H1__compare_or_so_what": _h1_cmp,
    "H2": _h2, "H2__drill_down": _h2_drill, "H2__why": _h2_why, "H2__compare_or_so_what": _h2_cmp,
    "H3": _h3, "H3__drill_down": _h3_drill, "H3__why": _h3_why, "H3__compare_or_so_what": _h3_cmp,
    "H4": _h4, "H4__drill_down": _h4_drill, "H4__why": _h4_why, "H4__compare_or_so_what": _h4_cmp,
    "H5": _h5, "H5__drill_down": _h5_drill, "H5__why": _h5_why, "H5__compare_or_so_what": _h5_cmp,
    "H6": _h6, "H6__drill_down": _h6_drill, "H6__why": _h6_why, "H6__compare_or_so_what": _h6_cmp,
    "H7": _h7, "H7__drill_down": _h7_drill, "H7__why": _h7_why, "H7__compare_or_so_what": _h7_cmp,
    "H8": _h8, "H8__drill_down": _h8_drill, "H8__why": _h8_why, "H8__compare_or_so_what": _h8_cmp,
    "H9": _h9, "H9__drill_down": _h9_drill, "H9__why": _h9_why, "H9__compare_or_so_what": _h9_cmp,
    "H10": _h10, "H10__drill_down": _h10_drill, "H10__compare_or_so_what": _h10_cmp,
}
