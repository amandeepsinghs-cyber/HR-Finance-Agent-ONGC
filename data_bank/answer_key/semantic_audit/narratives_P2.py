"""Narratives for P11-P20 entries (slice P2; rendered from result rows; no typed numbers)."""

from semantic_audit.common import f, inr, inr_cr, names, num, pct, signed_pct, total  # noqa: F401


def _g(r, k, d=0):
    v = (r or {}).get(k)
    return d if v is None else v


def _first(rows, pred):
    for r in rows:
        if pred(r):
            return r
    return {}


# ----------------------------------------------------------------------------- P11
def _p11(rows):
    ex = _first(rows, lambda r: r.get("in_jrtp_scope"))
    non = _first(rows, lambda r: "Non-executive" in str(r.get("staff_population", "")))
    brd = _first(rows, lambda r: "Board" in str(r.get("staff_population", "")))
    b = _g(ex, "breached_10yr_cap")
    if b:
        lead = (f"{num(b)} executives currently in the Delhi cluster have exceeded the JRTP 10-year cumulative cap; "
                f"{num(_g(ex, 'breached_exempt_retiring_3yr'))} are exempt as they retire within 3 years and "
                f"{num(_g(ex, 'breached_due_transfer'))} are due for transfer.")
    else:
        lead = (f"No executive in Delhi has exceeded the JRTP 10-year cumulative-tenure cap: the longest cumulative Delhi stay "
                f"among the {num(_g(ex, 'currently_in_delhi_cluster'))} executives there is {f(_g(ex, 'max_cumulative_years', None), 1)} years, "
                f"so nobody is due for a cap-driven transfer and no retirement exemption is needed.")
    s2 = (f" The {num(_g(non, 'breached_10yr_cap'))} long-stayers that a raw count throws up are Group B/C/D non-executives "
          f"(outside JRTP Clause 1.2), plus {num(_g(brd, 'breached_10yr_cap'))} Board member (the CMD), who is also outside the policy.")
    s3 = (f" Watch-list: {num(_g(ex, 'approaching_cap_8yr_plus'))} executives are past 8 years in the cluster, and "
          f"{num(_g(ex, 'retiring_within_3yr'))} Delhi executives retire within 3 years ({num(_g(ex, 'retiring_within_2yr'))} within 2), "
          f"which would protect them under Clause 7.1 if they are ever listed for transfer.")
    return lead + s2 + s3


def _p11_dd(rows):
    n = total(rows, "executives_in_delhi")
    b = total(rows, "breached_10yr_cap")
    top = max(rows, key=lambda r: _g(r, "max_cumulative_years", 0)) if rows else {}
    near = [r for r in rows if _g(r, "approaching_cap_8yr_plus")]
    lead = (f"There are {num(b)} executives in Delhi over the 10-year cumulative cap, so no list of breaching executives exists "
            f"in the posting records (the premise of 138 is not supported).") if not b else (
            f"{num(b)} Delhi executives exceed the 10-year cumulative cap.")
    s2 = (f" Across {num(n)} executives in grades {names(rows, 'grade_id', 1)} to {rows[-1].get('grade_id') if rows else 'n/a'}, "
          f"{num(total(rows, 'over_5yr_in_cluster'))} have spent over 5 years in the cluster and {num(total(rows, 'approaching_cap_8yr_plus'))} "
          f"are past 8 years ({names(near, 'grade_id', 6)}); the longest stay is {f(_g(top, 'max_cumulative_years', None), 2)} years in grade {top.get('grade_id')}.")
    s3 = f" {num(total(rows, 'retiring_within_3yr'))} of these executives retire within 3 years."
    return lead + s2 + s3


def _p11_cmp(rows):
    d = _first(rows, lambda r: r.get("is_delhi"))
    others = [r for r in rows if not r.get("is_delhi")]
    top = others[0] if others else {}
    tot = total(rows, "non_exempt_to_rotate")
    lead = (f"Rotating every non-exempt tenure-breaching officer would change Delhi executive staffing by "
            f"{num(-_g(d, 'non_exempt_to_rotate'))} ({signed_pct(_g(d, 'net_change_pct', None))}), from "
            f"{num(_g(d, 'executives_in_cluster'))} to {num(_g(d, 'executives_after_rotation'))}, because no Delhi executive has breached the cap.")
    s2 = (f" The rotation load sits elsewhere: {num(tot)} non-exempt executives breach the cap company-wide, led by "
          f"{top.get('cluster_name')} ({num(_g(top, 'non_exempt_to_rotate'))}, {signed_pct(_g(top, 'net_change_pct', None))} of its executives)"
          f" and {others[1].get('cluster_name') if len(others) > 1 else 'n/a'} ({num(_g(others[1] if len(others) > 1 else {}, 'non_exempt_to_rotate'))}).")
    s3 = f" A further {num(total(rows, 'exempt_retiring_3yr'))} breaching executives are protected by the 3-year pre-retirement rule."
    return lead + s2 + s3


