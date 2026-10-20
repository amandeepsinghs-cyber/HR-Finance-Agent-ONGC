"""Narratives for C-series entries (rendered from result rows; no typed numbers)."""

from semantic_audit.common import f, inr_cr, names, num, pct, signed_pct, total  # noqa: F401


def _c11(rows):
    hits = [r for r in rows if r.get("added_hc_and_lost_production")]
    decl = [r for r in rows if r.get("boe_growth_pct") is not None and r["boe_growth_pct"] < 0]
    grew_hc = [r for r in rows if (r.get("hc_change") or 0) > 0]
    hc21, hc26 = total(rows, "hc_mar21"), total(rows, "hc_mar26")
    if hits:
        lead = (f"{len(hits)} asset(s) added headcount between 31-Mar-2021 and 31-Mar-2026 while FY26 production "
                f"fell below FY21: {names(hits, 'short_name', 5)}.")
    else:
        lead = ("No asset both added headcount and lost production over the five years: between 31-Mar-2021 and "
                "31-Mar-2026 every asset whose production fell also reduced its headcount.")
    worst = decl[0] if decl else None
    s2 = (f"Across the {len(rows)} producing assets, period-end headcount fell from {num(hc21)} to {num(hc26)} "
          f"({signed_pct((hc26 - hc21) * 100.0 / hc21 if hc21 else None)}), while {len(decl)} assets produced less in FY26 than FY21; "
          f"the steepest BOE decline was {worst['short_name']} ({signed_pct(worst['boe_growth_pct'])}, "
          f"headcount {signed_pct(worst['hc_growth_pct'])}).") if worst else ""
    s3 = ""
    if grew_hc:
        g = grew_hc[0]
        s3 = (f" The only headcount gain was {g['short_name']} (+{num(g['hc_change'])}), whose output rose from "
              f"{f(g['mmboe_fy21'], 1)} to {f(g['mmboe_fy26'], 1)} MMboe as new production came on stream.")
    return f"{lead} {s2}{s3} Production is compared in BOE (oil and gas also shown separately); headcount uses March period-end snapshots."


# ----------------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------------
def _g(r, k, default=None):
    v = (r or {}).get(k)
    return default if v is None else v


def _join(items):
    items = [str(i) for i in items]
    if not items:
        return "none"
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _first(rows, pred):
    for r in rows:
        if pred(r):
            return r
    return None


# ----------------------------------------------------------------------------------------------
# C1 family
# ----------------------------------------------------------------------------------------------
def _c1_drill(rows):
    if not rows:
        return "No E5–E7 officer in Delhi HQ has completed five years of continuous stay."
    top = rows[0]
    tot = total(rows, "e5_e7_past_5yr")
    hi = max(rows, key=lambda r: _g(r, "pct_of_discipline_past_5yr", 0))
    top4 = sum(float(_g(r, "e5_e7_past_5yr", 0)) for r in rows[:4])
    return (f"{top['discipline_name']} has the largest block of long-staying senior officers in Delhi HQ: "
            f"{num(top['e5_e7_past_5yr'])} E5–E7 officers past five years ({pct(top['pct_of_discipline_past_5yr'])} of its Delhi E5–E7 strength), "
            f"followed by {names(rows[1:4], 'discipline_name', 3)}. "
            f"These top four disciplines hold {num(top4)} of the {num(tot)} E5–E7 officers past five years "
            f"({pct(top4 * 100.0 / tot if tot else None)}), so senior rotation in Delhi should start with them. "
            f"By concentration, {hi['discipline_name']} is the most entrenched ({pct(hi['pct_of_discipline_past_5yr'])} of its "
            f"{num(hi['e5_e7_in_delhi'])} Delhi E5–E7 officers past five years).")


def _c1_why(rows):
    tot = total(rows, "officer_count")
    none = _first(rows, lambda r: r.get("exemption_tag") == "None recorded")
    tagged = [r for r in rows if r.get("exemption_tag") != "None recorded"]
    n_none = _g(none, "officer_count", 0)
    lead = "Almost none" if tot and n_none / tot >= 0.9 else "Most"
    s1 = (f"{lead} of the {num(tot)} executives past five years in Delhi HQ {'has' if lead == 'Almost none' else 'lack'} a recorded justification: "
          f"{num(n_none)} ({pct(_g(none, 'pct_of_delhi_5yr_plus'))}) carry no exemption tag, reason code or approver in SAP.")
    if tagged:
        t = tagged[0]
        s2 = (f" The only recorded exemption is {t['exemption_tag']} ({t['exemption_reason_code']}, approved by "
              f"{t['exemption_approved_by']}) for {num(t['officer_count'])} officers, all valid as of 19-Oct-2026 "
              f"({num(t['valid_as_of_2026_10_19'])}).") if t.get("valid_as_of_2026_10_19") == t.get("officer_count") else (
              f" The only recorded exemption is {t['exemption_tag']} ({t['exemption_reason_code']}, approved by "
              f"{t['exemption_approved_by']}) for {num(t['officer_count'])} officers.")
    else:
        s2 = ""
    s3 = (f" A further {num(_g(none, 'retiring_within_3yr', 0))} untagged officers retire within three years and would "
          f"qualify for the JRTP Clause 7 pre-retirement exemption, so the extended stays are largely undocumented "
          f"rather than approved exceptions.")
    return s1 + s2 + s3


def _c1_cmp(rows):
    by = {r["wc_id"]: r for r in rows}
    d, t, m, a = by.get("WC-DEL"), by.get("WC-DDN"), by.get("WC-ROM"), by.get("ALL")
    dp, tp, mp_, ap = (_g(x, "pct_stay_ge_5yr", 0) for x in (d, t, m, a))
    lower = dp < tp and dp < mp_
    s1 = (f"Delhi HQ's five-year retention rate is {'lower than' if lower else 'comparable to or higher than'} the other corporate offices: "
          f"{pct(dp)} of its {num(_g(d, 'total_current_executives'))} executives have stayed five years or more, versus "
          f"{pct(tp)} at Dehradun Tel Bhavan and {pct(mp_)} at Regional Office Mumbai.")
    s2 = (f" The company-wide rate is {pct(ap)} (average continuous stay {f(_g(a, 'avg_continuous_stay_years'))} years vs "
          f"{f(_g(d, 'avg_continuous_stay_years'))} in Delhi), so Delhi's issue is the size of its long-stay pool "
          f"({num(_g(d, 'executives_ge_5yr'))} executives) rather than an unusually high rate." if dp <= ap else
          f" The company-wide rate is {pct(ap)}, so Delhi is above the corporate norm.")
    s3 = (f" Tel Bhavan has an even larger long-stay block ({num(_g(t, 'executives_ge_5yr'))} executives) and should be "
          f"included in any HQ rotation drive." if _g(t, "executives_ge_5yr", 0) > _g(d, "executives_ge_5yr", 0) else "")
    return s1 + s2 + s3


# ----------------------------------------------------------------------------------------------
# C2 family
# ----------------------------------------------------------------------------------------------
def _c2(rows):
    pool = [r for r in rows if r.get("section") == "overdue_pool"]
    recv = [r for r in rows if r.get("section") == "receiving_station"]
    tot = _g(rows[0], "company_overdue_total", 0) if rows else 0
    vac = total(recv, "exec_vacancy")
    s1 = (f"{num(tot)} executives are overdue for rotation under JRTP Clause 3.2 (five or more years of continuous stay at "
          f"their current work centre, excluding officers within three years of superannuation or holding a valid exemption); the largest pools sit at "
          f"{names(pool, 'short_name', 3)} ({', '.join(num(r['overdue_executives']) for r in pool[:3])}).")
    s2 = (f" Only {len(recv)} hard or remote stations are short of executives against FY26 sanctioned posts, with a combined gap of "
          f"{num(vac)}: {', '.join(f'{r['short_name']} {num(r['exec_vacancy'])}' for r in recv[:5])}.")
    s3 = (f" The overdue pool is roughly {f(tot / vac if vac else None, 0)} times the receiving gap, so the binding constraint is "
          f"placement capacity, not a shortage of movable officers; the offshore assets themselves hold large overdue pools, so "
          f"rotation has to be a swap rather than a one-way flow.") if vac else ""
    return s1 + s2 + s3


def _c2_drill(rows):
    by = {}
    for r in rows:
        by.setdefault(r["short_name"], []).append(r)
    tri = by.get("Tripura Asset", [])
    asm = by.get("Assam Asset", [])
    tri_def = total(tri, "exec_deficit")
    tri_san = total(tri, "exec_sanctioned")
    asm_def = total(asm, "exec_deficit")
    short = [r for r in tri if (r.get("exec_deficit") or 0) > 0]
    s1 = (f"Tripura Asset carries the whole deficit: {num(tri_def)} executive posts vacant out of {num(tri_san)} sanctioned "
          f"({pct(tri_def * 100.0 / tri_san if tri_san else None)}), led by {', '.join(f'{r['discipline_name']} {num(r['exec_deficit'])}' for r in short[:3])}."
          if tri_def and not asm_def else
          f"Tripura Asset is short {num(tri_def)} executive posts and Assam Asset {num(asm_def)} against FY26 sanctioned strength.")
    s2 = (f" Assam Asset is fully staffed against its {num(total(asm, 'exec_sanctioned'))} sanctioned executive posts in every discipline, "
          f"so NE recruitment or rotation should be targeted at Agartala, not Nazira." if not asm_def else "")
    hi = max(short, key=lambda r: r.get("deficit_pct") or 0) if short else None
    s3 = (f" The steepest proportional gap is {hi['discipline_name']} at Tripura ({pct(hi['deficit_pct'])} of sanctioned posts vacant)."
          if hi else "")
    return s1 + s2 + s3


def _c2_why(rows):
    inn, out = total(rows, "executives_posted_into_ne"), total(rows, "executives_posted_out_of_ne")
    neg = [r for r in rows if (r.get("net_flow_into_ne") or 0) < 0]
    last = rows[-1] if rows else {}
    s1 = (f"Every recent transfer cycle has moved more executives out of the North-East than into it: across FY22–FY26, "
          f"{num(inn)} executives were posted into NE work centres and {num(out)} out, a cumulative net loss of "
          f"{num(abs(_g(last, 'cumulative_net_flow', 0)))}." if len(neg) == len(rows) and rows else
          f"Across FY22–FY26, {num(inn)} executives were posted into NE work centres and {num(out)} out "
          f"(net {num(_g(last, 'cumulative_net_flow', 0))}); {len(neg)} of {len(rows)} cycles were net-negative.")
    s2 = (f" Outflows (officers completing NE tenures) consistently outrun replacement postings, so the gap is a structural "
          f"replacement shortfall in each Annual General Transfer rather than a one-off event.")
    s3 = (f" Against FY26 sanctions the NE executive gap is {num(_g(last, 'ne_exec_vacancy_fy26'))} of "
          f"{num(_g(last, 'ne_exec_sanctioned_fy26'))} posts; only FY26 sanctioned strength is recorded, so earlier-year "
          f"shortfalls cannot be measured directly.")
    return s1 + s2 + s3


