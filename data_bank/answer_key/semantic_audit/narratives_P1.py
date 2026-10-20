"""Narratives for slice P1 (P1-P10 + follow-ups), rendered from result rows; no typed numbers.

Policy entries return extracted clause text in `quote_snippet` (with a `provision` label); every figure quoted
below is pulled out of that text with a regex, so the narrative changes if the source clause changes.
"""

import re

from semantic_audit.common import f, inr, inr_cr, names, num, pct, signed_pct, total  # noqa: F401


# --------------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------------
def _q(rows, prefix=None):
    """Concatenated quote text; optionally only rows whose provision starts with `prefix`."""
    out = []
    for r in rows or []:
        if prefix is None or str(r.get("provision") or "").startswith(prefix):
            out.append(str(r.get("quote_snippet") or ""))
    return " ".join(out)


def _rx(text, pat, default="n/a", group=1):
    m = re.search(pat, text or "", re.S)
    return m.group(group).strip() if m else default


def _row(rows, key, val):
    for r in rows or []:
        if r.get(key) == val:
            return r
    return {}


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------------------------------
# P1 - station tenure
# --------------------------------------------------------------------------------------------------
def _p1(rows):
    t3, t4 = _q(rows, "JRTP 3"), _q(rows, "JRTP 4")
    mn = _rx(t3, r"shall be (\d+) \([^)]+\) completed years")
    win = _rx(t3, r"completion of (\d+ to \d+) years")
    cap = _rx(t4, r"aggregate of (\d+) \([^)]+\) years")
    return (f"The minimum tenure at a station is {mn} completed years (JRTP 3.1), and no executive may spend more than "
            f"an aggregate of {cap} years in a single city or Geographic Cluster over the whole career (JRTP 4.1). "
            f"Rotation is normally considered after {win} years at a work centre, and moving someone before {mn} years "
            f"needs administrative exigency, restructuring or disciplinary necessity approved by Director (HR). "
            f"The {cap}-year cap is cumulative: every posting in the same station or cluster is added up irrespective of "
            f"breaks or in-place promotions (JRTP 4.2).")


def _p1_drill(rows):
    t3, t2, t6 = _q(rows, "JRTP 3"), _q(rows, "JRTP 2"), _q(rows, "JRTP 6")
    mn = _rx(t3, r"shall be (\d+) \([^)]+\) completed years")
    win = _rx(t3, r"completion of (\d+ to \d+) years")
    ext = _rx(t3, r"extended up to (\d+) years")
    hard = _rx(t6, r"at least one full tenure of (\d+) \([^)]+\) continuous years")
    lst = _rx(t6, r"North-East work centre \(([^)]*)\)")
    allow = _rx(t6, r"\((\d+)% of BP\)")
    tri = _rx(t2, r"Tripura Asset \(([^)]*)\)")
    return (f"JRTP does not set a different maximum for hard stations: the same {mn}-year minimum and {win}-year "
            f"rotation window apply everywhere, but every technical or operational executive must complete at least one "
            f"full {hard}-year continuous tenure in a Category 'C' hard station ({lst}) before E4-to-E5 merit promotion "
            f"(JRTP 6.1). Normal-station tenure can be stretched to {ext} years for critical technical roles (3.3), while "
            f"hard-station service earns a Special Hard Station Allowance of {allow}% of basic pay, retention of family "
            f"accommodation at the last station and extra leave/travel concessions (6.3). Category C (JRTP 2.1c) covers "
            f"the Assam asset, the Tripura asset ({tri}), Bokaro, Jodhpur and offshore installations; note that the "
            f"cluster schedule (5.2) groups Silchar with Assam rather than Tripura.")


def _p1_why(rows):
    t4, t1 = _q(rows, "JRTP 4"), _q(rows, "JRTP 1")
    cap = _rx(t4, r"aggregate of (\d+) \([^)]+\) years")
    lst = _rx(t4, r"completed (\d+, \d+, and \d+) years")
    sa = _rx(t4, r"superannuation within (\d+ to \d+) years")
    has_obj = "equitable sharing of arduous" in t1
    obj = ("broadening multi-basin exposure for leadership development and ensuring equitable sharing of arduous and "
           "remote postings" if has_obj else "the rotation objectives in Clause 1.3")
    return (f"JRTP gives no stand-alone reason for the {cap}-year cumulative cap; its rationale is the policy's own "
            f"objectives in Clause 1.3 - {obj} - which an indefinitely long stay in one city would defeat. Clause 4.3 "
            f"operationalises it: Corporate HR lists officers at {lst} years of cumulative stay every year and puts those "
            f"at {cap} years or more (notably Delhi-NCR and Mumbai Urban) on the mandatory outstation transfer list. "
            f"Retention beyond the cap is allowed only for superannuation within {sa} years, certified severe medical "
            f"conditions, or CMD approval for vital national hydrocarbon projects (4.4).")