# ----------------------------------------------------------------------------- P12
def _p12(rows):
    never = [r for r in rows if r.get("never_hard_or_ne_posted")]
    short = [r for r in rows if not r.get("never_hard_or_ne_posted")]
    lead = (f"{len(rows)} executives due for E4→E5 review have not completed the mandatory continuous 3-year hard/North-East tenure; "
            f"{len(never)} of them ({names(never, 'name', 3)}) has never had a hard or NE posting at all.")
    s2 = (f" The other {len(short)} ({names(short, 'name', 3)}) have a longest continuous hard/NE stint of "
          f"{num(min((_g(r, 'longest_continuous_hard_ne_days') for r in short), default=None))}–{num(max((_g(r, 'longest_continuous_hard_ne_days') for r in short), default=None))} days, short of the 3 years JRTP Clause 6.1 requires,"
          f" so under Clause 6.2 they should be kept out of the zone of consideration unless the EC grants a deferment.")
    discs = sorted({str(r.get("discipline")) for r in rows})
    reasons = sorted({str(r.get("pending_reason", "")).replace("_", " ") for r in rows})
    s3 = (f" They are in {', '.join(discs)}, and their DPCs are already held up for other reasons ({'; '.join(reasons)}).") if rows else ""
    return lead + s2 + s3


def _p12_dd(rows):
    due = total(rows, "due_for_e4_e5_review")
    by = {r.get("discipline"): r for r in rows}
    drl, prd = by.get("Drilling", {}), by.get("Production", {})
    fa = by.get("Finance & Accounts (F&A)", {})
    lead = (f"Of the {num(due)} E4 executives currently due for E5 review, {num(_g(drl, 'due_for_e4_e5_review'))} are in Drilling, "
            f"{num(_g(prd, 'due_for_e4_e5_review'))} in Production and {num(_g(fa, 'due_for_e4_e5_review'))} in F&A.")
    s2 = (f" Only {num(total(rows, 'lacking_3yr_hard_ne_tenure'))} lack the 3-year hard/NE tenure (Production {num(_g(prd, 'lacking_3yr_hard_ne_tenure'))}, "
          f"Drilling {num(_g(drl, 'lacking_3yr_hard_ne_tenure'))}), so the hardship rule is not what is holding these cases back.")
    s3 = (f" The '260' in the question is not supported: open E4→E5 cases exist only in {names(rows, 'discipline', 5)}.")
    return lead + s2 + s3


def _p12_cmp(rows):
    met = _first(rows, lambda r: str(r.get("hardship_status", "")).startswith("Met"))
    some = _first(rows, lambda r: str(r.get("hardship_status", "")).startswith("Some"))
    none = _first(rows, lambda r: str(r.get("hardship_status", "")).startswith("No"))
    lead = (f"Officers who met the 3-year hard/NE norm cleared E4→E5 at {pct(_g(met, 'clearance_rate_pct', None))}, lower than those who "
            f"did not ({pct(_g(some, 'clearance_rate_pct', None))} with under 3 years, {pct(_g(none, 'clearance_rate_pct', None))} with no hard posting).")
    s2 = (f" So the prerequisite is not being enforced: {num(_g(some, 'cleared') + _g(none, 'cleared'))} officers were promoted since FY22 without "
          f"completing it, and no hardship waiver is recorded for any of them.")
    s3 = (f" Of {num(total(rows, 'e4_e5_cases'))} cases, the {num(total(rows, 'pending_delayed'))} pending ones are stuck on court stays "
          f"and vigilance clearance rather than on hardship tenure.")
    return lead + s2 + s3