def _c2_cmp(rows):
    tot = total(rows, "overdue_executives")
    never = [r for r in rows if r.get("never_completed_mandatory_tenure")]
    n = total(never, "overdue_executives")
    zero = _first(rows, lambda r: str(r.get("hard_tenure_status", "")).startswith("Never posted"))
    short = _first(rows, lambda r: str(r.get("hard_tenure_status", "")).startswith("Served"))
    return (f"{num(n)} of the {num(tot)} overdue executives ({pct(n * 100.0 / tot if tot else None)}) have never completed a "
            f"mandatory 36-month tenure in a Category-C or offshore location. "
            f"Of these, {num(_g(short, 'overdue_executives', 0))} served such a station for less than three years and "
            f"{num(_g(zero, 'overdue_executives', 0))} have never been posted to one at all. "
            f"They are the natural first candidates for the hard-station vacancies, since JRTP Clause 6.1 bars E4→E5 "
            f"promotion without that tenure.")


# ----------------------------------------------------------------------------------------------
# C3 family
# ----------------------------------------------------------------------------------------------
def _c3(rows):
    up = [r for r in rows if not r.get("no_increase")]
    flat = [r for r in rows if r.get("no_increase")]
    worst = sorted(flat, key=lambda r: r.get("hc_change") or 0)[:3]
    h21, h26 = total(rows, "hc_mar21"), total(rows, "hc_mar26")
    s1 = (f"{len(flat)} of {len(rows)} work centres saw no headcount increase between 31-Mar-2021 and 31-Mar-2026; only "
          f"{_join(f'{r['short_name']} (+{num(r['hc_change'])}, {signed_pct(r['growth_pct'])})' for r in up)} grew.")
    s2 = (f" Company headcount fell from {num(h21)} to {num(h26)} ({signed_pct((h26 - h21) * 100.0 / h21 if h21 else None)}), "
          f"with the largest reductions at {', '.join(f'{r['short_name']} ({num(r['hc_change'])})' for r in worst)}.")
    s3 = (" Growth at corporate HQ while every field asset except the new deepwater asset shrank is the pattern to challenge."
          if any(r.get("wc_type") == "office" for r in up) else "")
    return s1 + s2 + s3 + " Headcount uses March period-end snapshots, not sums of monthly snapshots."


def _c3_drill(rows):
    ex = [r for r in rows if r.get("cadre") == "executive"]
    ne = [r for r in rows if r.get("cadre") == "non_executive"]
    grew = [r for r in ex if (r.get("change_5yr") or 0) > 0]
    fell = sorted([r for r in ex if (r.get("change_5yr") or 0) < 0], key=lambda r: r.get("change_pct") or 0)
    s1 = (f"The shift is almost entirely executive: executive headcount fell at "
          f"{', '.join(f'{r['short_name']} ({num(r['hc_mar21'])}→{num(r['hc_mar26'])}, {signed_pct(r['change_pct'])})' for r in fell)}"
          + (f", while {', '.join(f'{r['short_name']} rose ({num(r['hc_mar21'])}→{num(r['hc_mar26'])}, {signed_pct(r['change_pct'])})' for r in grew)}." if grew else "."))
    ne_rng = [r.get("change_pct") for r in ne if r.get("change_pct") is not None]
    s2 = (f" Non-executive strength was broadly stable at all four assets (changes between {signed_pct(min(ne_rng))} and "
          f"{signed_pct(max(ne_rng))}), so the reduction came through officer attrition and redeployment rather than field-crew cuts."
          if ne_rng else "")
    return s1 + s2 + " Figures are March period-end snapshots for each year 2021–2026."


def _c3_why(rows):
    g = _first(rows, lambda r: r.get("field_maturity") == "growth")
    m = [r for r in rows if r.get("field_maturity") != "growth"]
    s1 = (f"The headcount shift tracks the production shift: {g['short_name']} (KG-DWN-98/2, a growth field) went from "
          f"{f(g['mmboe_fy21'], 1)} to {f(g['mmboe_fy26'], 1)} MMboe ({f(g['oil_mmt_fy26'], 3)} MMT oil and {f(g['gas_bcm_fy26'], 3)} BCM gas in FY26) "
          f"and is the only one of the four to add staff (+{num(g['hc_change'])}).") if g else ""
    s2 = (f" The mature assets lost output and people together: "
          f"{', '.join(f'{r['short_name']} {signed_pct(r['boe_growth_pct'])} BOE / {num(r['hc_change'])} heads' for r in m)}.")
    s3 = " Natural decline in mature onshore fields, not a reallocation decision alone, explains most of the reduction; the deepwater ramp-up absorbed only a small net addition."
    return (s1 + s2 + s3).strip()


def _c3_cmp(rows):
    assets = [r for r in rows if r.get("short_name") != "All producing assets"]
    tot = _first(rows, lambda r: r.get("short_name") == "All producing assets")
    faster = [r for r in assets if r.get("boe_growth_pct") is not None and r.get("hc_growth_pct") is not None
              and r["hc_growth_pct"] < r["boe_growth_pct"]]
    new = [r for r in assets if r.get("boe_growth_pct") is None and (r.get("mmboe_fy26") or 0) > 0]
    s1 = (f"Headcount has fallen faster than production almost everywhere: across the producing assets headcount changed "
          f"{signed_pct(_g(tot, 'hc_growth_pct'))} (Mar-21 to Mar-26) against {signed_pct(_g(tot, 'oil_condensate_growth_pct'))} for oil and condensate, "
          f"{signed_pct(_g(tot, 'gas_growth_pct'))} for gas and {signed_pct(_g(tot, 'boe_growth_pct'))} in BOE (FY21 to FY26).")
    gap = sorted(faster, key=lambda r: r["hc_growth_pct"] - r["boe_growth_pct"])[:2]
    s2 = (f" {len(faster)} of the {len(assets) - len(new)} assets with FY21 output cut headcount by more than their BOE decline "
          f"(widest gaps: {', '.join(f'{r['short_name']} {signed_pct(r['hc_growth_pct'])} heads vs {signed_pct(r['boe_growth_pct'])} BOE' for r in gap)}), "
          f"so output per head has improved.") if faster else ""
    s3 = (f" {new[0]['short_name']} had no FY21 production (output {f(new[0]['mmboe_fy26'], 1)} MMboe in FY26) and is the only asset "
          f"where both headcount and output grew.") if new else ""
    return s1 + s2 + s3


# ----------------------------------------------------------------------------------------------
# C4 family
# ----------------------------------------------------------------------------------------------
def _c4(rows):
    gs = [r for r in rows if r.get("section") == "grade_summary"]
    roles = [r for r in rows if r.get("section") == "role_no_ready_successor"]
    ret = total(gs, "retiring_next_3yr")
    act = total(gs, "active_officers")
    inplan = total(gs, "retiring_in_plan_position")
    noplan = total(gs, "retiring_not_in_succession_plan")
    by = {r["grade_id"]: r for r in gs}
    s1 = (f"{num(ret)} of {num(act)} active E7+ officers (GM and above, including board level) retire in the next three years "
          f"(19-Oct-2026 to 18-Oct-2029): {', '.join(f'{g} {num(by[g]['retiring_next_3yr'])}' for g in ('E7', 'E8', 'E9', 'DIR', 'CMD') if g in by)}.")
    s2 = (f" {num(len(roles))} succession-plan roles held by these retirees have no 'Ready Now' successor: "
          f"{'; '.join(f'{r['role_title']}, {r['work_centre']} (retires {r['retirement_date']})' for r in roles)}.") if roles else \
         " Every succession-plan role held by these retirees has a 'Ready Now' successor."
    s3 = (f" The larger exposure is coverage: only {num(inplan)} of the {num(ret)} retirees hold a position in the succession plan, "
          f"leaving {num(noplan)} with no mapped successor at all.")
    return s1 + s2 + s3


def _c4_drill(rows):
    tot = total(rows, "retiring_12m")
    sen = total(rows, "retiring_12m_e5_plus")
    top = rows[:3]
    plan = [r for r in rows if r.get("plan_roles_retiring")]
    s1 = (f"{num(tot)} executives at Mumbai High, Neelam & Heera and Drilling Services retire in the next 12 months, "
          f"{num(sen)} of them at E5 or above; the senior gaps concentrate in "
          f"{', '.join(f'{r['work_centre']} {r['discipline_name']} ({num(r['retiring_12m_e5_plus'])} E5+)' for r in top)}.")
    s2 = (f" Only {len(plan)} of these is a mapped succession-plan role ({'; '.join(f'{r['plan_roles_retiring']} at {r['work_centre']}' for r in plan)}), "
          f"so most offshore production and drilling retirements will not be covered by the formal succession board.") if plan else \
         " None of these retirements is a mapped succession-plan role."
    s3 = (f" The first exits fall on {min(str(r['first_retirement']) for r in rows)}, so replacement postings belong in the current transfer cycle."
          if rows else "")
    return s1 + s2 + s3


def _c4_why(rows):
    tot = total(rows, "positions_no_ready_now")
    reasons = {}
    for r in rows:
        reasons[r["readiness_gap_reason"]] = reasons.get(r["readiness_gap_reason"], 0) + (r.get("positions_no_ready_now") or 0)
    main_reason, main_n = max(reasons.items(), key=lambda kv: kv[1]) if reasons else ("n/a", 0)
    t1 = _first(rows, lambda r: r.get("criticality_tier") == "Tier_1_Critical")
    ne = total(rows, "successor_1_lacks_ne_hard_station")
    s1 = (f"All {num(tot)} positions without a 'Ready Now' successor cite the same gap - {main_reason.replace('_', ' ')}"
          if len(reasons) == 1 else
          f"The dominant reason among the {num(tot)} positions without a 'Ready Now' successor is {main_reason.replace('_', ' ')} ({num(main_n)})")
    s1 += (f"; {num(_g(t1, 'positions_no_ready_now', 0))} are Tier-1 critical roles ({_g(t1, 'roles', '')}).")
    s2 = (f" Successors are being groomed in onshore or corporate roles without offshore command exposure, and for {num(ne)} positions "
          f"the first-choice successor also lacks NE/hard-station tenure, which JRTP Clause 6 makes a promotion prerequisite.")
    s3 = (f" {num(total(rows, 'incumbent_retires_3yr'))} of these incumbents retire within three years, so targeted offshore "
          f"postings for successors are the fastest fix.")
    return s1 + s2 + s3