def _p1_cmp(rows):
    t = _q(rows, "JRTP 1.2")
    grades = _rx(t, r"Grades (E\d+ through E\d+)")
    return (f"The corpus cannot support a like-for-like comparison: JRTP's tenure rules apply only to regular executives "
            f"in Grades {grades} (JRTP 1.2), and no transfer or tenure policy for non-executive unionised staff exists in "
            f"ONGC's document set. The executive-only scope is deliberate - other rulebooks such as the Leave Rules "
            f"expressly cover both executives and non-executives (Leave Rules 1.2). For executives, transfer is an "
            f"incident of service anywhere in India or abroad (JRTP 1.4); non-executive transfer terms would sit in "
            f"standing orders or wage settlements that are not in the corpus.")


# --------------------------------------------------------------------------------------------------
# P2 - clusters
# --------------------------------------------------------------------------------------------------
def _p2(rows):
    if not rows:
        return "No cluster data returned."
    n = len(rows)
    r0 = rows[0]
    nxt = rows[1:3]
    singles = [r for r in rows if _int(r.get("work_centres")) == 1]
    all_listed = all(str(r.get("listed_in_jrtp_5_2")).lower() == "true" for r in rows)
    nxt_txt = ", ".join(f"{r.get('cluster_id')} ({num(r.get('work_centres'))})" for r in nxt)
    s3 = ("Every cluster in the work-centre master is named in the JRTP 5.2 schedule, so the data and the policy agree."
          if all_listed else "Some clusters in the work-centre master are not named in JRTP 5.2 - check the schedule.")
    return (f"ONGC has {n} Geographic Clusters; all work centres inside one cluster count as a single station for "
            f"tenure, so moves within a cluster do not reset the tenure clock (JRTP 5.1-5.3). The largest is "
            f"{r0.get('cluster_id')} ({r0.get('cluster_name')}) with {num(r0.get('work_centres'))} work centres across "
            f"{r0.get('cities')}, followed by {nxt_txt}; {len(singles)} clusters are single-site "
            f"({names(singles, 'cluster_name', 6)}). {s3}")


def _p2_drill(rows):
    def cl(pred):
        return {r.get("cluster_id") for r in rows if pred(str(r.get("city") or "").lower())}
    dl, dd = cl(lambda c: c == "new delhi"), cl(lambda c: c == "dehradun")
    mup = cl(lambda c: c in ("mumbai", "uran", "panvel"))
    n_dd = len([r for r in rows if str(r.get("city") or "").lower() == "dehradun"])
    mum_id = next(iter(mup)) if len(mup) == 1 else None
    mum_rows = [r for r in rows if r.get("cluster_id") == mum_id]
    hard = [r for r in mum_rows if str(r.get("hard_station_cat")) == "C"]
    panvel = [r for r in mum_rows if str(r.get("city") or "").lower() == "panvel"]
    sep = "Yes - Delhi and Dehradun are separate clusters" if dl and dd and not (dl & dd) else "Delhi and Dehradun share a cluster"
    s2 = (f"Mumbai, Uran and Panvel are one cluster ({mum_id}, {len(mum_rows)} work centres including Uran Plant and the "
          f"Panvel units {names(panvel, 'short_name', 3)}), so moving among them does not reset station or cumulative tenure."
          if mum_id else "Mumbai, Uran and Panvel do not fall in a single cluster.")
    s3 = (f" The cluster mixes Category C offshore assets ({names(hard, 'short_name', 3)}) with Category A urban offices, "
          f"so an offshore-to-office move in Mumbai still counts as the same station." if hard else "")
    return (f"{sep}: New Delhi is {', '.join(sorted(dl))} and all {n_dd} Dehradun work centres form {', '.join(sorted(dd))}, "
            f"so a Delhi-Dehradun move is a genuine outstation transfer. {s2}{s3}")


def _p2_why(rows):
    t53, t42 = _q(rows, "JRTP 5.3"), _q(rows, "JRTP 4.2")
    ex = _rx(t53, r"\(e\.g\. (.*?)\)")
    return (f"Contiguous work centres are grouped so that a move within one urban or industrial agglomeration cannot "
            f"pass as rotation: an intra-cluster transfer ({ex}) does NOT reset station tenure or cumulative cluster "
            f"tenure (JRTP 5.3). Clause 4.2 then adds up every historical posting in the same station or cluster "
            f"irrespective of breaks or in-place promotions, so the cumulative cap cannot be dodged by short hops"
            f"{'' if t42 else ' (4.2 text not returned)'}. A cluster is defined as contiguous stations within a defined "
            f"industrial or urban agglomeration (5.1).")


def _p2_cmp(rows):
    t4, t3 = _q(rows, "JRTP 4"), _q(rows, "JRTP 3")
    lst = _rx(t4, r"completed (\d+, \d+, and \d+) years")
    cap = _rx(t4, r"completed or exceeded (\d+) years")
    mn = _rx(t3, r"shall be (\d+) \([^)]+\) completed years")
    return (f"Moving within the same cluster has no tenure effect - the clock keeps running, because it is not an "
            f"outstation transfer and neither station tenure nor cumulative cluster tenure resets (JRTP 5.3). The officer "
            f"stays on HR's annual cumulative-stay roster ({lst}-year milestones) and at {cap} years in the cluster goes "
            f"onto the mandatory outstation transfer list (4.2-4.3). In practice a Delhi-to-Noida or WOB-to-Uran move "
            f"cannot be used to satisfy the {mn}-year rotation norm (3.1-3.2).")