# ----------------------------------------------------------------------------- P13
def _p13(rows):
    fy = _first(rows, lambda r: r.get("fiscal_year") == "FY26")
    ytd = _first(rows, lambda r: r.get("fiscal_year") == "FY27")
    within = "Yes" if fy.get("within_cap") else "No"
    lead = (f"{within}: FY26 employer superannuation contributions were {pct(_g(fy, 'total_employer_super_pct', None))} of Basic + DA "
            f"against the DPE 30% cap, leaving {f(_g(fy, 'headroom_pct_points', None), 1)} percentage points, or "
            f"{inr_cr(_g(fy, 'headroom_cr', None))} of headroom on a Basic + DA base of {inr_cr(_g(fy, 'basic_plus_da_cr', None))}.")
    s2 = (f" The mix is CPF {pct(_g(fy, 'cpf_pct', None))}, PRBS {pct(_g(fy, 'prbs_pct', None))}, PRMB {pct(_g(fy, 'prmb_pct', None))} and gratuity "
          f"{pct(_g(fy, 'gratuity_pct_imputed', None))}, so PRBS could be raised to its upper band without breaching the cap.")
    s3 = (f" FY27 to date ({num(_g(ytd, 'months_covered'))} months) runs at the same {pct(_g(ytd, 'total_employer_super_pct', None))};"
          f" the gratuity rate is imputed because gratuity is not booked in payroll.")
    return lead + s2 + s3


def _p13_dd(rows):
    by = {str(r.get("scheme")): r for r in rows}

    def p(key):
        for k, r in by.items():
            if k.startswith(key):
                return r
        return {}
    cpf, prbs, prmb, gr, tot = p("Contributory"), p("PRBS"), p("Post-retirement"), p("Gratuity"), p("Total")
    lead = (f"In FY26 the employer put {pct(_g(cpf, 'pct_of_basic_da', None), 2)} of Basic + DA into CPF, {pct(_g(prbs, 'pct_of_basic_da', None), 2)} into PRBS pension, "
            f"{pct(_g(gr, 'pct_of_basic_da', None), 2)} into gratuity and {pct(_g(prmb, 'pct_of_basic_da', None), 2)} into post-retirement medical, "
            f"{pct(_g(tot, 'pct_of_basic_da', None), 2)} in total ({inr_cr(_g(tot, 'employer_contribution_cr', None))}).")
    s2 = (f" PRMB at {pct(_g(prmb, 'pct_of_basic_da', None), 2)} is below the {prmb.get('policy_reference_rate', 'n/a')} reference rate in PRBS Clause 3.1, "
          f"while PRBS ({inr_cr(_g(prbs, 'employer_contribution_cr', None))}) sits inside its {prbs.get('policy_reference_rate', 'n/a')} band.")
    s3 = " Gratuity is imputed from the payroll superannuation rate because it is not booked in payroll."
    return lead + s2 + s3


def _p13_cmp(rows):
    ex = _first(rows, lambda r: str(r.get("cadre_group", "")).startswith("Executives"))
    lead = (f"On the FY26 executive payroll, {inr_cr(_g(ex, 'headroom_cr', None), 1)} of headroom remains under the 30% cap: "
            f"executive employer superannuation contributions were {inr_cr(_g(ex, 'employer_super_contribution_cr', None), 1)} "
            f"against a cap of {inr_cr(_g(ex, 'cap_amount_cr', None), 1)} ({pct(_g(ex, 'employer_super_pct', None))} of Basic + DA).")
    s2 = (f" Across all cadres the headroom is {inr_cr(total(rows, 'headroom_cr'), 1)}, so any enrichment of executive superannuation "
          f"(e.g. a higher PRBS rate) must fit within that amount.")
    s3 = f" The executive figure covers {num(_g(ex, 'employees_paid'))} executives paid during the year (Basic + DA {inr_cr(_g(ex, 'basic_plus_da_cr', None), 1)})."
    return lead + s2 + s3


# ----------------------------------------------------------------------------- P14
def _p14(rows):
    ex = _first(rows, lambda r: r.get("mou_rating") == "Excellent")
    vg = _first(rows, lambda r: r.get("mou_rating") == "Very Good")
    gd = _first(rows, lambda r: r.get("mou_rating") == "Good")
    lead = (f"Dropping from Excellent to Very Good would cut the executive PRP pool by {pct(abs(_g(vg, 'change_vs_excellent_pct')))}, "
            f"about {inr_cr(abs(_g(vg, 'change_vs_excellent_cr')), 1)}, from {inr_cr(_g(ex, 'exec_prp_pool_cr', None), 1)} to "
            f"{inr_cr(_g(vg, 'exec_prp_pool_cr', None), 1)} on FY26 payroll.")
    s2 = (f" The MoU rating drives half the PRP formula (eligibility falls from {num(_g(ex, 'mou_eligibility_pct'))}% to {num(_g(vg, 'mou_eligibility_pct'))}%); "
          f"a further slip to Good would cost {inr_cr(abs(_g(gd, 'change_vs_excellent_cr')), 1)}.")
    s3 = (f" The MoU composite was {f(_g(ex, 'fy26_mou_composite_score', None), 2)} in FY26 and is projected at "
          f"{f(_g(ex, 'fy27_projected_composite_score', None), 2)} for FY27; the estimate assumes FY26 executive PRP outgo is the Excellent-rating pool, "
          f"with team and individual components unchanged.")
    return lead + s2 + s3