def _c4_cmp(rows):
    allr = _first(rows, lambda r: r.get("cadre_family") == "All technical E6")
    eng = _first(rows, lambda r: str(r.get("cadre_family", "")).startswith("Engineering"))
    geo = _first(rows, lambda r: str(r.get("cadre_family", "")).startswith("Geoscience"))
    return (f"{pct(_g(allr, 'pct_meet_benchmark'))} of active technical E6 officers ({num(_g(allr, 'meet_dpc_benchmark'))} of "
            f"{num(_g(allr, 'e6_with_fy26_apar'))} with an FY26 APAR) meet the DPC benchmark score of {f(_g(allr, 'benchmark_score'))} "
            f"for promotion to GM, but only {pct(_g(allr, 'pct_outstanding'))} ({num(_g(allr, 'outstanding_accelerated'))}) are rated "
            f"Outstanding, the band that supports accelerated promotion. "
            f"Chief Engineers meet the benchmark {'more' if _g(eng, 'pct_meet_benchmark', 0) > _g(geo, 'pct_meet_benchmark', 0) else 'less'} often ({pct(_g(eng, 'pct_meet_benchmark'))}) than geoscientists "
            f"({pct(_g(geo, 'pct_meet_benchmark'))}), and their Outstanding share is "
            f"{pct(_g(eng, 'pct_outstanding'))} vs {pct(_g(geo, 'pct_outstanding'))}. "
            f"The accelerated pipeline is therefore about {num(_g(allr, 'outstanding_accelerated'))} officers, enough to cover the E7 "
            f"retirements in C4 only if they are also given offshore exposure.")


# ----------------------------------------------------------------------------------------------
# C5 family
# ----------------------------------------------------------------------------------------------
def _c5(rows):
    top = rows[0] if rows else {}
    hi = max(rows, key=lambda r: r.get("retirement_pct") or 0) if rows else {}
    tot = total(rows, "retiring_by_fy30")
    act = total(rows, "active_executives")
    geo = [r for r in rows if r.get("discipline_id") in ("DISC-GEO", "DISC-GPS", "DISC-GPW")]
    s1 = (f"Production faces the largest retirement gap by FY30 in absolute terms ({num(_g(top, 'retiring_by_fy30'))} of "
          f"{num(_g(top, 'active_executives'))} executives, {pct(_g(top, 'retirement_pct'))}), but {hi.get('discipline_name')} is hit hardest "
          f"proportionally, losing {pct(hi.get('retirement_pct'))} ({num(hi.get('retiring_by_fy30'))}) of its officers by 31-Mar-2030."
          if top.get("discipline_id") == "DISC-PRD" else
          f"{top.get('discipline_name')} faces the largest retirement gap by FY30 ({num(_g(top, 'retiring_by_fy30'))} executives, {pct(_g(top, 'retirement_pct'))}).")
    s2 = (f" Across the core technical disciplines {num(tot)} of {num(act)} executives ({pct(tot * 100.0 / act if act else None)}) retire by FY30; "
          f"geoscience (Geology plus Geophysics) loses {num(total(geo, 'retiring_by_fy30'))} and Reservoir "
          f"{num(_g(_first(rows, lambda r: r.get('discipline_id') == 'DISC-RES'), 'retiring_by_fy30'))}.")
    s3 = (f" In every discipline retirements exceed the entire E0–E2 junior pipeline (e.g. {top.get('discipline_name')} "
          f"{num(_g(top, 'retiring_by_fy30'))} retiring vs {num(_g(top, 'e0_e2_pipeline'))} juniors), so the gap cannot be closed by promotion alone."
          if all((r.get("retiring_by_fy30") or 0) > (r.get("e0_e2_pipeline") or 0) for r in rows) else
          f" {top.get('discipline_name')} has {num(_g(top, 'e0_e2_pipeline'))} E0–E2 juniors against {num(_g(top, 'retiring_by_fy30'))} retirements.")
    return s1 + s2 + s3


def _c5_drill(rows):
    last = {}
    for r in rows:
        last[r["discipline"]] = r
    tot = sum(float(r.get("cumulative_to_date") or 0) for r in last.values())
    peak = max(rows, key=lambda r: r.get("superannuations") or 0) if rows else {}
    return (f"{num(tot)} executives in Geology, Geophysics and Reservoir superannuate between now and the end of FY30: "
            f"{_join(f'{d} {num(r['cumulative_to_date'])}' for d, r in last.items())}. "
            f"Exits accelerate after the current year - the single biggest year is {peak.get('retirement_fy')} for "
            f"{peak.get('discipline')} ({num(peak.get('superannuations'))}) - so the loss is back-loaded into FY28–FY30. "
            f"FY27 counts only the remainder of the year from 19-Oct-2026.")


def _c5_why(rows):
    base = [r for r in rows if r.get("period") == "FY14-FY19"]
    win = [r for r in rows if r.get("period") == "FY20-FY25"]
    b, w = total(base, "technical_executive_intake"), total(win, "technical_executive_intake")
    wa = total(win, "still_active")
    s1 = (f"Core technical executive intake collapsed in FY20–FY25: {num(w)} officers joined Drilling, Geoscience, Reservoir and "
          f"Production over six years (about {num(w / len(win) if win else None)} a year) versus {num(b)} in FY14–FY19 "
          f"(about {num(b / len(base) if base else None)} a year).")
    s2 = ((f" None of the FY20–FY25 joiners is still in service" if not wa else f" Only {num(wa)} of the FY20–FY25 joiners are still in service")
          + ", so the cohort that should be reaching E3–E4 by FY30 is effectively missing, exactly when the C5 retirements peak.")
    s3 = (" With no mid-career bench, each senior retirement must be filled by accelerated promotion of a thin E3–E5 layer "
          "or lateral hiring, which is the seniority vacuum the question describes.")
    return s1 + s2 + s3


def _c5_cmp(rows):
    prj = [r for r in rows if r.get("host_work_centre") != "All"]
    co = _first(rows, lambda r: r.get("host_work_centre") == "All")
    hi = max(prj, key=lambda r: r.get("pct_retiring") or 0) if prj else {}
    big = prj[0] if prj else {}
    s1 = "No ongoing deepwater or HP-HT project was found in the project register."
    s1 = (f"The {len(prj)} ongoing deepwater/HP-HT projects depend on host teams that will lose between "
          f"{pct(min(r.get('pct_retiring') or 0 for r in prj))} and {pct(max(r.get('pct_retiring') or 0 for r in prj))} of their "
          f"drilling and subsurface specialists by FY30, against {pct(_g(co, 'pct_retiring'))} company-wide "
          f"({num(_g(co, 'host_specialists_retiring_by_fy30'))} of {num(_g(co, 'host_specialists_active'))}).") if prj else s1
    s2 = (f" The largest, {big.get('project_or_scope')} ({inr_cr(big.get('sanctioned_cost_inr_cr'))}), relies on "
          f"{num(big.get('host_specialists_active'))} specialists at {big.get('host_work_centre')}, of whom "
          f"{num(big.get('host_specialists_retiring_by_fy30'))} retire by FY30; the most exposed is {hi.get('project_or_scope')} "
          f"({pct(hi.get('pct_retiring'))} of {num(hi.get('host_specialists_active'))}).") if prj else ""
    s3 = " There is no project staffing plan in the data, so host work-centre strength is used as the proxy for project capability."
    return s1 + s2 + s3


# ----------------------------------------------------------------------------------------------
# C6 family
# ----------------------------------------------------------------------------------------------
def _c6(rows):
    loss = [r for r in rows if r.get("is_loss_making")]
    top = rows[:3]
    tot = total(rows, "pbt_inr_cr")
    top3 = sum(float(r.get("pbt_inr_cr") or 0) for r in top)
    s1 = (f"In FY26 the most profitable fields were {_join(f'{r['field_name']} ({inr_cr(r['pbt_inr_cr'])} PBT)' for r in top)}, "
          f"and only {len(loss)} of {len(rows)} fields made a loss: "
          f"{_join(f'{r['field_name']}, {r['asset']} ({inr_cr(r['pbt_inr_cr'], 2)})' for r in loss)}." if loss else
          f"In FY26 the most profitable fields were {_join(f'{r['field_name']} ({inr_cr(r['pbt_inr_cr'])} PBT)' for r in top)}, and no field made a loss.")
    s2 = (f" The top three generate {pct(top3 * 100.0 / tot if tot else None)} of the {inr_cr(tot)} field-level PBT, "
          f"so profitability is concentrated in a handful of large fields.") if tot else ""
    near = [r for r in rows if not r.get("is_loss_making") and (r.get("pbt_margin_pct") or 0) < 5]
    s3 = (f" {_join(f'{r['field_name']} ({pct(r['pbt_margin_pct'])} margin)' for r in near)} are barely above breakeven and are the "
          f"next loss risks.") if near else ""
    return s1 + s2 + s3


def _c6_drill(rows):
    neg = [r for r in rows if (r.get("net_margin_pct") or 0) < 0]
    lo = rows[:3]
    hi = rows[-1] if rows else {}
    s1 = (f"Margins in the mature onshore fields of Assam and Cauvery span from {pct(_g(rows[0], 'net_margin_pct'))} at "
          f"{_g(rows[0], 'field_name')} to {pct(hi.get('net_margin_pct'))} at {hi.get('field_name')} in FY26.") if rows else "No fields matched."
    lo_assets = sorted({r.get("asset") for r in lo})
    s2 = (f" The weak end is {_join(lo_assets)}: {_join(f'{r['field_name']} (EBITDA {inr_cr(r['ebitda_inr_cr'], 1)}, net margin {pct(r['net_margin_pct'])})' for r in lo)}"
          f"{'; ' + neg[0]['field_name'] + ' is the only one with a net loss' if len(neg) == 1 else ''}.")
    others = [r for r in rows if r.get("asset") not in lo_assets]
    s3 = (f" The remaining {len(others)} fields earn net margins of {pct(min(r['net_margin_pct'] for r in others))}–"
          f"{pct(max(r['net_margin_pct'] for r in others))}, so the problem is specific to {_join(lo_assets)}."
          if others else "")
    return s1 + s2 + s3