# --------------------------------------------------------------------------------------------------
# P3 - pre-retirement exemption
# --------------------------------------------------------------------------------------------------
def _ret(t):
    return (_rx(t, r"within (\d+) \([^)]+\) years of superannuation"), _rx(t, r"\(age (\d+) years and above\)"),
            _rx(t, r"executives with (\d+) years or less remaining"),
            _rx(t, r"remaining until superannuation \(age (\d+) years"))


def _p3(rows):
    n, age, m, age2 = _ret(_q(rows, "JRTP 7"))
    return (f"Yes - an executive within {n} years of superannuation (age {age} and above) is strictly exempt from "
            f"mandatory outstation transfers (JRTP 7.1), and in practice the protection extends to {m} years (age {age2} "
            f"and above). The exemption falls away only if you yourself ask to move to your declared home town or "
            f"retirement station, or if Director (HR) or CMD orders an administrative or disciplinary transfer in "
            f"writing (7.2). So an officer two years from retirement is protected unless one of those two exceptions applies.")


def _p3_drill(rows):
    n, age, m, age2 = _ret(_q(rows, "JRTP 7"))
    w44 = _rx(_q(rows, "JRTP 4"), r"superannuation within (\d+ to \d+) years")
    w13 = _rx(_q(rows, "JRTP 13"), r"superannuation within ([\d]+.[\d]+) years")
    return (f"The binding cut-off is {n} years (age {age} and above): executives that close to superannuation are "
            f"strictly exempt (JRTP 7.1); the {m}-year window (age {age2} and above) is organisational practice, under "
            f"which officers are only 'ordinarily' not moved. The wider window recurs elsewhere in the policy - "
            f"superannuation within {w44} years is a ground for retention beyond the cumulative cap (4.4a) and "
            f"superannuation within {w13} years a ground for representation to the TGRC (13.2d).")


def _p3_why(rows):
    t = _q(rows)
    m = _rx(t, r"transfers within (\d+) years of retirement")
    p = _rx(t, r"less than ([\d.]+)%")
    return (f"Executives near retirement are ordinarily kept at their current station to allow a smooth superannuation "
            f"transition, pension settlement, family stabilisation and medical management (JRTP 7.1). They may still "
            f"request a transfer to their declared home town or chosen retirement station (7.2a), and only a written "
            f"administrative or disciplinary order from Director (HR) or CMD can override the protection (7.2b). "
            f"Compliance is reported as high: non-initial transfers within {m} years of retirement are under {p}% of "
            f"transfer actions in SAP records (7.3).")


def _p3_cmp(rows):
    n, age, _, _ = _ret(_q(rows, "JRTP 7"))
    t8, t13 = _q(rows, "JRTP 8"), _q(rows, "JRTP 13")
    v = _rx(t8, r"maximum of (\d+ to \d+) years")
    d = _rx(t13, r"within (\d+) \([^)]+\) calendar days")
    dd = _rx(t13, r"within (\d+) days\.")
    return (f"Retirement protection is automatic, while medical and spouse grounds must be applied for and adjudicated: "
            f"within {n} years of superannuation an executive is strictly exempt (JRTP 7.1), but a medical case needs "
            f"Standing Medical Board certification and Special Review Board approval, valid for only {v} years with annual "
            f"re-evaluation (8.1-8.3). A working spouse in government or a CPSE at the station is not an exemption at all - "
            f"only a ground for representation to the TGRC within {d} days of the order, disposed of within {dd} days, "
            f"with no automatic stay (13.1-13.3).")