def _p14_dd(rows):
    base, vg, red = total(rows, "prp_excellent_basis_cr"), total(rows, "prp_very_good_cr"), total(rows, "reduction_cr")
    big = max(rows, key=lambda r: _g(r, "reduction_cr", 0)) if rows else {}
    lead = (f"The distributable PRP corpus across E1–E9 falls by {pct(abs(_g(rows[0] if rows else {}, 'reduction_pct', None)))} "
            f"between Excellent and Very Good, from {inr_cr(base, 1)} to {inr_cr(vg, 1)} ({inr_cr(red, 1)} less).")
    s2 = (f" The cut is the same percentage in every grade because the MoU component is company-wide; the largest rupee hit is in "
          f"{big.get('grade_id')} ({inr_cr(_g(big, 'reduction_cr', None), 2)}), which has the largest PRP pool.")
    s3 = " Based on FY26 executive PRP outgo in payroll."
    return lead + s2 + s3


def _p14_cmp(rows):
    e5 = _first(rows, lambda r: r.get("grade_id") == "E5")
    e7 = _first(rows, lambda r: r.get("grade_id") == "E7")
    lead = (f"A drop to Very Good would cost an average E5 Manager about {inr(_g(e5, 'loss_per_fte_inr', None))} a year in PRP and an "
            f"E7 General Manager about {inr(_g(e7, 'loss_per_fte_inr', None))}.")
    s2 = (f" Annual PRP per head would fall from {inr(_g(e5, 'prp_per_fte_excellent_inr', None))} to {inr(_g(e5, 'prp_per_fte_very_good_inr', None))} (E5) "
          f"and from {inr(_g(e7, 'prp_per_fte_excellent_inr', None))} to {inr(_g(e7, 'prp_per_fte_very_good_inr', None))} (E7), "
          f"a gap of {inr(_g(e7, 'loss_per_fte_inr', 0) - _g(e5, 'loss_per_fte_inr', 0))} per head between the two grades.")
    s3 = (f" E7 PRP is only {pct(_g(e7, 'prp_pct_of_basic', None))} of basic pay against {pct(_g(e5, 'prp_pct_of_basic', None))} for E5, "
          f"which is why the senior grade's loss is not much larger; figures are FY26 averages per full-time equivalent.")
    return lead + s2 + s3


# ----------------------------------------------------------------------------- P15
def _p15(rows):
    r0 = rows[0] if rows else {}
    met = "Yes" if r0.get("obligation_met") else "No"
    lead = (f"{met}: FY26 CSR spend of {inr_cr(_g(r0, 'fy26_total_spend_cr', None))} was {pct(_g(r0, 'spend_pct_of_obligation', None))} of the "
            f"Section 135 obligation of {inr_cr(_g(r0, 'obligation_2pct_cr', None), 1)} (2% of average FY23–FY25 net profit of "
            f"{inr_cr(_g(r0, 'avg_net_profit_fy23_fy25_cr', None))}).")
    s2 = (f" The top states were {names(rows, 'state_name', 3)}, which together took "
          f"{pct(sum(_g(r, 'share_of_fy26_spend_pct') for r in rows[:3]))} of the spend ({inr_cr(sum(_g(r, 'csr_spend_cr') for r in rows[:3]), 1)}).")
    s3 = (f" Spend was spread across {len(rows)} states; the leader, {r0.get('state_name')}, received {inr_cr(_g(r0, 'csr_spend_cr', None), 1)} "
          f"({pct(_g(r0, 'share_of_fy26_spend_pct', None))}). Net profit uses PBT as a proxy for the Section 198 figure.")
    return lead + s2 + s3