def _c6_why(rows):
    bench = _first(rows, lambda r: str(r.get("field_name", "")).startswith("All FY26"))
    worst = [r for r in rows if r is not bench]
    w = worst[0] if worst else {}
    b_mp = _g(bench, "manpower_inr_per_boe", 0)
    mult = (w.get("manpower_inr_per_boe") or 0) / b_mp if b_mp else None
    comps = {k: w.get(k) or 0 for k in ("manpower_inr_per_boe", "power_fuel_inr_per_boe", "workover_inr_per_boe",
                                          "water_handling_inr_per_boe", "chemicals_inr_per_boe", "contractor_inr_per_boe")}
    lead = "Manpower cost, not water handling, is the primary driver" if max(comps, key=comps.get) == "manpower_inr_per_boe" else "Manpower is a major driver"
    s1 = (f"{lead}: at {w.get('field_name')} manpower costs "
          f"₹{num(w.get('manpower_inr_per_boe'))} per BOE against a field average of ₹{num(b_mp)} "
          f"(about {f(mult, 0)}x), out of total opex of ₹{num(w.get('opex_inr_per_boe'))}/BOE vs ₹{num(_g(bench, 'opex_inr_per_boe'))}.")
    s2 = (f" High water cut ({pct(w.get('water_cut_pct'))} vs {pct(_g(bench, 'water_cut_pct'))}) sets up the problem by shrinking oil "
          f"output, which inflates every fixed cost per barrel - power and fuel ₹{num(w.get('power_fuel_inr_per_boe'))}/BOE vs "
          f"₹{num(_g(bench, 'power_fuel_inr_per_boe'))} and contract labour ₹{num(w.get('contractor_inr_per_boe'))} vs ₹{num(_g(bench, 'contractor_inr_per_boe'))}.")
    wo_ratio = (w.get("workover_inr_per_boe") or 0) / _g(bench, "workover_inr_per_boe", 1)
    s3 = (f" Workover spend is {'close to' if wo_ratio <= 1.3 else 'well above'} the norm (₹{num(w.get('workover_inr_per_boe'))} vs ₹{num(_g(bench, 'workover_inr_per_boe'))}/BOE); "
          f"the recorded root cause is {str(w.get('root_cause_loss_code')).replace('_', ' ')}. FY26 has one loss-making field, so the "
          f"comparison covers the five lowest-PBT fields.")
    return s1 + s2 + s3


def _c6_cmp(rows):
    by = {r["asset"]: r for r in rows}
    mh, bs = by.get("Mumbai High", {}), by.get("Bassein & Satellite", {})
    an, me = by.get("Ankleshwar Asset", {}), by.get("Mehsana Asset", {})
    top = rows[0] if rows else {}
    onshore_lead = top.get("onshore_offshore") == "onshore"
    s1 = (f"{'Onshore' if onshore_lead else 'Offshore'} leads on margin: {top.get('asset')} has the highest EBITDA margin "
          f"({pct(top.get('ebitda_margin_pct'))}), ahead of Bassein ({pct(bs.get('ebitda_margin_pct'))}), Mumbai High "
          f"({pct(mh.get('ebitda_margin_pct'))}) and Mehsana ({pct(me.get('ebitda_margin_pct'))}) in FY26.")
    on_pbt = min(_g(an, "pbt_margin_pct", 0), _g(me, "pbt_margin_pct", 0)) > max(_g(mh, "pbt_margin_pct", 0), _g(bs, "pbt_margin_pct", 0))
    s2 = (f" On PBT margin {'the onshore pair leads clearly' if on_pbt else 'the picture is mixed'} - Ankleshwar {pct(an.get('pbt_margin_pct'))} and "
          f"Mehsana {pct(me.get('pbt_margin_pct'))} vs Mumbai High {pct(mh.get('pbt_margin_pct'))} and Bassein {pct(bs.get('pbt_margin_pct'))}"
          f"{' - offshore depreciation (DD&A) absorbs more of the EBITDA' if on_pbt else ''}.")
    s3 = (f" Offshore still dominates absolute profit (Mumbai High {inr_cr(mh.get('pbt_inr_cr'))} PBT vs Mehsana {inr_cr(me.get('pbt_inr_cr'))}), "
          f"and {max(rows, key=lambda r: r.get('opex_inr_per_boe') or 0).get('asset')} has the highest opex of the four "
          f"(₹{num(max(r.get('opex_inr_per_boe') or 0 for r in rows))}/BOE).")
    return s1 + s2 + s3


# ----------------------------------------------------------------------------------------------
# C8 family
# ----------------------------------------------------------------------------------------------
def _c8(rows):
    loss = [r for r in rows if (r.get("pbt_inr_cr") or 0) < 0]
    flag = [r for r in rows if r.get("pec_monetisation_potential_flag") or r.get("is_divestment_candidate")]
    s1 = (f"Only {len(loss)} mature field was loss-making in FY26 - {_join(f'{r['field_name']} ({r['asset']}, PBT {inr_cr(r['pbt_inr_cr'], 2)})' for r in loss)} - "
          f"and the candidate list is {_join(f'{r['field_name']} ({r['route_from_flags']})' for r in rows)}." if len(loss) == 1 else
          f"{len(loss)} mature fields were loss-making in FY26; candidates: {_join(f'{r['field_name']} ({r['route_from_flags']})' for r in rows)}.")
    s2 = (f" {'Both' if len(rows) == 2 else 'All'} are small {rows[0].get('asset') if rows else ''} fields ({_join(f'{f(r['mmboe_fy26'], 2)} MMboe' for r in rows)} in FY26) flagged for a Production "
          f"Enhancement Contract; none is flagged for outright divestment." if flag and not any(r.get("is_divestment_candidate") for r in rows) and all(r.get("asset") == rows[0].get("asset") for r in rows) else "")
    s3 = (f" Neither is a chronic loss-maker - FY24–FY26 cumulative PBT is {_join(f'{inr_cr(r['pbt_fy24_fy26_cr'], 1)} ({r['field_name']})' for r in rows)} - "
          f"so a PEC to cut cost is a better fit than divestment or a marginal-field offer.") if rows and all((r.get("pbt_fy24_fy26_cr") or 0) > 0 for r in rows) else ""
    return s1 + s2 + s3


def _c8_drill(rows):
    hit = [r for r in rows if r.get("negative_3_consecutive_years")]
    anyneg = [r for r in rows if (r.get("negative_ebitda_years") or 0) > 0]
    lo = min(rows, key=lambda r: r.get("min_ebitda_fy24_fy26") or 0) if rows else {}
    if hit:
        s1 = f"{len(hit)} fields had negative EBITDA in each of FY24–FY26: {names(hit, 'field_name', 5)}."
    else:
        s1 = (f"None of the {len(rows)} fields in Assam (Assam and Jorhat Assets) and Cambay had negative EBITDA in FY24, FY25 or FY26"
              + (f" - in fact no field had even one negative year." if not anyneg else "."))
    s2 = (f" The weakest is {lo.get('field_name')} ({lo.get('asset')}), whose EBITDA fell from {inr_cr(lo.get('ebitda_fy24'), 1)} to "
          f"{inr_cr(lo.get('ebitda_fy26'), 1)} but stayed positive; the three-year-negative test therefore identifies no field, and the "
          f"concern is a declining trend rather than sustained cash losses.")
    return s1 + s2


def _c8_why(rows):
    bench = _first(rows, lambda r: "benchmark" in str(r.get("field_name", "")))
    cands = [r for r in rows if r is not bench]
    c = cands[0] if cands else {}
    s1 = (f"The binding constraints are extreme water cut and a fixed in-house workforce on tiny volumes: the candidate fields run at "
          f"{_join(pct(r['water_cut_pct']) for r in cands)} water cut (company {pct(_g(bench, 'water_cut_pct'))}), lifting "
          f"{_join(f(r['water_bbl_per_boe']) for r in cands)} barrels of water per BOE against {f(_g(bench, 'water_bbl_per_boe'))}.")
    s2 = (f" That pushes lifting cost to {_join(f'${f(r['lifting_cost_usd_boe'], 2)}' for r in cands)}/BOE vs ${f(_g(bench, 'lifting_cost_usd_boe'), 2)}, "
          f"of which manpower alone is {_join(f'${f(r['manpower_cost_usd_boe'], 2)}' for r in cands)} vs ${f(_g(bench, 'manpower_cost_usd_boe'), 2)}, "
          f"with only {_join(num(r['boe_per_regular_employee']) for r in cands)} BOE per regular employee (company {num(_g(bench, 'boe_per_regular_employee'))}).")
    up_ok = all(abs((r.get("avg_uptime_pct") or 0) - _g(bench, "avg_uptime_pct", 0)) <= 2 for r in cands)
    s3 = ((f" Uptime is in line with the company ({_join(pct(r['avg_uptime_pct']) for r in cands)} vs {pct(_g(bench, 'avg_uptime_pct'))}), "
           "so the problem is cost structure, not reliability - which is what a lean PEC operator changes;" if up_ok else
           " Uptime also lags the company norm;") + " third-party PEC cost benchmarks are not in the data.")
    return s1 + s2 + s3


def _c8_cmp(rows):
    tot = _first(rows, lambda r: r.get("field_name") == "Bottom-5 total")
    f5 = [r for r in rows if r is not tot]
    est = [r for r in f5 if r.get("has_estimate")]
    s1 = (f"Recorded estimates put the saving at {inr_cr(_g(tot, 'total_annual_savings_inr_cr'), 1)} a year - "
          f"{inr_cr(_g(tot, 'estimated_annual_opex_savings_inr_cr'), 1)} opex and {inr_cr(_g(tot, 'estimated_annual_capex_savings_inr_cr'), 1)} capex - "
          f"but only {len(est)} of the bottom five fields ({names(est, 'field_name', 5)}) carry an estimate.")
    s2 = (f" The five fields together spent {inr_cr(_g(tot, 'opex_fy26_inr_cr'), 1)} on opex in FY26 ({inr_cr(_g(tot, 'manpower_fy26_inr_cr'), 1)} of it "
          f"manpower) while earning {inr_cr(_g(tot, 'pbt_fy26_inr_cr'), 1)} PBT, so monetising them gives up little profit.")
    s3 = (f" Only one of the five is actually loss-making in FY26; {_join(r['field_name'] for r in f5 if not r.get('has_estimate'))} have no "
          f"savings estimate, so the full bottom-five figure cannot be stated from the data.")
    return s1 + s2 + s3