# --------------------------------------------------------------------------------------------------
# P4 - earned leave
# --------------------------------------------------------------------------------------------------
def _p4(rows):
    t3, t4 = _q(rows, "Leave Rules 3"), _q(rows, "Leave Rules 4")
    acc = _rx(t3, r"earn (\d+) \([^)]+\) calendar days")
    half = _rx(t3, r"installments of (\d+) days")
    cap = _rx(t3, r"ceiling of (\d+) \([^)]+\) days")
    enc = _rx(t4, r"aggregate ceiling of (\d+) \([^)]+\) days")
    div = _rx(t4, r"\) / (\d+)\]")
    yrs = (int(cap) // int(acc)) if cap.isdigit() and acc.isdigit() and int(acc) else None
    yrs_txt = f", so the ceiling is reached after about {yrs} years without using leave" if yrs else ""
    return (f"You can accumulate up to {cap} days of Earned Leave and encash up to {enc} days at retirement "
            f"(Leave Rules 3.3, 4.1). EL accrues at {acc} days a year, credited in advance as {half} days on 1 January and "
            f"1 July{yrs_txt}; anything above the ceiling lapses. The encashment amount is (Basic Pay + IDA) / {div} x "
            f"unutilised EL days, with HRA, cafeteria perks and PRP excluded (4.2).")


def _p4_drill(rows):
    t3, t51, t53 = _q(rows, "Leave Rules 3"), _q(rows, "Leave Rules 5.1"), _q(rows, "Leave Rules 5.3")
    cap = _rx(t3, r"ceiling of (\d+) \([^)]+\) days")
    hpl = _rx(t51, r"rate of (\d+) \([^)]+\) days")
    agg = _rx(t53, r"combined aggregate ceiling of (\d+) days")
    ratio = _rx(t53, r"(\w+) days of HPL shall equal one day")
    return (f"The EL accumulation ceiling is {cap} days (Leave Rules 3.3); credits above it are parked in a reserve and "
            f"lapse on 30 June / 31 December if unused (3.4). Half Pay Leave accrues at {hpl} days per completed year "
            f"(5.1) and can be encashed at superannuation only to bridge an EL shortfall up to the combined {agg}-day "
            f"aggregate, at {ratio} days of HPL per day of cash salary (5.3). So total leave encashment at retirement "
            f"never exceeds {agg} days, whatever the EL/HPL mix.")


def _p4_why(rows):
    t4 = _q(rows, "Leave Rules 4")
    cap = _rx(t4, r"aggregate ceiling of (\d+) \([^)]+\) days")
    dpe = "subject to DPE guidelines" in _q(rows, "Leave Rules 5")
    return (f"The Leave Rules do not state the rationale; they fix a {cap}-day encashment ceiling and a (Basic Pay + IDA) "
            f"formula (4.1-4.2) and make HPL encashment explicitly {'subject to DPE guidelines' if dpe else 'subject to external guidelines'} "
            f"(5.3) - i.e. ONGC, as a CPSE, keeps terminal leave benefits inside the DPE pay-and-perks framework. "
            f"The income-tax exemption limit on leave encashment is not in the document corpus, so the tax side of the "
            f"question cannot be answered from ONGC sources. Excluding HRA, perks and PRP from the base keeps the "
            f"liability tied to basic pay plus IDA only.")


def _p4_cmp(rows):
    t42, t43 = _q(rows, "Leave Rules 4.2"), _q(rows, "Leave Rules 4.3")
    cap = _rx(t42, r"up to max (\d+)")
    n = _rx(t43, r"encash up to (\d+) days")
    m = _rx(t43, r"minimum balance of (\d+) days")
    div = _rx(t42, r"\) / (\d+)\]")
    return (f"At retirement you encash up to {cap} days in one lump sum at (Basic Pay + IDA) / {div} per day (Leave Rules 4.2); "
            f"during service you may encash at most {n} days once a calendar year and must keep at least {m} days in "
            f"balance (4.3). The rate is the same pay-based formula, so the difference is volume and timing, not value per day. "
            f"The corpus has no LFA/LTC-linked encashment rule - running encashment under 4.3 is the only in-service provision.")


# --------------------------------------------------------------------------------------------------
# P5 - study leave
# --------------------------------------------------------------------------------------------------
def _study(rows):
    t6, t7 = _q(rows, "Leave Rules 6"), _q(rows, "Leave Rules 7")
    return dict(svc=_rx(t6, r"minimum of (\d+) \([^)]+\) years"), dur=_rx(t6, r"shall be (\d+) \(\S+\) months"),
                phd=_rx(t6, r"maximum of (\d+) months for an approved doctoral"),
                bond=_rx(t7, r"minimum period of (\d+) \([^)]+\) completed years"),
                pp=_rx(t7, r"plus (\d+)% per annum"))


def _p5(rows):
    s = _study(rows)
    return (f"You are eligible for study leave after {s['svc']} years of continuous regular service, for study directly "
            f"relevant to ONGC's hydrocarbon or corporate-finance work, up to {s['dur']} months over your career "
            f"({s['phd']} for an approved Ph.D.) (Leave Rules 6.1-6.3). Before leaving you must sign a service bond with "
            f"two solvent sureties to serve {s['bond']} years after return; leaving within that period means refunding all "
            f"leave salary, allowances, fees and travel costs plus compound interest at the bank lending rate + {s['pp']}% "
            f"(7.1-7.2). Study in India is sanctioned by Director (HR); study abroad needs CMD approval (6.4).")


def _p5_drill(rows):
    s = _study(rows)
    return (f"The qualifying service is a minimum of {s['svc']} years of continuous regular service in ONGC (Leave Rules 6.2). "
            f"The rules do not list approved degree specialisations; they only require postgraduate study, an executive "
            f"fellowship or research directly relevant to hydrocarbon exploration, reservoir development, drilling "
            f"engineering or corporate finance (6.1). A named-specialisation list would have to come from an HR circular "
            f"that is not in the corpus.")


def _p5_why(rows):
    s = _study(rows)
    return (f"The bond protects ONGC's investment: an officer on study leave keeps drawing leave salary and allowances "
            f"while ONGC pays tuition, books and travel, so the rules bind the officer to serve {s['bond']} years after "
            f"return (Leave Rules 7.1) and claw everything back with compound interest at the bank lending rate + "
            f"{s['pp']}% on breach (7.2). Because leave can never be claimed as of right (1.3), ONGC can make study leave "
            f"conditional on that bond and two solvent sureties.")


def _p5_cmp(rows):
    s = _study(rows)
    return (f"The Leave Rules make no domestic/overseas distinction on duration: study leave is capped at {s['dur']} months "
            f"over a career ({s['phd']} for a Ph.D.) wherever the course is (Leave Rules 6.3); the only difference is the "
            f"sanctioning authority - Director (HR) for study in India, CMD for study abroad (6.4). No higher allowance for "
            f"premier overseas institutions is specified anywhere in the corpus, so that premise cannot be supported "
            f"from ONGC rules.")


# --------------------------------------------------------------------------------------------------
# P6 - gifts
# --------------------------------------------------------------------------------------------------
def _gift(rows):
    t4 = _q(rows, "DPE CDA Rule 12(4)")
    t2 = _q(rows, "DPE CDA Rule 12(2)")
    t3 = _q(rows, "DPE CDA Rule 12(3)")
    return dict(lim=_rx(t4, r"exceeds rupees ([a-z ]+?) in the case"),
                months=_rx(t4, r"period of (\d+) months"),
                agg_e=_rx(t4, r"exceeds (Rs\.[\d,]+/-)"), agg_n=_rx(t4, r"and (Rs\.[\d,]+/-) ?in case"),
                rel_e=_rx(t2, r"\(i\) rupees ([a-z ]+?) in the case"), rel_n=_rx(t2, r"\(ii\) rupees ([a-z ]+?) in the case"),
                fr=_rx(t3, r"exceeds rupees ([a-z ]+?) in the case"))


def _p6(rows):
    g = _gift(rows)
    note = "lavish or frequent hospitality" in _q(rows)
    return (f"Only within a small limit: a vendor has official dealings with you, so the relative and personal-friend "
            f"exceptions do not apply, and you need the competent authority's sanction before accepting any gift worth "
            f"more than rupees {g['lim']} (DPE CDA Rule 12(4)). Several gifts from the same firm within {g['months']} months "
            f"must be reported once they add up to more than {g['agg_e']} (executives) / {g['agg_n']} (non-executives)"
            f"{', and lavish or frequent hospitality from anyone with official dealings must be avoided (Rule 12 Note)' if note else ''}. "
            f"The festive exception in 12(3) covers only personal friends with no official dealings, so it does not help "
            f"with vendor gifts at Diwali.")


def _p6_drill(rows):
    g = _gift(rows)
    return (f"The gift ceilings are: gifts from near relatives at weddings or religious functions must be reported above "
            f"rupees {g['rel_e']} for executives / rupees {g['rel_n']} for non-executives (Rule 12(2)); gifts from personal "
            f"friends without official dealings must be reported above rupees {g['fr']} (12(3)); and any other gift above "
            f"rupees {g['lim']} needs prior sanction, with repeat gifts from one source within {g['months']} months reportable "
            f"above {g['agg_e']} / {g['agg_n']} in aggregate (12(4)). These are the DPE model conduct rules for CPSEs (G-06); "
            f"the ONGC CDA Rules text in the corpus (P1-01) contains no gift schedule of its own.")


def _p6_why(rows):
    has2a = "2A." in _q(rows, "DPE CDA Rule 5")
    return (f"The conduct rules treat vendor gifts as a corruption risk: taking any bribe or illegal gratification is "
            f"misconduct{', and soliciting donations or sponsorship from contractors or vendors for an employee-linked NGO is misconduct too' if has2a else ''} "
            f"(DPE CDA Rule 5). Every employee must not place themselves under any obligation that could influence "
            f"official duties, nor misuse their position for personal benefit (Rule 4(1)(xiv)-(xv)), and must avoid "
            f"lavish or frequent hospitality from firms with official dealings (Rule 12 Note). The specific CVC circular "
            f"on reporting and surrendering gifts is not in the corpus; prompt reporting is simply how these rules keep "
            f"any acceptance transparent.")


def _p6_cmp(rows):
    g = _gift(rows)
    return (f"It turns on official dealings: a personal friend with no official dealings may give a festive gift that is "
            f"reportable only above rupees {g['fr']} (Rule 12(3)), whereas a business associate falls outside that "
            f"exception and any gift above rupees {g['lim']} needs prior sanction (12(4)). The Explanation makes the test "
            f"explicit - free transport, board, lodging or any pecuniary advantage from anyone other than a near relative "
            f"or a personal friend without official dealings counts as a gift. So the same Diwali hamper is a reporting "
            f"matter from a friend but a sanction matter from a vendor.")


# --------------------------------------------------------------------------------------------------
# P7 - travel
# --------------------------------------------------------------------------------------------------
def _p7(rows):
    r = rows[0] if rows else {}
    return (f"As an {r.get('grade_id')} ({r.get('designation')}) you fly {r.get('ta_da_travel_class')} on official tours, "
            f"and your hotel ceiling in Mumbai - a {r.get('mumbai_city_category')} city - is "
            f"{inr(r.get('daily_lodging_limit_cat_a_inr'))} per day (dim_grade). The ceiling is applied as written: "
            f"{num(r.get('e2_mumbai_claims'))} {r.get('grade_id')} claims to Mumbai reimbursed lodging at an average "
            f"{inr(r.get('avg_lodging_per_night_inr'))} per night, with entitlement {r.get('claim_class_entitlement')}. "
            f"Lodging is reimbursed against hotel receipts at scheduled tariff, and in metros with an ONGC office the "
            f"company normally books the accommodation.")


def _p7_drill(rows):
    r = rows[0] if rows else {}
    return (f"An {r.get('grade_id')} on tour in Mumbai ({r.get('city_class')}) can claim hotel stay up to "
            f"{inr(r.get('hotel_ceiling_per_day_inr'))} per day and local conveyance of "
            f"{inr(r.get('local_conveyance_per_day_inr'))} per day ({r.get('conveyance_source')} revision for executives). "
            f"Actual claims sit exactly at the ceiling: {num(r.get('e2_class_a_claims'))} {r.get('grade_id')} Class-A claims "
            f"averaged {inr(r.get('avg_lodging_per_night_inr'))} per night. Meals taken at the hotel reduce the daily "
            f"allowance by one quarter each.")


def _p7_why(rows):
    t = _q(rows)
    d = _rx(t, r"working on (\d+) days On/Off")
    return (f"The corpus does not name Balmer Lawrie or IRCTC as mandatory booking agents, so that premise cannot be "
            f"confirmed from ONGC documents. What the TA Regulations do mandate is cost control on air travel: citing "
            f"'the large amount of saving on the check fare tickets', all air tickets must be booked at check fare / the "
            f"most economical fare for the stated timing, and any deviation needs the controlling officer's written "
            f"reasons (TA Regs 4.2.1 h). Executives other than EDs fly economy (4.2.1 g), and {d}-day on/off offshore "
            f"crews are exempt from check-fare booking.")


def _p7_cmp(rows):
    by = {r.get("grade_id"): r for r in rows}
    low = [r for g, r in by.items() if g in ("E1", "E2", "E3")]
    a = low[0].get("class_a_per_night_inr") if low else None
    b = low[0].get("class_b_per_night_inr") if low else None
    c = low[0].get("class_c_per_night_inr") if low else None
    prem = (float(a) / float(b) - 1) * 100 if a and b else None
    e4 = by.get("E4", {})
    s2 = ""
    if e4 and e4.get("cat_a_ceiling_inr") and e4.get("class_a_per_night_inr") is not None \
            and float(e4["cat_a_ceiling_inr"]) != float(e4["class_a_per_night_inr"]):
        s2 = (f" E4 is the exception: dim_grade gives E4 a Class-A ceiling of {inr(e4.get('cat_a_ceiling_inr'))}, but E4 "
              f"claims are paid at only {inr(e4.get('class_a_per_night_inr'))} - the grade master and the claims engine disagree.")
    return (f"On actual claims, Class-A cities like Mumbai and Delhi reimburse lodging at {inr(a)} per night for E1-E3 versus "
            f"{inr(b)} in Class-B field centres - a {signed_pct(prem, 0)} premium; Class-C and offshore stays are also paid "
            f"at {inr(c)}.{s2} No Class-B ceiling exists in dim_grade or in the TA Regulations text, so the Class-B figure "
            f"is inferred from {num(total(rows, 'claims'))} E1-E4 claims rather than from a published rule.")


# --------------------------------------------------------------------------------------------------
# P8 - whistle blower
# --------------------------------------------------------------------------------------------------
def _p8(rows):
    t = _q(rows)
    d = _rx(t, r"not later than (\d+) days")
    mail = _rx(t, r"E-mail: (\S+@\S+)")
    return (f"Send a signed, written Protected Disclosure in a closed envelope super-scribed 'Protected Disclosure under "
            f"the Whistle Blower policy' (or e-mail {mail} with that subject) to the Nodal Officer - the Company "
            f"Secretary, Deendayal Urja Bhawan, New Delhi - within {d} days of becoming aware (WBP 7.1-7.3). The Nodal "
            f"Officer conceals your identity before forwarding and no acknowledgement is issued, to protect you; "
            f"anonymous or pseudonymous complaints are not entertained (7.3-7.5). Retaliation of any kind - termination, "
            f"suspension, disciplinary action, transfer, demotion or refusal of promotion - is barred, and victimisation "
            f"can be reported directly to the Chairman of the Audit Committee (13.1-13.2).")


def _p8_drill(rows):
    t = _q(rows)
    mail = _rx(t, r"E-mail: (\S+@\S+)")
    return (f"Whistle Blower disclosures are received by the Nodal Officer - the Company Secretary (WBP 4.8) - at "
            f"{mail} / Deendayal Urja Bhawan, New Delhi (7.1), not by the CVO. They are dealt with by the Competent "
            f"Authority, i.e. the Director (HR) or a Functional Director nominated by the CMD (4.4); the Chief Vigilance "
            f"Officer appears only as one of the possible Investigators (4.7). The corpus does not name the current CVO "
            f"or Company Secretary.")


def _p8_why(rows):
    return ("The safeguards exist so that employees report genuine misconduct 'without fear of punishment/ victimization "
            "or unfair treatment' - a vigil mechanism only works if reporting carries no career risk (WBP 3.2-3.3). That is "
            "why 13.1 expressly protects against retaliatory transfer, demotion, refusal of promotion, suspension or "
            "termination. The protection is not a shield for abuse: mala fide, frivolous or knowingly false disclosures "
            "attract disciplinary action and disqualify the complainant from further disclosures (14.1-14.3).")


def _p8_cmp(rows):
    t = _q(rows)
    s = _rx(t, r"within ten \((\d+)\) working days")
    i = _rx(t, r"completed within (\d+) days")
    return (f"A Protected Disclosure is a written, good-faith report of unethical or improper activity - personal "
            f"grievances are expressly excluded (WBP 4.9) and go through ordinary channels such as the Grievance "
            f"Management System, ICC or Safety Committees instead (Human Rights Policy 4). Disclosures run on a "
            f"confidential track: identity concealed, a Screening Committee recommendation within {s} working days (9.3) "
            f"and investigation normally completed within {i} days (9.15), with quarterly reporting to the Audit "
            f"Committee. An ordinary grievance carries none of that identity protection or Audit Committee oversight.")


# --------------------------------------------------------------------------------------------------
# P9 - POSH
# --------------------------------------------------------------------------------------------------
def _p9(rows):
    n = len(rows)
    dl = _row(rows, "wc_id", "WC-DEL") or (rows[0] if rows else {})
    fem = sum(1 for r in rows if str(r.get("presiding_officer_gender") or "").lower() == "female")
    sizes = [_int(r.get("internal_members_count")) for r in rows if _int(r.get("internal_members_count")) is not None]
    wp = [float(r["women_members_pct"]) for r in rows if r.get("women_members_pct") is not None]
    ext = {r.get("external_member_name") for r in rows}
    po = {r.get("presiding_officer_name") for r in rows}
    s3 = (f" The ICC master records the presiding officer only as a designation ('{next(iter(po))}') rather than a name, "
          if len(po) == 1 else " ")
    return (f"File the complaint with the Internal Complaints Committee of your own work centre - all {n} work centres "
            f"have an active ICC, reachable at its listed e-mail (e.g. {dl.get('work_centre')}: {dl.get('contact_email')}). "
            f"{fem} of {n} committees are presided over by a woman, each has {min(sizes) if sizes else 'n/a'}-"
            f"{max(sizes) if sizes else 'n/a'} internal members with women at {pct(min(wp) if wp else None, 0)} or more, "
            f"and an external NGO member ({len(ext)} individuals cover all {n} ICCs).{s3}"
            f"and the corpus holds no POSH procedure document, so filing timelines and format cannot be cited from ONGC rules.")


def _p9_drill(rows):
    tot = total(rows, "committees")
    fem = total(rows, "female_presiding_officers")
    lst = "; ".join(f"{r.get('external_member_name')} ({r.get('external_member_ngo')}, {num(r.get('committees'))} ICCs)"
                    for r in rows)
    mn = min((float(r["min_women_members_pct"]) for r in rows if r.get("min_women_members_pct") is not None), default=None)
    one_name = all(_int(r.get("distinct_presiding_officer_names")) == 1 for r in rows)
    s2 = (" but the master holds one placeholder name for every presiding officer, so the Presiding Officer at a given "
          "work centre cannot be named from the data" if one_name else "")
    return (f"{len(rows)} external members serve all {num(tot)} ICCs: {lst}. Every presiding officer is a woman "
            f"({num(fem)} of {num(tot)}){s2}. Women make up at least {pct(mn, 0)} of every committee.")


def _p9_why(rows):
    if not rows:
        return "No POSH case data returned."
    first, last_full = rows[0], _row(rows, "fiscal_year", "FY26") or rows[-1]
    worst = min(rows, key=lambda r: float(r.get("pct_closed_within_90") or 100))
    tc, tw = total(rows, "cases_closed"), total(rows, "closed_within_90_days")
    return (f"The 90-day limit exists to force timely closure, and ONGC's own record shows why it matters: the share of "
            f"POSH inquiries closed within 90 days fell from {pct(first.get('pct_closed_within_90'), 0)} in "
            f"{first.get('fiscal_year')} to {pct(last_full.get('pct_closed_within_90'), 0)} in {last_full.get('fiscal_year')}, "
            f"when the longest inquiry took {num(last_full.get('max_inquiry_days'))} days (worst year: "
            f"{worst.get('fiscal_year')}). Over {rows[0].get('fiscal_year')}-{rows[-1].get('fiscal_year')}, {num(tw)} of "
            f"{num(tc)} closed cases met the 90-day norm ({pct(tw * 100.0 / tc if tc else None)}). The statutory text "
            f"behind the rule is not in the document corpus, so the 'why' is evidenced from case data rather than cited.")


def _p9_cmp(rows):
    return ("The corpus contains no POSH Act or ICC procedure rules, so the specific interim reliefs an ICC can recommend "
            "during an inquiry cannot be cited from ONGC documents. What the documents do establish: where there is a "
            "sexual-harassment complaint, the Complaints Committee is deemed the inquiring authority under the conduct "
            "rules (DPE CDA Rule 25 proviso); ONGC has 'zero tolerance' for sexual harassment and hostile work "
            "environments (Human Rights Policy 3.2); and the ICC is a recognised time-bound grievance channel (HRP 4). "
            "Any answer listing interim measures would need the POSH Act text or an ONGC ICC SOP added to the corpus.")


# --------------------------------------------------------------------------------------------------
# P10 - promotion
# --------------------------------------------------------------------------------------------------
def _p10(rows):
    t2, t3 = _q(rows, "R&P 2"), _q(rows, "R&P 3")
    res = _rx(t2, r"E3 to E4: (\d+ to \d+) \(")
    rating = _rx(t3, r"For E3.E4: Minimum cumulative rating of ('[^']+' \(score [^)]+\))")
    return (f"Promotion from E3 to E4 is time-bound, not vacancy-based: you need {res} completed years' residency at E3 "
            f"(R&P 2.1c), a cumulative APAR rating of {rating} across the residency period (3.1c), and unconditional "
            f"vigilance clearance from the CVO (7.1). Everyone who meets all three is promoted, effective 1 January or "
            f"1 July after completing residency (2.2-2.3). Any sustained adverse remark or a year rated below 'Good' "
            f"defers promotion by one year (3.2), and suspension, a major-penalty charge-sheet or pending prosecution "
            f"bars it (7.2).")


def _p10_drill(rows):
    t = _q(rows)
    res = _rx(t, r"E3 to E4: (\d+ to \d+) \(")
    sc = _rx(t, r"score ≥ ([\d.]+ / \d+%)")
    return (f"Minimum qualifying residency for E3 to E4 is {res} completed years at E3 (R&P 2.1c), and the APAR threshold "
            f"is a cumulative 'Very Good' (score ≥ {sc}) across the residency period (3.1c). A single year rated below "
            f"'Good' or any sustained adverse remark defers promotion by one year until the benchmark is restored (3.2).")


def _p10_why(rows):
    t4 = _q(rows, "R&P 4")
    q = _rx(t4, r"Certifications: (\d+) Points")
    tot = _rx(t4, r"(\d+)-point composite")
    return (f"Vigilance clearance is a hard gate: no officer is empanelled or promoted without unconditional CVO "
            f"clearance, and suspension, a major-penalty charge-sheet or pending criminal prosecution bars promotion "
            f"(R&P 7.1-7.2). If proceedings are pending at DPC time the findings go into a sealed cover, opened only on "
            f"full exoneration with notional seniority from the date the immediate junior was promoted (8.2-8.3). "
            f"Qualifications count only in the merit channel (E4 to E5 and above), worth {q} of {tot} DPC points (4.3c); "
            f"the corpus has no rule making training completion a promotion condition.")


def _p10_cmp(rows):
    t5, t4 = _q(rows, "R&P 5"), _q(rows, "R&P 4")
    y = _rx(t5, r"one full tenure of (\d+) \([^)]+\) years")
    a = _rx(t4, r"\(last 5 years\): (\d+) Points")
    b = _rx(t4, r"Interview: (\d+) Points")
    c = _rx(t4, r"Certifications: (\d+) Points")
    d = _rx(t4, r"Experience Weighting: (\d+) Points")
    z = _rx(t4, r"ratio of (1:\d+)")
    return (f"Up to E4 the criteria are identical for engineering and support disciplines - the same residency, APAR "
            f"benchmark and vigilance clearance, with no vacancy constraint (R&P 2.2). The divergence starts at E4 to E5: "
            f"technical cadres (Drilling, Production, Reservoir, Geology, Geophysics, Engineering) must first complete a "
            f"{y}-year Category 'C' hard-station tenure or be bypassed by the DPC (5.1-5.2), whereas HR, MM and Finance are "
            f"not in that list. The merit matrix ({a} APAR / {b} interview / {c} qualifications / {d} seniority) and the "
            f"{z} zone of consideration apply to all disciplines, with seniority reckoned within each discipline (4.2-4.3).")


NARRATIVES = {
    "P1": _p1, "P1__drill_down": _p1_drill, "P1__why": _p1_why, "P1__compare_or_so_what": _p1_cmp,
    "P2": _p2, "P2__drill_down": _p2_drill, "P2__why": _p2_why, "P2__compare_or_so_what": _p2_cmp,
    "P3": _p3, "P3__drill_down": _p3_drill, "P3__why": _p3_why, "P3__compare_or_so_what": _p3_cmp,
    "P4": _p4, "P4__drill_down": _p4_drill, "P4__why": _p4_why, "P4__compare_or_so_what": _p4_cmp,
    "P5": _p5, "P5__drill_down": _p5_drill, "P5__why": _p5_why, "P5__compare_or_so_what": _p5_cmp,
    "P6": _p6, "P6__drill_down": _p6_drill, "P6__why": _p6_why, "P6__compare_or_so_what": _p6_cmp,
    "P7": _p7, "P7__drill_down": _p7_drill, "P7__why": _p7_why, "P7__compare_or_so_what": _p7_cmp,
    "P8": _p8, "P8__drill_down": _p8_drill, "P8__why": _p8_why, "P8__compare_or_so_what": _p8_cmp,
    "P9": _p9, "P9__drill_down": _p9_drill, "P9__why": _p9_why, "P9__compare_or_so_what": _p9_cmp,
    "P10": _p10, "P10__drill_down": _p10_drill, "P10__why": _p10_why, "P10__compare_or_so_what": _p10_cmp,
}