def _p15_dd(rows):
    four = total(rows, "csr_spend_cr")
    tot = _g(rows[0] if rows else {}, "fy26_total_spend_cr", None)
    lead = (f"The four states received {inr_cr(four, 1)} of the {inr_cr(tot)} FY26 CSR spend: "
            + ", ".join(f"{r.get('state_name')} {inr_cr(_g(r, 'csr_spend_cr', None), 1)}" for r in rows) + ".")
    s2 = (f" Together that is {pct(sum(_g(r, 'share_of_fy26_total_pct') for r in rows))} of the total; {rows[0].get('state_name') if rows else 'n/a'} "
          f"alone took {pct(_g(rows[0] if rows else {}, 'share_of_fy26_total_pct', None))}, while the other three received "
          f"{inr_cr(total(rows[1:], 'csr_spend_cr'), 1)} between them despite hosting major producing assets.")
    s3 = f" {rows[0].get('state_name')} spend went to {rows[0].get('csr_themes')}." if rows else ""
    return lead + s2 + s3


def _p15_cmp(rows):
    fy = _first(rows, lambda r: r.get("fiscal_year") == "FY26")
    short = [r for r in rows if _g(r, "surplus_cr") < 0]
    lead = (f"FY26 CSR spend of {inr_cr(_g(fy, 'csr_spend_cr', None))} exceeded the 2% obligation of {inr_cr(_g(fy, 'obligation_2pct_cr', None), 1)} "
            f"by {inr_cr(_g(fy, 'surplus_cr', None), 1)} ({pct(_g(fy, 'spend_pct_of_obligation', None))} of the requirement).")
    s2 = (f" That is the second year in a row above the line, but on the same PBT basis {names(short, 'fiscal_year', 3)} fell short "
          f"(lowest {pct(min((_g(r, 'spend_pct_of_obligation') for r in short), default=None))} of obligation), which conflicts with the "
          f"'mandate met' flag on every CSR project record.") if short else " Spend has been above the requirement in every year shown."
    s3 = " Obligation = 2% of the average of the three preceding years' net profit, using PBT as the proxy."
    return lead + s2 + s3


# ----------------------------------------------------------------------------- P16
def _p16(rows):
    t2 = _first(rows, lambda r: r.get("tier") == 2)
    t3 = _first(rows, lambda r: r.get("tier") == 3)
    t1 = _first(rows, lambda r: r.get("tier") == 1)
    lead = (f"A ₹50 crore drilling contract can be approved by the Functional Director concerned, with Director (Finance) concurrence "
            f"({t2.get('bdp_clause')}: drilling and well-service awards up to ₹50 crore); anything above ₹50 crore goes to the "
            f"{t3.get('approving_authority', 'Executive Committee')} ({t3.get('bdp_clause')}).")
    s2 = (" Because ₹50 crore is exactly the Director ceiling, any variation or price escalation would push the award into EC territory, "
          "and Clause 7.3 forbids splitting it to stay under a limit; a major deepwater rig charter is reserved for the Board regardless (Clause 6.1(b)).")
    above = total([r for r in rows if _g(r, "tier") > 1], "drilling_pos")
    s3 = (f" In practice, {num(_g(t1, 'drilling_pos'))} drilling POs on record ({inr_cr(_g(t1, 'drilling_po_value_cr', None))}) are within the "
          f"Level-3 limit (largest {inr_cr(_g(t1, 'largest_po_cr', None), 2)}) and {num(above)} have needed Director, EC or Board approval.")
    return lead + s2 + s3


# ----------------------------------------------------------------------------- P17
def _p17(rows):
    r = rows[0] if rows else {}
    lead = (f"Yes, but only modestly: FY26 internal accruals after the dividend ({inr_cr(_g(r, 'accruals_after_dividend_cr', None))}) covered "
            f"capex of {inr_cr(_g(r, 'capex_cr', None))} with {inr_cr(_g(r, 'surplus_after_capex_cr', None))} to spare, which is worth at most about "
            f"₹{f(_g(r, 'max_extra_dps_from_surplus_inr', None), 2)} a share more.")
    s2 = (f" The payout is already {pct(_g(r, 'payout_pct_of_pat', None))} of PAT ({inr_cr(_g(r, 'dividend_cr', None))}, ₹{f(_g(r, 'dividend_per_share_inr', None), 2)}/share), "
          f"{inr_cr(_g(r, 'paid_above_floor_cr', None))} above the DIPAM 30%-of-PAT floor, and the Dividend Distribution Policy requires "
          f"future capex plans to be weighed.")
    s3 = (f" Capex is not easing: FY27 Apr–Sep spend was {inr_cr(_g(r, 'fy27_apr_sep_capex_cr', None))} vs {inr_cr(_g(r, 'fy26_apr_sep_capex_cr', None))} "
          f"a year earlier ({signed_pct(_g(r, 'capex_h1_change_pct', None))}). Net worth and debt are not in the data, so the 5%-of-net-worth test and "
          f"leverage cannot be checked.")
    return lead + s2 + s3