# ----------------------------------------------------------------------------------------------
# C14 family (document)
# ----------------------------------------------------------------------------------------------
def _c14(rows):
    loss = [r for r in rows if r.get("is_loss_making")]
    pec = [r for r in rows if r.get("pec_monetisation_potential_flag")]
    hc = total(rows, "regular_employee_headcount")
    ct = total(rows, "contractor_headcount")
    mm = total(rows, "mmboe_fy26")
    mp = total(rows, "allocated_manpower_cost_inr_cr")
    opex = total(rows, "total_opex_inr_cr")
    lines = [
        (f"Only {len(loss)} of the five weakest FY26 fields actually lost money "
         f"({_join(f'{r['field_name']}, {inr_cr(r['pbt_inr_cr'], 2)} PBT' for r in loss)}); the other "
         f"{len(rows) - len(loss)} are profitable but thin, so the board issue is a high-cost tail rather than large losses."),
        "",
        "**Board Note - Five weakest fields by FY26 PBT**",
        "",
        (f"**Production.** Together the five produced {f(mm, 2)} MMboe in FY26: "
         f"{_join(f'{r['field_name']} {f(r['mmboe_fy26'], 2)}' for r in rows)}."),
        (f"**Cost.** Opex was {inr_cr(opex, 1)}, of which manpower {inr_cr(mp, 1)} ({pct(mp * 100.0 / opex if opex else None)}); "
         f"lifting cost runs from ${f(min(r['lifting_cost_per_boe_usd'] for r in rows), 2)} to "
         f"${f(max(r['lifting_cost_per_boe_usd'] for r in rows), 2)}/BOE."),
        (f"**Staffing.** {num(hc)} regular employees and {num(ct)} contract workers - about "
         f"{num((hc + ct) / mm if mm else None)} people per MMboe."),
        (f"**Recommendation.** Offer {_join(r['field_name'] for r in pec)} under a Production Enhancement Contract "
         f"(recorded 5-year payoff {_join(inr_cr(r['projected_pec_farmout_payoff_5yr_inr_cr'], 1) for r in pec)}); "
         f"put the remaining fields on a cost-reduction watch-list focused on manpower redeployment."
         if pec else "**Recommendation.** Place all five on a cost-reduction watch-list focused on manpower redeployment."),
    ]
    return "\n".join(lines)


def _c14_drill(rows):
    loss = [r for r in rows if r.get("is_loss")]
    rev = total(rows, "gross_revenue_inr_cr")
    s1 = (f"In FY26 the five fields earned {inr_cr(rev, 1)} gross revenue against {inr_cr(total(rows, 'total_opex_inr_cr'), 1)} opex "
          f"({inr_cr(total(rows, 'manpower_cost_inr_cr'), 1)} manpower), for a combined net operating result of "
          f"{inr_cr(total(rows, 'net_operating_result_inr_cr'), 2)}.")
    s2 = (f" Only {_join(f'{r['field_name']} ({inr_cr(r['net_operating_result_inr_cr'], 2)})' for r in loss)} posted a net operating loss; "
          f"the others ranged from {inr_cr(min(r['net_operating_result_inr_cr'] for r in rows if not r.get('is_loss')), 2)} to "
          f"{inr_cr(max(r['net_operating_result_inr_cr'] for r in rows), 2)}.") if loss else " None posted a net operating loss."
    s3 = (f" Statutory levies ({inr_cr(total(rows, 'statutory_levies_inr_cr'), 1)}) and DD&A ({inr_cr(total(rows, 'dda_depreciation_inr_cr'), 1)}) "
          f"absorb most of the margin before PBT.")
    return s1 + s2 + s3


def _c14_why(rows):
    coded = [r for r in rows if r.get("root_cause_loss_code") not in (None, "Not recorded")]
    mp_lead = [r for r in rows if r.get("largest_opex_component") == "manpower"]
    hw = [r for r in rows if (r.get("water_cut_pct") or 0) >= 85]
    s1 = (f"Only {_join(f'{r['field_name']} ({str(r['root_cause_loss_code']).replace('_', ' ')})' for r in coded)} has a recorded root-cause code; "
          f"for the others the evidence points to the same constraint.")
    s2 = (f" {len(hw)} of the five are mature oil fields at {_join(pct(r['water_cut_pct']) for r in hw)} water cut "
          f"(a depleted water-drive reservoir), which shrinks oil output per well.") if hw else ""
    s3 = (f" In {'all five' if len(mp_lead) == len(rows) else str(len(mp_lead))} fields manpower is the largest opex line "
          f"({pct(min(r['largest_component_pct_of_opex'] for r in mp_lead))}–{pct(max(r['largest_component_pct_of_opex'] for r in mp_lead))} of opex), "
          f"so a fixed workforce on declining volumes, not a single equipment failure, is what turns these fields loss-making.") if mp_lead else ""
    return s1 + s2 + s3


def _c14_cmp(rows):
    tot = _first(rows, lambda r: str(r.get("field_name", "")).startswith("Fields with a PEC estimate"))
    est = [r for r in rows if r is not tot and r.get("pec_farmout_payoff_5yr_inr_cr") is not None]
    no = [r for r in rows if r is not tot and r.get("pec_farmout_payoff_5yr_inr_cr") is None]
    s1 = (f"For the {len(est)} fields with a recorded estimate, a PEC/farm-out is worth {inr_cr(_g(tot, 'pec_farmout_payoff_5yr_inr_cr'), 1)} "
          f"over five years versus {inr_cr(_g(tot, 'inhouse_5yr_pbt_flat_inr_cr'), 1)} if run in-house at FY26 profitability - an advantage of "
          f"{inr_cr(_g(tot, 'pec_advantage_5yr_inr_cr'), 1)} ({_join(f'{r['field_name']} {inr_cr(r['pec_advantage_5yr_inr_cr'], 1)}' for r in est)}).")
    s2 = (f" The in-house case holds FY26 PBT flat, which flatters it given declining output, so the PEC advantage is if anything understated.")
    s3 = (f" {_join(r['field_name'] for r in no)} have no PEC estimate; at FY26 PBT they would earn "
          f"{_join(inr_cr(r['inhouse_5yr_pbt_flat_inr_cr'], 1) for r in no)} in-house over five years and should be evaluated before any offer.") if no else ""
    return s1 + s2 + s3


# ----------------------------------------------------------------------------------------------
# C12 family
# ----------------------------------------------------------------------------------------------
def _c12(rows):
    co = _first(rows, lambda r: r.get("asset") == "All producing assets")
    a = [r for r in rows if r is not co]
    hi, lo = (a[0], a[-1]) if a else ({}, {})
    s1 = (f"FY26 manpower cost per BOE ranges from ${f(lo.get('manpower_cost_usd_per_boe'), 2)} (₹{num(lo.get('manpower_cost_inr_per_boe'))}) at "
          f"{lo.get('asset')} to ${f(hi.get('manpower_cost_usd_per_boe'), 2)} (₹{num(hi.get('manpower_cost_inr_per_boe'))}) at {hi.get('asset')}, "
          f"against a producing-asset average of ${f(_g(co, 'manpower_cost_usd_per_boe'), 2)} (₹{num(_g(co, 'manpower_cost_inr_per_boe'))}).")
    s2 = (f" {hi.get('asset')} is an outlier at roughly {f((hi.get('manpower_cost_usd_per_boe') or 0) / _g(co, 'manpower_cost_usd_per_boe', 1), 0)}x "
          f"the average because {num(hi.get('regular_headcount'))} employees produce only {f(hi.get('mmboe_fy26'), 2)} MMboe "
          f"({num(hi.get('boe_per_employee'))} BOE per employee vs {num(_g(co, 'boe_per_employee'))}); the next highest are "
          f"{_join(f'{r['asset']} (${f(r['manpower_cost_usd_per_boe'], 2)})' for r in a[1:3])}.")
    below2 = [r for r in a if (r.get("manpower_cost_usd_per_boe") or 99) < 2]
    s3 = (f" {_join(r['asset'] for r in below2)} sit below $2/BOE." if below2 else "")
    return s1 + s2 + s3 + " Cost is the allocated manpower cost in the FY26 field P&L; USD at the FY26 average rate."


def _c12_drill(rows):
    by = {}
    for r in rows:
        by.setdefault(r["asset"], {})[r["cadre"]] = r
    parts = []
    for asset, d in by.items():
        e, n = d.get("executive", {}), d.get("non_executive", {})
        parts.append(f"{asset} ${f((e.get('payroll_usd_per_boe') or 0) + (n.get('payroll_usd_per_boe') or 0), 2)} "
                     f"(executive ${f(e.get('payroll_usd_per_boe'), 2)}, non-executive ${f(n.get('payroll_usd_per_boe'), 2)})")
    ex_share = [d.get("executive", {}).get("pct_of_asset_payroll") for d in by.values() if d.get("executive")]
    s1 = f"On an FY26 payroll basis, manpower cost per BOE is {_join(parts)}."
    s2 = (f" Executives account for {pct(min(ex_share))}–{pct(max(ex_share))} of payroll at these assets, so the executive cadre drives "
          f"most of the cost per barrel everywhere.") if ex_share else ""
    asm = by.get("Assam Asset", {})
    s3 = (f" Assam is the exception in mix: non-executives are {pct(asm.get('non_executive', {}).get('pct_of_asset_payroll'))} of its payroll, "
          f"reflecting a larger field-crew base." if asm and (asm.get("non_executive", {}).get("pct_of_asset_payroll") or 0) > 40 else "")
    return s1 + s2 + s3 + " Payroll is FY26 gross salary from payroll_monthly (the field P&L has no cadre split)."


def _c12_why(rows):
    on = _first(rows, lambda r: r.get("onshore_offshore") == "onshore" and r.get("maturity") == "mature")
    off = _first(rows, lambda r: r.get("onshore_offshore") == "offshore" and r.get("maturity") == "mature")
    s1 = (f"It is a volume effect, not a pay effect: mature onshore fields cost ${f(_g(on, 'manpower_cost_usd_per_boe'), 2)} of manpower per BOE "
          f"vs ${f(_g(off, 'manpower_cost_usd_per_boe'), 2)} for mature offshore fields, even though each onshore employee costs less "
          f"(₹{f(_g(on, 'manpower_cost_per_employee_inr_lakh'))} lakh vs ₹{f(_g(off, 'manpower_cost_per_employee_inr_lakh'))} lakh a year)."
          if _g(on, "manpower_cost_per_employee_inr_lakh", 0) < _g(off, "manpower_cost_per_employee_inr_lakh", 0) else
          f"Mature onshore fields cost ${f(_g(on, 'manpower_cost_usd_per_boe'), 2)} of manpower per BOE vs ${f(_g(off, 'manpower_cost_usd_per_boe'), 2)} offshore.")
    s2 = (f" The difference is output per head: {num(_g(on, 'boe_per_employee'))} BOE per employee onshore vs {num(_g(off, 'boe_per_employee'))} "
          f"offshore, because onshore output is spread over {num(_g(on, 'fields'))} small fields averaging {f(_g(on, 'mmboe_per_field'), 2)} MMboe "
          f"each against {f(_g(off, 'mmboe_per_field'), 2)} MMboe per offshore field.")
    s3 = " Each onshore field needs its own minimum crew for wells, gathering stations and water handling regardless of volume, so cost per barrel rises as fields decline."
    return s1 + s2 + s3


def _c12_cmp(rows):
    last = rows[-1] if rows else {}
    first = rows[0] if rows else {}
    s1 = ("The peer comparison cannot be made from the available data: there is no Oil India Limited or other operator "
          "manpower or production data in the warehouse.")
    s2 = (f" ONGC's own company-level manpower cost was ${f(last.get('manpower_cost_usd_per_boe'), 2)} per BOE (₹{num(last.get('manpower_cost_inr_per_boe'))}) "
          f"in {last.get('fiscal_year')}, against ${f(first.get('manpower_cost_usd_per_boe'), 2)} (₹{num(first.get('manpower_cost_inr_per_boe'))}) in "
          f"{first.get('fiscal_year')}; employee cost moved from ₹{num(first.get('employee_cost_total_inr_cr'))} cr to ₹{num(last.get('employee_cost_total_inr_cr'))} cr while production went from "
          f"{f(first.get('mmboe'), 1)} to {f(last.get('mmboe'), 1)} MMboe.")
    s3 = (f" Manpower is about {pct((last.get('manpower_cost_usd_per_boe') or 0) * 100.0 / (last.get('lifting_cost_average_usd_boe') or 1))} "
          f"of the {last.get('fiscal_year')} lifting cost of ${f(last.get('lifting_cost_average_usd_boe'), 2)}/BOE; a peer benchmark would "
          f"need external annual-report data.")
    return s1 + s2 + s3


# ----------------------------------------------------------------------------------------------
# C11 follow-ups
# ----------------------------------------------------------------------------------------------
def _c11_drill(rows):
    parts = [f"{r['short_name']} {num(r['hc_mar21'])}→{num(r['hc_mar26'])} heads ({signed_pct(r['hc_change_pct'])}), crude "
             f"{f(r['crude_mmt_fy21'], 3)}→{f(r['crude_mmt_fy26'], 3)} MMT ({signed_pct(r['crude_variance_pct'])}), gas "
             f"{f(r['gas_bcm_fy21'], 3)}→{f(r['gas_bcm_fy26'], 3)} BCM ({signed_pct(r['gas_variance_pct'])})" for r in rows]
    fell = all((r.get("hc_change") or 0) < 0 for r in rows)
    s1 = (f"All three assets cut headcount over the five years while output fell: {'; '.join(parts)}." if fell else
          f"Five-year changes: {'; '.join(parts)}.")
    faster = [r for r in rows if (r.get("hc_change_pct") or 0) < (r.get("crude_variance_pct") or 0)]
    gas_faster = [r for r in rows if (r.get("gas_variance_pct") or 0) < (r.get("hc_change_pct") or 0)]
    s2 = ((f" Headcount fell faster than crude output at {_join(r['short_name'] for r in faster)}" if faster else
           " Crude output fell faster than headcount at all three")
          + (f"; gas fell faster than headcount at {_join(r['short_name'] for r in gas_faster)}." if gas_faster else "."))
    return s1 + s2 + " Headcount is 31-Mar-2021 vs 31-Mar-2026; production is FY21 vs FY26, oil and gas in separate units."


def _c11_why(rows):
    by = {r["discipline_group"]: r for r in rows}
    se, ad = by.get("Surface engineering", {}), by.get("Administrative & support", {})
    core = by.get("Subsurface, drilling & production", {})
    grew = [r for r in rows if (r.get("hc_change") or 0) > 0]
    s1 = (f"They did not expand: at the {num(_g(rows[0], 'declining_assets'))} assets whose production fell, surface engineering staff went from "
          f"{num(se.get('hc_mar21'))} to {num(se.get('hc_mar26'))} ({signed_pct(se.get('hc_change_pct'))}) and administrative & support staff from "
          f"{num(ad.get('hc_mar21'))} to {num(ad.get('hc_mar26'))} ({signed_pct(ad.get('hc_change_pct'))}) between March 2021 and March 2026."
          if not grew and rows else
          f"{_join(r['discipline_group'] for r in grew)} grew at the declining assets.")
    s2 = (f" What did rise is surface engineering's share of the workforce ({pct(se.get('share_mar21_pct'))} → {pct(se.get('share_mar26_pct'))}), "
          f"because subsurface, drilling and production staff were cut harder ({signed_pct(core.get('hc_change_pct'))}).")
    s3 = (" The question's premise comes from the earlier answer key, which summed twelve monthly headcount snapshots; on period-end "
          "headcount no asset or support function expanded.")
    return s1 + s2 + s3


def _c11_cmp(rows):
    exp = [r for r in rows if r.get("is_expanding") is True]
    pa = _first(rows, lambda r: r.get("short_name") == "Corporate average - producing assets")
    co = _first(rows, lambda r: r.get("short_name") == "Corporate average - whole company")
    e = exp[0] if exp else {}
    s1 = (f"The only expanding asset, {e.get('short_name')} (headcount {num(e.get('hc_mar21'))}→{num(e.get('hc_mar26'))}), produced "
          f"{num(e.get('boe_per_employee_fy26'))} BOE per employee in FY26 - "
          f"{f((e.get('boe_per_employee_fy26') or 0) / _g(pa, 'boe_per_employee_fy26', 1), 1)}x the producing-asset average of "
          f"{num(_g(pa, 'boe_per_employee_fy26'))} and {f((e.get('boe_per_employee_fy26') or 0) / _g(co, 'boe_per_employee_fy26', 1), 1)}x the "
          f"whole-company figure of {num(_g(co, 'boe_per_employee_fy26'))}." if len(exp) == 1 else
          f"{len(exp)} assets expanded headcount; producing-asset average is {num(_g(pa, 'boe_per_employee_fy26'))} BOE per employee.")
    nonexp = [r for r in rows if r.get("is_expanding") is False]
    top = nonexp[:2]
    s2 = (f" Its added staff therefore went where productivity is high; the most productive assets overall remain "
          f"{_join(f'{r['short_name']} ({num(r['boe_per_employee_fy26'])})' for r in top)}, and the least productive is "
          f"{nonexp[-1]['short_name']} ({num(nonexp[-1]['boe_per_employee_fy26'])}).") if nonexp else ""
    return s1 + s2 + " BOE per employee = FY26 BOE / 31-Mar-2026 headcount."


# ----------------------------------------------------------------------------------------------
# C9 family
# ----------------------------------------------------------------------------------------------
def _c9(rows):
    late = [r for r in rows if r.get("behind_schedule")]
    over = [r for r in rows if (r.get("cost_overrun_cr") or 0) > 0]
    tot = total(over, "cost_overrun_cr")
    top = rows[0] if rows else {}
    pcts = {r.get("cost_overrun_pct") for r in over}
    s1 = (f"{len(late)} major projects are behind schedule and {len(over)} are over budget, by {inr_cr(tot)} in total; the largest is "
          f"{top.get('project_name')} at {inr_cr(top.get('cost_overrun_cr'), 1)} over and {num(top.get('schedule_slippage_months'))} months late.")
    late_sorted = sorted(late, key=lambda r: -(r.get("schedule_slippage_months") or 0))
    s2 = (f" The longest delays are {_join(f'{r['project_name']} ({num(r['schedule_slippage_months'])} months, {inr_cr(r['cost_overrun_cr'], 1)})' for r in late_sorted[:3])}.")
    s3 = (f" Every project's revised cost is exactly {pct(next(iter(pcts)))} above sanction, which looks like a uniform estimate rather than "
          f"project-specific forecasts and should be validated before it is reported." if len(pcts) == 1 and over else "")
    return s1 + s2 + s3


def _c9_drill(rows):
    kg = _first(rows, lambda r: str(r.get("project_name", "")).startswith("KG-DWN"))
    pl = [r for r in rows if r is not kg]
    s1 = (f"KG-DWN-98/2 is {num(_g(kg, 'schedule_slippage_months'))} months behind (completion moved from {_g(kg, 'planned_completion')} to "
          f"{_g(kg, 'actual_or_revised_completion')}) and {inr_cr(_g(kg, 'cost_overrun_cr'), 1)} over its {inr_cr(_g(kg, 'sanctioned_cost_inr_cr'))} sanction "
          f"({pct(_g(kg, 'cost_overrun_pct'))}), with {num(_g(kg, 'delayed_milestones'))} milestones on the delayed critical path.")
    s2 = (f" Among the Western Offshore pipeline replacement projects, "
          f"{_join(f'{r['project_name']} is {num(r['schedule_slippage_months'])} months late and {inr_cr(r['cost_overrun_cr'], 1)} over ({r['status']})' for r in pl)}.")
    worst = max(pl, key=lambda r: r.get("schedule_slippage_months") or 0) if pl else {}
    s3 = (f" {worst.get('project_name')} is the one still open and slipping, now due {worst.get('actual_or_revised_completion')}." if worst.get("status") == "delayed" else "")
    return s1 + s2 + s3


def _c9_why(rows):
    tot = total(rows, "projects_slipped")
    top = rows[0] if rows else {}
    s1 = (f"Contractor standby is the most common cause: {num(top.get('projects_slipped'))} of the {num(tot)} slipped projects "
          f"(average {f(top.get('avg_slippage_months'))} months) - {top.get('projects')}." if top.get("delay_root_cause_category") == "contractor_standby" else
          f"The most common cause is {str(top.get('delay_root_cause_category')).replace('_', ' ')} ({num(top.get('projects_slipped'))} of {num(tot)} slipped projects).")
    others = rows[1:]
    s2 = (f" The rest trace to {_join(f'{str(r['delay_root_cause_category']).replace('_', ' ')} ({r['projects']})' for r in others)}.")
    big = max(rows, key=lambda r: r.get("cost_overrun_cr") or 0) if rows else {}
    s3 = (f" By value, {str(big.get('delay_root_cause_category')).replace('_', ' ')} dominates ({inr_cr(big.get('cost_overrun_cr'), 1)} of overrun on "
          f"{num(big.get('projects_slipped'))} project(s)), so it matters more than the most frequent cause.") if big and big is not top else ""
    return s1 + s2 + s3


def _c9_cmp(rows):
    tot = _first(rows, lambda r: str(r.get("project_name", "")).startswith("Portfolio total"))
    prj = [r for r in rows if r is not tot]
    same_rce = all((r.get("variance_vs_rce_cr") or 0) == 0 for r in prj)
    top = prj[0] if prj else {}
    s1 = (f"Across the {len(prj)} projects the anticipated final cost is {inr_cr(_g(tot, 'anticipated_final_cost_inr_cr'))} against "
          f"{inr_cr(_g(tot, 'original_sanctioned_cost_inr_cr'))} originally sanctioned by the Board - {inr_cr(_g(tot, 'variance_vs_original_cr'))} "
          f"({pct(_g(tot, 'variance_vs_original_pct'))}) over.")
    s2 = (" The anticipated final cost equals the latest Revised Cost Estimate for every project, so no further overrun beyond the RCE is forecast."
          if same_rce else f" {sum(1 for r in prj if (r.get('variance_vs_rce_cr') or 0) > 0)} projects are forecast above their RCE.")
    s3 = (f" {top.get('project_name')} alone accounts for {inr_cr(top.get('variance_vs_original_cr'), 1)} "
          f"({pct((top.get('variance_vs_original_cr') or 0) * 100.0 / _g(tot, 'variance_vs_original_cr', 1))} of the portfolio variance).")
    return s1 + s2 + s3