def _p17_dd(rows):
    fy = _first(rows, lambda r: r.get("fiscal_year") == "FY26")
    lead = (f"For FY26 the DIPAM minimum on the 30%-of-PAT test is {inr_cr(_g(fy, 'dipam_floor_30pct_pat_cr', None))}; "
            f"ONGC paid {inr_cr(_g(fy, 'actual_dividend_cr', None))}, {inr_cr(_g(fy, 'above_floor_cr', None))} above it ({pct(_g(fy, 'payout_pct_of_pat', None))} of PAT).")
    s2 = (f" The margin over the floor rose from {inr_cr(_g(rows[-1] if rows else {}, 'above_floor_cr', None))} in "
          f"{(rows[-1] if rows else {}).get('fiscal_year')}, so the floor is not the binding constraint.")
    s3 = " The 5%-of-net-worth test cannot be computed because net worth is not in the data, and DIPAM requires the higher of the two."
    return lead + s2 + s3


def _p17_why(rows):
    fy = _first(rows, lambda r: r.get("fiscal_year") == "FY26")
    fy25 = _first(rows, lambda r: r.get("fiscal_year") == "FY25")
    lead = (f"FY26 capex of {inr_cr(_g(fy, 'capex_cr', None))} absorbed {pct(_g(fy, 'capex_pct_of_accruals', None))} of internal accruals "
            f"(PAT + DD&A), leaving a funding surplus of only {inr_cr(_g(fy, 'funding_surplus_cr', None))} after the dividend.")
    s2 = (f" In FY25 capex of {inr_cr(_g(fy25, 'capex_cr', None))} exceeded accruals after dividend by "
          f"{inr_cr(abs(_g(fy25, 'funding_surplus_cr')))}, which shows how quickly a capex spike can turn a higher payout into borrowing.")
    s3 = (f" The surplus has shrunk from {inr_cr(_g(rows[-1] if rows else {}, 'funding_surplus_cr', None))} in "
          f"{(rows[-1] if rows else {}).get('fiscal_year')} as the payout rose to {pct(_g(fy, 'dividend_payout_ratio_pct', None))}; "
          f"debt obligations cannot be quantified because borrowings are not in the data.")
    return lead + s2 + s3


def _p17_cmp(rows):
    fy = _first(rows, lambda r: r.get("fiscal_year") == "FY26")
    first = rows[0] if rows else {}
    lead = (f"The FY26 DPS of ₹{f(_g(fy, 'dividend_per_share_inr', None), 2)} is ₹{f(_g(fy, 'dps_change_inr', None), 2)} "
            f"({signed_pct(_g(fy, 'dps_change_pct', None))}) above FY25 and continues the steady rise from ₹{f(_g(first, 'dividend_per_share_inr', None), 2)} in {first.get('fiscal_year')}.")
    s2 = (f" Profits fell over the same period, so the payout ratio climbed from {pct(_g(first, 'payout_pct_of_pat', None))} to "
          f"{pct(_g(fy, 'payout_pct_of_pat', None))} of PAT, meaning DPS growth is now funded by a rising payout share rather than by earnings.")
    s3 = f" PAT was {inr_cr(_g(fy, 'pat_inr_cr', None))} in FY26 against {inr_cr(_g(first, 'pat_inr_cr', None))} in {first.get('fiscal_year')}."
    return lead + s2 + s3


NARRATIVES = {
    "P11": _p11,
    "P11__drill_down": _p11_dd,
    "P11__compare_or_so_what": _p11_cmp,
    "P12": _p12,
    "P12__drill_down": _p12_dd,
    "P12__compare_or_so_what": _p12_cmp,
    "P13": _p13,
    "P13__drill_down": _p13_dd,
    "P13__compare_or_so_what": _p13_cmp,
    "P14": _p14,
    "P14__drill_down": _p14_dd,
    "P14__compare_or_so_what": _p14_cmp,
    "P15": _p15,
    "P15__drill_down": _p15_dd,
    "P15__compare_or_so_what": _p15_cmp,
    "P16": _p16,
    "P17": _p17,
    "P17__drill_down": _p17_dd,
    "P17__why": _p17_why,
    "P17__compare_or_so_what": _p17_cmp,
}