# ----------------------------------------------------------------------------------------------
# C7 family
# ----------------------------------------------------------------------------------------------
def _c7(rows):
    top = rows[:3]
    under = [r for r in rows if r.get("under_invested")]
    under = sorted(under, key=lambda r: -(r.get("reserves_2p_mmtoe_fy26") or 0))
    s1 = (f"Over FY22–FY26 the most capex went to {_join(f'{r['asset']} ({inr_cr(r['capex_fy22_fy26_cr'])}, {pct(r['pct_of_5yr_capex'])})' for r in top)}; "
          f"the under-invested reserve holders are {_join(f'{r['asset']} ({pct(r['pct_of_2p_reserves'])} of 2P reserves but {pct(r['pct_of_5yr_capex'])} of capex)' for r in under[:4])}.")
    b = under[0] if under else {}
    s2 = (f" {b.get('asset')} - home of {b.get('largest_2p_field')} - received {inr_cr(b.get('capex_cr_per_mmtoe_2p'), 1)} per MMTOE of 2P reserves "
          f"against an average of {inr_cr(b.get('avg_capex_cr_per_mmtoe_2p'), 1)}, the clearest case for more development spend.") if b else ""
    plant = [r for r in top if r.get("wc_type") in ("plant", "office", "institute")]
    s3 = (f" {plant[0]['asset']} is a {plant[0]['wc_type']}, not a reserve holder, so its {inr_cr(plant[0]['capex_fy22_fy26_cr'])} should be "
          f"verified against the project register before drawing conclusions.") if plant else ""
    return s1 + s2 + s3 + " Capex is recorded by asset, so under-investment is assessed at asset level (largest field shown)."


def _c7_drill(rows):
    by = {r["region"]: r for r in rows}
    w = by.get("Western Offshore (MH, B&S)", {})
    e = by.get("Eastern Offshore (KG Basin)", {})
    lead, lag = (e, w) if (e.get("cumulative_5yr_cr") or 0) > (w.get("cumulative_5yr_cr") or 0) else (w, e)
    s1 = (f"Eastern Offshore (KG Basin) received {inr_cr(e.get('cumulative_5yr_cr'))} of capex over FY22–FY26 "
          f"({pct(e.get('pct_of_company_5yr_capex'))} of company capex) against {inr_cr(w.get('cumulative_5yr_cr'))} "
          f"({pct(w.get('pct_of_company_5yr_capex'))}) for Western Offshore (Mumbai High plus Bassein & Satellite).")
    s2 = (f" {lead.get('region')} leads by {inr_cr((lead.get('cumulative_5yr_cr') or 0) - (lag.get('cumulative_5yr_cr') or 0))}; spending in both "
          f"regions more than doubled in FY25 (Eastern {inr_cr(e.get('fy25_cr'))}, Western {inr_cr(w.get('fy25_cr'))}) before easing in FY26.")
    return s1 + s2


def _c7_why(rows):
    have = [r for r in rows if r.get("dev_drilling_be_cr") is not None]
    none = [r for r in rows if r.get("dev_drilling_be_cr") is None]
    none_big = sorted(none, key=lambda r: -(r.get("reserves_2p_mmtoe_fy26") or 0))[:3]
    under = [r for r in have if (r.get("actual_vs_be_cr") or 0) < 0]
    s1 = (f"The shortfall is mostly not under-spending against BE/RE but the absence of any development-drilling budget line: "
          f"{_join(f'{r['asset']} ({f(r['reserves_2p_mmtoe_fy26'], 1)} MMTOE 2P)' for r in none_big)} had no development-drilling capex "
          f"budgeted or spent in FY22–FY26.")
    s2 = (f" Where a line exists, spend tracked plan closely - {_join(f'{r['asset']} {pct(r['utilisation_vs_be_pct'])} of BE' for r in have)} - and "
          f"the largest gap is {min(have, key=lambda r: r.get('actual_vs_be_cr') or 0)['asset']} at "
          f"{inr_cr(min(r.get('actual_vs_be_cr') or 0 for r in have))} vs BE.") if have else ""
    s3 = (" The data holds no recorded reason for the allocation, so the 'why' is a planning-allocation gap (reserves not translated into "
          "drilling budgets), not an execution shortfall; capex is also not recorded at field level.")
    return s1 + s2 + s3


def _c7_cmp(rows):
    kg = _first(rows, lambda r: str(r.get("development", "")).startswith("KG"))
    mh = _first(rows, lambda r: str(r.get("development", "")).startswith("Mumbai"))
    similar = abs(_g(kg, "rrr_2p_fy26", 0) - _g(mh, "rrr_2p_fy26", 0)) <= 0.1
    s1 = (f"{'Both developments replace reserves at a similar rate' if similar else 'Reserve replacement differs'} (2P RRR {f(_g(kg, 'rrr_2p_fy26'), 2)} for KG-DWN-98/2 vs "
          f"{f(_g(mh, 'rrr_2p_fy26'), 2)} for Mumbai High in FY26; {f(_g(kg, 'rrr_2p_fy22_fy26'), 2)} vs {f(_g(mh, 'rrr_2p_fy22_fy26'), 2)} over FY22–FY26), "
          f"but capital intensity is {'far higher at KG' if _g(kg, 'project_capex_usd_per_boe_added', 0) > 2 * _g(mh, 'project_capex_usd_per_boe_added', 0) else 'comparable'}: ${f(_g(kg, 'project_capex_usd_per_boe_added'), 2)} of project capex per BOE added vs "
          f"${f(_g(mh, 'project_capex_usd_per_boe_added'), 2)} for MH Redevelopment.")
    s2 = (f" KG's {inr_cr(_g(kg, 'project_revised_cost_cr'))} project added {f(_g(kg, 'accretion_fy22_fy26_mmtoe'), 2)} MMTOE of 2P over five years, "
          f"while MH's {inr_cr(_g(mh, 'project_revised_cost_cr'))} redevelopment added {f(_g(mh, 'accretion_fy22_fy26_mmtoe'), 2)} MMTOE; reported "
          f"development cost is ${f(_g(kg, 'dev_cost_usd_boe_fy26'), 2)}/BOE vs ${f(_g(mh, 'dev_cost_usd_boe_fy26'), 2)}/BOE.")
    s3 = " KG is a first-time deepwater development whose cost buys new production capacity, so its $/BOE added is expected to fall as further reserves are booked."
    return s1 + s2 + s3


# ----------------------------------------------------------------------------------------------
# C10 family
# ----------------------------------------------------------------------------------------------
def _c10(rows):
    exc = [r for r in rows if str(r.get("fy27_projected_rating", "")).lower() == "excellent"]
    good = [r for r in rows if str(r.get("fy27_projected_rating", "")).lower() == "good"]
    vg = [r for r in rows if str(r.get("fy27_projected_rating", "")).lower() == "very good"]
    r0 = rows[0] if rows else {}
    s1 = (f"FY27 is tracking {'Very Good at best' if not exc else 'partly Excellent'}: on the H1 run-rate the projected composite score is "
          f"{f(r0.get('fy27_projected_composite'), 2)} (to date {f(r0.get('fy27_composite_to_date'), 2)}), with {len(exc)} of {len(rows)} "
          f"parameters on course for Excellent, {len(vg)} Very Good and {len(good)} Good.")
    worst = sorted(rows, key=lambda r: r.get("pct_of_excellent") or 0)[:3]
    s2 = (f" The weakest are {_join(f'{r['parameter_name']} ({f(r['fy27_projected_achievement'], 3 if r['unit_of_measure'] in ('MMT', 'BCM', 'Ratio', 'Rate') else 0)} {r['unit_of_measure']} vs Excellent {f(r['excellent_target'], 3 if r['unit_of_measure'] in ('MMT', 'BCM', 'Ratio', 'Rate') else 0)}, {pct(r['pct_of_excellent'])})' for r in worst)}.")
    crude = _first(rows, lambda r: str(r.get("parameter_name", "")).startswith("Crude"))
    s3 = (f" Crude oil, the heaviest-weighted parameter ({num(_g(crude, 'weightage'))}%), is projected at {f(_g(crude, 'fy27_projected_achievement'), 3)} MMT - "
          f"below even the Very Good threshold of {f(_g(crude, 'very_good_target'), 1)} MMT.") if crude and (crude.get("fy27_projected_achievement") or 0) < (crude.get("very_good_target") or 0) else ""
    return s1 + s2 + s3 + " FY27 figures are full-year projections on six months of actuals (Apr–Sep 2026); LTIFR is scored lower-is-better."


def _c10_drill(rows):
    good = [r for r in rows if str(r.get("fy27_projected_rating", "")).lower() == "good"]
    named = [r for r in rows if any(k in str(r.get("parameter_name", "")) for k in ("Crude", "Gas", "Capital", "Reserve"))]
    tot = total(rows, "weighted_score_forgone")
    s1 = (f"{len(rows)} FY27 MoU parameters are currently projected below 'Excellent', including {'all four' if len(named) == 4 else len(named)} of those named: "
          f"{_join(f'{r['parameter_name']} ({r['fy27_projected_rating']})' for r in named)}.")
    drag = max(rows, key=lambda r: r.get("weighted_score_forgone") or 0) if rows else {}
    s2 = (f" {len(good)} are only 'Good' ({_join(r['parameter_name'] for r in good)}), and {drag.get('parameter_name')} alone forgoes "
          f"{f(drag.get('weighted_score_forgone'), 2)} composite points, the largest single drag.")
    s3 = f" In total {f(tot, 2)} points of composite score are being lost versus an all-Excellent outcome."
    return s1 + s2 + s3


def _c10_why(rows):
    co = _first(rows, lambda r: r.get("scope") == "Company total")
    assets = [r for r in rows if r is not co]
    up = [r for r in assets if (r.get("q2_change_vs_fy26_bcm") or 0) > 0]
    down = [r for r in assets if (r.get("q2_change_vs_fy26_bcm") or 0) < 0]
    s1 = (f"Q2 FY27 gas output was {f(_g(co, 'q2_fy27_bcm'), 3)} BCM against a pro-rata Excellent target of {f(_g(co, 'mou_excellent_q_target_bcm'), 3)} BCM "
          f"(gap {f(_g(co, 'q2_gap_to_excellent_bcm'), 3)} BCM) - just above the Very Good pace of {f(_g(co, 'mou_very_good_q_target_bcm'), 3)} BCM and "
          f"{signed_pct(_g(co, 'q2_change_pct'))} on Q2 FY26, so it is behind the Excellent schedule rather than falling.")
    s2 = (f" Natural decline at {len(down)} assets (largest drops {_join(f'{r['scope']} {f(r['q2_change_vs_fy26_bcm'], 3)} BCM' for r in down[:2])}) "
          f"was {'more than ' if (_g(co, 'q2_change_vs_fy26_bcm', 0) > 0) else 'partly '}offset by {_join(f'{r['scope']} (+{f(r['q2_change_vs_fy26_bcm'], 3)} BCM, {signed_pct(r['q2_change_pct'])})' for r in up)}, "
          f"but not by enough to reach the Excellent run-rate.") if up else ""
    s3 = (" The development-well part cannot be assessed: no FY27 wells are recorded in wells_drilled." if _g(co, "fy27_wells_recorded", 0) == 0 else "")
    return s1 + s2 + s3


def _c10_cmp(rows):
    by = {r["fiscal_year"]: r for r in rows}
    a, b, c = by.get("FY25", {}), by.get("FY26", {}), by.get("FY27", {})
    s1 = (f"On current trends FY27 will close with a composite score of about {f(c.get('projected_year_end_composite'), 2)}, versus "
          f"{f(a.get('composite_score'), 2)} in FY25 when {num(a.get('params_excellent'))} parameters ({num(a.get('weight_rated_excellent'))}% of weight) "
          f"were rated Excellent.")
    s2 = (f" The score has slid for two years - {f(b.get('composite_score'), 2)} in FY26 with no Excellent parameter - and FY27 again has "
          f"{num(c.get('params_excellent'))} Excellent and {num(c.get('params_good'))} Good ratings.")
    s3 = (f" Recovering FY25's level would need roughly {f((a.get('composite_score') or 0) - (c.get('projected_year_end_composite') or 0), 2)} "
          f"extra points in H2, i.e. several parameters moving up a full band.")
    return s1 + s2 + s3


# ----------------------------------------------------------------------------------------------
# C13 family (what-if)
# ----------------------------------------------------------------------------------------------
def _c13(rows):
    tot = _first(rows, lambda r: r.get("section") == "scenario_total")
    rec = [r for r in rows if r.get("section") == "receiving_asset"]
    s1 = (f"Moving 200 E3–E5 executives from Delhi and Dehradun to field assets would cost about {inr_cr(_g(tot, 'one_time_transfer_cost_cr'), 2)} "
          f"one-time (₹{f(_g(tot, 'avg_transfer_cost_lakh'), 2)} lakh per officer in transfer grant, CTA and baggage) plus "
          f"{inr_cr(_g(tot, 'annual_hard_station_allowance_cr'), 2)} a year in hard-station allowance, and would lift field executive "
          f"coverage from {pct(_g(tot, 'fill_pct_before'))} to {pct(_g(tot, 'fill_pct_after'))} of sanctioned posts.")
    s2 = (f" Allocated pro-rata to vacancies, the biggest gains go to {_join(f'{r['entity']} (+{num(r['allocated_officers'])})' for r in rec[:3])}, "
          f"but {num(_g(tot, 'vacancy_after_move'))} of the {num(_g(tot, 'exec_vacancy'))} field executive vacancies would remain.")
    s3 = (f" The pool is available: Delhi and Dehradun hold {num(_g(tot, 'source_pool_e3_e5'))} E3–E5 executives, {num(_g(tot, 'source_pool_overdue'))} "
          f"of them already overdue for rotation; salaries move with the officers, so there is no payroll saving.")
    return s1 + s2 + s3


def _c13_drill(rows):
    top = rows[:3]
    zero = [r for r in rows if (r.get("pm_vacancy") or 0) == 0]
    named = {r["field_asset"]: r for r in rows}
    tri, cau, asm = named.get("Tripura Asset", {}), named.get("Cauvery Asset", {}), named.get("Assam Asset", {})
    s1 = (f"The largest production and maintenance engineering coverage gains go to "
          f"{_join(f'{r['field_asset']} +{num(r['pm_coverage_gain'])} ({pct(r['pm_fill_pct_before'])}→{pct(r['pm_fill_pct_after'])} P&M fill)' for r in top)}.")
    s2 = (f" Of the examples named, Tripura gains {num(tri.get('pm_coverage_gain'))} ({pct(tri.get('pm_fill_pct_before'))}→{pct(tri.get('pm_fill_pct_after'))}) "
          f"and Karaikal (Cauvery Asset) {num(cau.get('pm_coverage_gain'))} ({pct(cau.get('pm_fill_pct_before'))}→{pct(cau.get('pm_fill_pct_after'))}), "
          f"while Assam gains {num(asm.get('pm_coverage_gain'))} because its P&M posts are already {pct(asm.get('pm_fill_pct_before'))} filled.")
    s3 = (f" {_join(r['field_asset'] for r in zero)} have no P&M vacancy, so officers sent there would be surplus to sanctioned strength." if zero else "")
    return s1 + s2 + s3


def _c13_why(rows):
    by = {r["component"]: r for r in rows}
    tg, cta, bag, tot = (by.get(k, {}) for k in ("One-time transfer grant", "Composite transfer grant (CTA)", "Baggage transportation", "Total one-time cost"))
    return (f"Moving 200 officers would cost about {inr_cr(tot.get('cost_for_200_officers_cr'), 2)} one-time: transfer grant "
            f"{inr_cr(tg.get('cost_for_200_officers_cr'), 2)} (₹{num(tg.get('per_officer_inr'))} each), composite transfer grant "
            f"{inr_cr(cta.get('cost_for_200_officers_cr'), 2)} (₹{num(cta.get('per_officer_inr'))} each) and baggage transportation "
            f"{inr_cr(bag.get('cost_for_200_officers_cr'), 2)} (₹{num(bag.get('per_officer_inr'))} each). "
            f"The rates are the averages of {num(tot.get('postings_basis'))} actual E3–E5 rotation and hard-station postings in FY24–FY26, "
            f"so CTA is the largest component ({pct((cta.get('per_officer_inr') or 0) * 100.0 / (tot.get('per_officer_inr') or 1), 0)} of the total). "
            f"These are one-off costs; recurring hard-station allowance is shown in the parent scenario.")


def _c13_cmp(rows):
    hq = [r for r in rows if r.get("scope") in ("Delhi HQ", "Dehradun Tel Bhavan")]
    fld = _first(rows, lambda r: r.get("scope") == "Receiving field assets")
    moved = total(hq, "payroll_moved_out_cr")
    s1 = (f"The move shifts about {inr_cr(moved, 1)} of annual executive payroll out of Delhi and Dehradun "
          f"({_join(f'{r['scope']} {num(r['executives_before'])}→{num(r['executives_after'])} executives, {signed_pct(r['exec_change_pct'])}' for r in hq)}), "
          f"but this is overhead re-allocated to the field, not a company saving.")
    s2 = (f" In the field it adds {signed_pct(_g(fld, 'exec_change_pct'))} to executive strength at the receiving assets, moving the supervision ratio only "
          f"from {f(_g(fld, 'non_exec_per_exec_before'), 2)} to {f(_g(fld, 'non_exec_per_exec_after'), 2)} non-executives per executive.")
    s3 = (f" Uptime at those assets already averages {pct(_g(fld, 'avg_uptime_pct_fy26'))}, and there is no data linking staffing to uptime, so the "
          f"case rests on filling vacancies and reducing HQ concentration rather than on a measurable uptime gain.")
    return s1 + s2 + s3


def _c1(rows):
    ge5 = total(rows, "delhi_executives_ge_5yr")
    ret = total(rows, "exempt_retiring_3yr")
    tag = total(rows, "exempt_valid_tag")
    due = total(rows, "non_exempt_due_transfer")
    top = sorted(rows, key=lambda r: -(r.get("delhi_executives_ge_5yr") or 0))[:3]
    cells = ", ".join(f"{r['grade_id']} {r['discipline_id']} ({num(r['delhi_executives_ge_5yr'])})" for r in top)
    return (f"{num(ge5)} executives have been in the Delhi office (WC-DEL) continuously for 5 years or more as of 19-Oct-2026. "
            f"Of these, {num(due)} are due for rotational transfer under JRTP Clause 3.0; {num(ret)} are protected because they retire within "
            f"3 years (Clause 7.1 practice) and {num(tag)} {'holds' if tag == 1 else 'hold'} a valid recorded exemption. "
            f"The largest grade/discipline cells are {cells}. "
            f"Caveat: most current stays in posting_history start on 1-Jul-2020, so tenure is a lower bound and the list should be checked against service books.")


NARRATIVES = {
    "C1": _c1,
    "C11": _c11,
    "C11__drill_down": _c11_drill,
    "C11__why": _c11_why,
    "C11__compare_or_so_what": _c11_cmp,
    "C1__drill_down": _c1_drill,
    "C1__why": _c1_why,
    "C1__compare_or_so_what": _c1_cmp,
    "C2": _c2,
    "C2__drill_down": _c2_drill,
    "C2__why": _c2_why,
    "C2__compare_or_so_what": _c2_cmp,
    "C3": _c3,
    "C3__drill_down": _c3_drill,
    "C3__why": _c3_why,
    "C3__compare_or_so_what": _c3_cmp,
    "C4": _c4,
    "C4__drill_down": _c4_drill,
    "C4__why": _c4_why,
    "C4__compare_or_so_what": _c4_cmp,
    "C5": _c5,
    "C5__drill_down": _c5_drill,
    "C5__why": _c5_why,
    "C5__compare_or_so_what": _c5_cmp,
    "C6": _c6,
    "C6__drill_down": _c6_drill,
    "C6__why": _c6_why,
    "C6__compare_or_so_what": _c6_cmp,
    "C8": _c8,
    "C8__drill_down": _c8_drill,
    "C8__why": _c8_why,
    "C8__compare_or_so_what": _c8_cmp,
    "C14": _c14,
    "C14__drill_down": _c14_drill,
    "C14__why": _c14_why,
    "C14__compare_or_so_what": _c14_cmp,
    "C12": _c12,
    "C12__drill_down": _c12_drill,
    "C12__why": _c12_why,
    "C12__compare_or_so_what": _c12_cmp,
    "C9": _c9,
    "C9__drill_down": _c9_drill,
    "C9__why": _c9_why,
    "C9__compare_or_so_what": _c9_cmp,
    "C7": _c7,
    "C7__drill_down": _c7_drill,
    "C7__why": _c7_why,
    "C7__compare_or_so_what": _c7_cmp,
    "C10": _c10,
    "C10__drill_down": _c10_drill,
    "C10__why": _c10_why,
    "C10__compare_or_so_what": _c10_cmp,
    "C13": _c13,
    "C13__drill_down": _c13_drill,
    "C13__why": _c13_why,
    "C13__compare_or_so_what": _c13_cmp,
}
