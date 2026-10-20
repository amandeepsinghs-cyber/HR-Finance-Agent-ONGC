"""Detailed rulebook definitions for all 7 ONGC demo reconstructions.

Provides deep, realistic, formal ONGC policy text, clauses, subclauses,
schedules, and real excerpt concordances for:
1. JRTP (Job Rotation & Transfer Policy)
2. BDP summary (Book of Delegated Powers)
3. Leave Rules (ONGC Leave Rules, 1995)
4. R&P/Promotion (Modified Recruitment & Promotion Regulations 1980 & DPC Guidelines)
5. HR Manual (Designations, Pay Scales & Service Conditions)
6. PRBS (Post Retirement Benefit Scheme)
7. Post-retirement medical (Post-Retirement Medical Benefit Scheme & Retiree Welfare)
"""

from typing import List, Dict, Any
from generators.documents.rulebook_models import (
    Rulebook, Chapter, Clause, Subclause, Annexure, AmendmentRecord
)

def get_all_rulebooks() -> List[Rulebook]:
    return [
        build_jrtp(),
        build_bdp(),
        build_leave_rules(),
        build_rp_regulations(),
        build_hr_manual(),
        build_prbs(),
        build_medical()
    ]


def build_jrtp() -> Rulebook:
    """Builds JRTP Rulebook."""
    amendments = [
        AmendmentRecord("Rev 0", "15-May-1992", "Board of Directors", "Original Job Rotation and Transfer Policy framed under ONGC Act."),
        AmendmentRecord("Rev 1", "01-Jul-2002", "Executive Committee", "Introduction of formal 3-year minimum station tenure and 10-year cumulative cap."),
        AmendmentRecord("Rev 2", "18-Oct-2010", "Board of Directors", "Formalization of North-East mandatory posting prerequisite for E4 to E5 merit promotion."),
        AmendmentRecord("Rev 3", "01-Apr-2016", "Executive Committee", "Establishment of Geographic Cluster system (Delhi-NCR, Mumbai Urban, Gujarat, Assam) and alignment with TA Regulations 2016."),
        AmendmentRecord("Rev 4", "01-Jul-2022", "Chairman & Managing Director", "Digitization of transfer proposals via intranet portal; clarification of pre-retirement exemption within 2-3 years of superannuation."),
    ]

    definitions = {
        "Station / Work Centre": "Any designated geographical establishment of ONGC including corporate offices, asset offices, basin headquarters, forward bases, plants, institutes, and logistics hubs.",
        "Geographic Cluster": "A defined group of contiguous work centres and operational bases within a common geographical zone where inter-station transfers are treated as within-cluster movements and do not reset cumulative cluster tenure.",
        "Hard Station (Category C)": "Stations characterized by severe operational difficulty, remote location, arduous climatic conditions, or North-East topography, including Assam Asset (Nazira/Sivasagar/Jorhat), Tripura Asset (Agartala), Bokaro CBM, Rajasthan Basin (Jodhpur), and Offshore Platforms/Installations.",
        "Station Tenure": "Continuous duration of posting served by an executive at a specific work centre from the date of reporting to the date of formal relief.",
        "Cumulative Cluster Tenure": "Total aggregate period served by an executive across one or more work centres within the same defined Geographic Cluster across their entire career.",
        "Pre-Decisional Records": "All draft transfer proposal sheets, committee minutes, replacement matrices, and preliminary transfer rosters prior to formal approval and official notification.",
        "Competent Transfer Authority": "The executive or committee empowered under the Book of Delegated Powers and Service Rules to approve and issue transfer orders for respective officer grades."
    }

    c1 = Chapter(
        1, "Preamble, Objectives & Scope",
        [
            Clause(
                clause_ref="Clause 1.0",
                clause_title="Short Title, Commencement and Scope",
                clause_text=(
                    "1.1 This policy shall be titled the 'ONGC Job Rotation & Transfer Policy (JRTP)' (Revision 4).\n"
                    "1.2 It shall apply to all regular executives across all disciplines in Grades E0 through E9 "
                    "posted across all work centres, plants, basins, offshore installations, and corporate offices of the Corporation.\n"
                    "1.3 The core objectives of job rotation and transfers in ONGC are: (a) ensuring optimal deployment of specialized technical "
                    "and managerial talent across upstream operational theatres; (b) broadening multi-basin and operational exposure for executive "
                    "leadership development; (c) ensuring equitable sharing of arduous and remote postings; and (d) maintaining operational readiness "
                    "and business continuity in critical exploration, drilling, production, and refining activities.\n"
                    "1.4 Transfer is an incident of service in ONGC. Every executive is liable to be transferred to any work centre, onshore basin, "
                    "offshore installation, institute, subsidiary, or joint venture of the Corporation within India or abroad."
                ),
                subclauses=[
                    Subclause("1.1", "Short Title & Revision", "Formally titled Job Rotation & Transfer Policy (JRTP), Rev 4."),
                    Subclause("1.2", "Executive Applicability", "Mandatory applicability across all E0–E9 regular executives nationwide."),
                    Subclause("1.3", "Strategic Objectives", "Balancing technical skill distribution, succession planning, and equitable hard station rotation."),
                    Subclause("1.4", "Corporate Service Liability", "Clear statement that transfer is an inherent condition of public sector enterprise employment.")
                ],
                maps_to_question_ids="E2; P1",
                source_basis="J-03"
            ),
            Clause(
                clause_ref="Clause 2.0",
                clause_title="Definitions & Classification of Work Centres",
                clause_text=(
                    "2.1 All work centres of the Corporation are categorized into three distinct categories for transfer and rotation administration:\n"
                    "   (a) Category 'A' (Standard / Urban / Corporate Centres): New Delhi HQ, Dehradun Complex (Tel Bhavan, KDMIPE, GEOPIC, IDT), "
                    "Ahmedabad, Mehsana, Mumbai Urban Offices (WOB, ROM), Vadodara, Kolkata Hub, Chennai, and Panvel Regional Offices.\n"
                    "   (b) Category 'B' (Operational / Field Bases): Ankleshwar, Cambay, Rajahmundry, Karaikal, Uran Plant, Hazira Plant, Dahej, "
                    "and associated onshore logistics supply bases.\n"
                    "   (c) Category 'C' (Hard Station / Difficult / Arduous & Offshore): Assam Operational Asset (Nazira, Sivasagar, Jorhat), "
                    "Tripura Asset (Agartala, Silchar), Bokaro CBM Complex, Rajasthan Basin (Jodhpur), and Offshore Platforms/Marine Production Installations "
                    "(Mumbai High North/South, Neelam, Heera, Bassein, and Eastern Offshore Deepwater Kakinada).\n"
                    "2.2 Reclassification of any work centre shall require the approval of the Executive Committee upon recommendation of Director (HR)."
                ),
                subclauses=[
                    Subclause("2.1", "Station Categorisation Matrix", "Defines Category A (Corporate/Metro), Category B (Field/Plant), and Category C (Hard Station/Offshore)."),
                    Subclause("2.2", "Hard Station Designation", "Formal classification of North-East, Bokaro, Jodhpur, and Offshore installations as Category C.")
                ],
                maps_to_question_ids="P1; P2",
                source_basis="P1-16"
            )
        ]
    )

    c2 = Chapter(
        2, "Station Tenure Norms & Cumulative Stay Caps",
        [
            Clause(
                clause_ref="Clause 3.0",
                clause_title="Station Tenure Norms",
                clause_text=(
                    "3.1 Minimum Station Tenure: The minimum normal tenure of an executive at any station shall be 3 (three) completed years.\n"
                    "3.2 Normal Rotation Window: Normal rotation of an executive shall be considered upon completion of 3 to 5 years at a work centre. "
                    "No executive shall ordinarily be displaced prior to completing 3 years, except on administrative exigencies, organizational restructuring, "
                    "or proven disciplinary necessity approved by Director (HR).\n"
                    "3.3 Technical Stint Longevity: For critical technical cadres (Drilling rig managers, Reservoir simulation specialists, Production platform heads), "
                    "tenure may be extended up to 5 years by the Key Executive to ensure project delivery, drilling campaign stability, and asset integrity.\n"
                    "3.4 The median stint across executive postings in the Corporation is statistically tracked at approximately 3.0 to 3.5 years, "
                    "maintaining institutional memory while preventing stagnation."
                ),
                subclauses=[
                    Subclause("3.1", "Three-Year Minimum Norm", "Establishes strict 3-year minimum residency prior to transfer eligibility."),
                    Subclause("3.2", "Three-to-Five Year Window", "Defines the standard operational rotation window between 36 and 60 months."),
                    Subclause("3.3", "Technical Continuity", "Permits extension up to 5 years for specialized drilling and reservoir engineering assignments.")
                ],
                maps_to_question_ids="E2; P1; D5; H10",
                source_basis="J-03"
            ),
            Clause(
                clause_ref="Clause 4.0",
                clause_title="Cumulative Stay Cap",
                clause_text=(
                    "4.1 Maximum Cumulative Career Stay: No executive shall be permitted to spend more than an aggregate of 10 (ten) years "
                    "at a single city or designated Geographic Cluster over their entire career in the Corporation.\n"
                    "4.2 Computation of Cumulative Stay: Cumulative stay shall be computed as the mathematical sum of all historical postings (SCD2 records) "
                    "served at work centres belonging to the same station or cluster, irrespective of breaks between postings or promotions in place.\n"
                    "4.3 Overstay Review: Corporate HR shall compile annually a list of all officers who have completed 5, 8, and 10 years of cumulative stay. "
                    "Officers who have completed or exceeded 10 years at a single cluster (notably Delhi-NCR or Mumbai Urban) shall be placed on the mandatory "
                    "outstation transfer proposal list for immediate redeployment to operational assets.\n"
                    "4.4 Retention Exceptions: Retention beyond the 10-year cumulative cap can only be granted under exceptional circumstances: (a) impending "
                    "superannuation within 2 to 3 years; (b) certified severe medical conditions approved by the Special Review Board; or (c) explicit CMD approval "
                    "for vital national hydrocarbon projects."
                ),
                subclauses=[
                    Subclause("4.1", "Ten-Year Career Ceiling", "Strict 10-year lifetime cap per station/cluster."),
                    Subclause("4.2", "Cumulative Aggregation Rule", "All postings within the same cluster accumulate towards the 10-year ceiling."),
                    Subclause("4.3", "Corporate HQ Overstay Roster", "Mandatory tracking and transfer proposals for officers exceeding 5 and 10 years in Delhi HQ."),
                    Subclause("4.4", "Exceptional Retention Authority", "Retention beyond 10 years requires CMD sanction or statutory pre-retirement exemption.")
                ],
                maps_to_question_ids="P1; P11; T2_FU2; H10",
                source_basis="J-03"
            )
        ]
    )

    c3 = Chapter(
        3, "Geographic Clusters & North-East / Hard Station Norms",
        [
            Clause(
                clause_ref="Clause 5.0",
                clause_title="Geographic Clusters",
                clause_text=(
                    "5.1 Contiguous stations within a defined industrial or urban agglomeration shall constitute a single Geographic Cluster.\n"
                    "5.2 The designated Geographic Clusters of ONGC are:\n"
                    "   (i) Cluster CL-DEL (Delhi National Capital Region): New Delhi Corporate HQ (Deendayal Urja Bhawan), Noida Offices, and Gurgaon.\n"
                    "   (ii) Cluster CL-MUM (Mumbai Urban & Petrochemicals): Mumbai World Oilfield Base (WOB), Regional Office Mumbai (ROM), "
                    "Uran Plant, Panvel Institutes (IOGPT, IEOT), and Dronagiri Logistics.\n"
                    "   (iii) Cluster CL-AHM-MEH (Ahmedabad–Mehsana): Ahmedabad Asset, Mehsana Asset, and Institute of Reservoir Studies (IRS).\n"
                    "   (iv) Cluster CL-CAM-ANK-VAD (Cambay–Ankleshwar–Vadodara): Vadodara Regional Office, Ankleshwar Asset, Cambay Asset, Hazira Plant, and Dahej C2-C3 Plant.\n"
                    "   (v) Cluster CL-NE-ASSAM (Assam Basin & Fields): Nazira Operational HQ, Sivasagar Asset, Jorhat Basin HQ, A&A Basin, and Silchar Base.\n"
                    "   (vi) Cluster CL-NE-TRIPURA (Tripura Complex): Agartala Asset and exploration blocks.\n"
                    "   (vii) Cluster CL-DDN (Dehradun Complex): Tel Bhavan HQ, KDMIPE, GEOPIC, IDT, and Academy.\n"
                    "   (viii) Cluster CL-KG (Eastern Offshore & KG Basin): Rajahmundry Asset and Kakinada Offshore Forward Base.\n"
                    "   (ix) Cluster CL-CAU-CHN (Cauvery Basin & Chennai): Karaikal Asset and Chennai Regional Office.\n"
                    "   (x) Cluster CL-KOL (Kolkata Hub): MBA Basin Headquarters and Regional Office.\n"
                    "   (xi) Cluster CL-BOK (Bokaro CBM Complex): Bokaro Coal Bed Methane Operations.\n"
                    "   (xii) Cluster CL-JOD (Jodhpur Rajasthan Basin): Jodhpur Field Base.\n"
                    "   (xiii) Cluster CL-GOA (Goa Training Hub): IPSHEM Betul.\n"
                    "5.3 Intra-Cluster Transfer Effect: Transfer between work centres within the same Geographic Cluster (e.g. from New Delhi to Noida, "
                    "or from Ahmedabad Asset to IRS Chandkheda, or from Mumbai WOB to Uran Plant) shall NOT constitute an outstation transfer for the purpose "
                    "of resetting station tenure or cumulative cluster tenure."
                ),
                subclauses=[
                    Subclause("5.1", "Cluster Definition", "Defines industrial agglomeration boundaries."),
                    Subclause("5.2", "Official Cluster Schedule", "Full listing of the 13 clusters matching world_bible reference."),
                    Subclause("5.3", "No Tenure Reset", "Intra-cluster movement preserves cumulative stay count.")
                ],
                maps_to_question_ids="E2; P2; P11",
                source_basis="P1-16"
            ),
            Clause(
                clause_ref="Clause 6.0",
                clause_title="Mandatory North-East / Hard Station Tenure",
                clause_text=(
                    "6.1 Mandatory Prerequisite for Executive Leadership: Every executive belonging to technical and general operational disciplines "
                    "must successfully complete at least one full tenure of 3 (three) continuous years in a Category 'C' Hard Station or North-East work centre "
                    "(Assam Asset, Tripura Asset, Bokaro CBM, Rajasthan Jodhpur, or 14/14 Offshore Duty) prior to consideration for merit promotion "
                    "from Superintending Engineer / Chief Manager (Grade E4) to Deputy General Manager (Grade E5).\n"
                    "6.2 Merit Review Exclusion: Executives who have not completed their mandatory Category 'C' hard station tenure shall not be empaneled "
                    "in the zone of consideration for E4→E5 merit review, unless explicitly granted temporary deferment by the Executive Committee on recorded "
                    "grounds of operational deployment on mission-critical national assets.\n"
                    "6.3 Incentives & Allowances: Officers serving in Category 'C' North-East and hard stations are entitled to Special Hard Station Allowance (10% of BP), "
                    "retention of family accommodation at the last station, additional casual leave, and subsidized travel concession (STC) per TA Regulations."
                ),
                subclauses=[
                    Subclause("6.1", "Mandatory 3-Year Hard Stint", "Three years Category C hard station service required before E5 promotion."),
                    Subclause("6.2", "Promotion Ineligibility", "Executives without Category C tenure barred from E4→E5 DPC review."),
                    Subclause("6.3", "Hard Station Benefits", "Special allowances, family retention, and TA entitlements.")
                ],
                maps_to_question_ids="P12; H10_FU1",
                source_basis="J-15"
            )
        ]
    )

    c4 = Chapter(
        4, "Exemptions, Deferments & Compassionate Grounds",
        [
            Clause(
                clause_ref="Clause 7.0",
                clause_title="Pre-Retirement Tenure Exemption",
                clause_text=(
                    "7.1 Superannuation Settlement Protection: Executives who are within 2 (two) years of superannuation (age 58 years and above) "
                    "shall be strictly exempt from mandatory outstation transfers. In organizational practice and annual transfer planning, "
                    "executives with 3 years or less remaining until superannuation (age 57 years and above) shall ordinarily not be transferred out "
                    "of their current station, to enable smooth superannuation transition, pension settlement, family stabilization, and medical management.\n"
                    "7.2 Exceptions to Protection: Pre-retirement exemption shall not apply where: (a) the officer explicitly requests an outstation transfer "
                    "to their declared home town / choice retirement station under Rule 14; or (b) an administrative or disciplinary transfer is ordered "
                    "under the specific written directions of the Director (HR) or CMD.\n"
                    "7.3 Statistical Compliance: Analysis of enterprise SAP records indicates that non-initial transfers within 3 years of retirement "
                    "account for less than 2.0% of total transfer actions, reflecting rigorous compliance with this protective provision."
                ),
                subclauses=[
                    Subclause("7.1", "Two-to-Three Year Exemption Norm", "Statutory exemption from outstation transfer for executives retiring within 2–3 years."),
                    Subclause("7.2", "Home Town Choice Transfer", "Permits voluntary request to move to preferred retirement location."),
                    Subclause("7.3", "Empirical Adherence", "Low observed rate of transfers near superannuation confirmed in enterprise records.")
                ],
                maps_to_question_ids="P3; P11; H10; H10_FU3",
                source_basis="J-03"
            ),
            Clause(
                clause_ref="Clause 8.0",
                clause_title="Medical & Compassionate Grounds",
                clause_text=(
                    "8.1 Serious Medical Illness: An executive suffering from serious chronic ailments (cancer, renal failure, cardiac disease requiring tertiary care, "
                    "or major neurological disorders), or having a dependent spouse or child suffering from such certified conditions, may apply for deferment "
                    "or exemption from transfer.\n"
                    "8.2 Medical Board Certification: All medical grounds must be evaluated and certified by an ONGC Standing Medical Board comprising the "
                    "Chief Medical Officer and specialist government physicians.\n"
                    "8.3 Special Review Board (SRB): All medical and compassionate exemption requests shall be adjudicated by the Special Review Board, chaired by "
                    "Director (HR), with ED-Chief ER and Head Corporate Medical as members. Approvals shall be valid for a maximum of 1 to 2 years, subject "
                    "to annual medical re-evaluation."
                ),
                subclauses=[
                    Subclause("8.1", "Chronic Illness Criteria", "Specifies qualifying critical health conditions for transfer deferment."),
                    Subclause("8.2", "Medical Board Evaluation", "Mandates formal certification by ONGC Standing Medical Board."),
                    Subclause("8.3", "Special Review Board Role", "Chaired by Director (HR); grants time-bound exemptions.")
                ],
                maps_to_question_ids="H10_FU3",
                source_basis="P1-03"
            )
        ]
    )

    c5 = Chapter(
        5, "Transfer Calendar, Cadre Balancing & Confidentiality",
        [
            Clause(
                clause_ref="Clause 9.0",
                clause_title="Annual Transfer Calendar & Notification Procedure",
                clause_text=(
                    "9.1 Structured Annual Transfer Cycle: To maintain operational stability and align with academic school sessions, general transfers "
                    "shall follow a strict annual schedule:\n"
                    "   (a) Initiation & Preference Submission (November–December): Corporate HR invites online tenure-complete declarations and transfer preferences via ESS.\n"
                    "   (b) Cadre Balancing & Replacement Mapping (January–February): Corporate HR and Cadre Authorities review vacancies, replacement matrices, and DPC outcomes.\n"
                    "   (c) Competent Authority Approval (March): Final proposals submitted to Director (HR) and CMD.\n"
                    "   (d) Official Notification (March / April): Formal transfer orders notified simultaneously on the intranet portal (ONGC Reports Web Portal).\n"
                    "   (e) Effective Movement (May–June, finalized by 1st July): Relieving and joining completed prior to the academic year.\n"
                    "9.2 Prohibition of Mid-Term Transfers: Mid-term out-of-cycle transfers are strictly prohibited except for unforeseen rig emergencies, operational blowout "
                    "control, project commissioning, or disciplinary action."
                ),
                subclauses=[
                    Subclause("9.1", "Annual Five-Stage Cycle", "November initiation to March/April notification, effective 1st July."),
                    Subclause("9.2", "Mid-Term Transfer Ban", "Prohibits off-cycle moves without explicit Director (HR) approval.")
                ],
                maps_to_question_ids="D2; D2_FU1; D2_FU3",
                source_basis="J-03"
            ),
            Clause(
                clause_ref="Clause 10.0",
                clause_title="Replacement & Cadre Balancing Norms",
                clause_text=(
                    "10.1 Discipline-for-Discipline Matching: In critical operational disciplines (Drilling, Production, Reservoir, Geology, Geophysics, Electrical, "
                    "Mechanical, and Instrumentation), no executive shall be relieved from an operational asset until a qualified replacement of matching discipline "
                    "and comparable seniority has reported or been placed on the mobilization schedule.\n"
                    "10.2 Asset Head Concurrence: Asset Managers and Basin In-charges must certify that replacement arrangements are in place to prevent production disruption."
                ),
                subclauses=[
                    Subclause("10.1", "One-for-One Matching", "Mandatory replacement in specialized technical cadres before release."),
                    Subclause("10.2", "Asset Continuity Certification", "Asset Manager must sign off on relief protocol.")
                ],
                maps_to_question_ids="H10; H10_FU2",
                source_basis="J-03"
            ),
            Clause(
                clause_ref="Clause 11.0",
                clause_title="Confidentiality of Pre-Decisional Records",
                clause_text=(
                    "11.1 Absolute Confidentiality of Draft Proposals: All preliminary transfer sheets, draft rosters, internal deliberations of the Transfer Screening Committee, "
                    "and proposed replacement lists are strictly CONFIDENTIAL and PRE-DECISIONAL records under Rule 11 of the ONGC CDA Rules, 1994.\n"
                    "11.2 Prohibition of Unauthorized Disclosure: No employee or executive shall solicit, disclose, share, circulate, or leak draft transfer orders "
                    "prior to official notification on the intranet portal. Any unauthorized disclosure of draft transfer lists constitutes major misconduct.\n"
                    "11.3 Digital System Access Controls: Access to transfer generation modules and draft proposal tables shall be restricted strictly to authorized "
                    "personnel in Corporate HR."
                ),
                subclauses=[
                    Subclause("11.1", "Pre-Decisional Classification", "Draft transfer lists are protected under CDA Rule 11."),
                    Subclause("11.2", "Leakage Misconduct", "Circulation of draft orders treated as severe disciplinary offence."),
                    Subclause("11.3", "Role-Based Access", "Draft rosters locked down cryptographically within HR systems.")
                ],
                maps_to_question_ids="P18; D2; D5",
                source_basis="P1-01"
            )
        ]
    )

    c6 = Chapter(
        6, "Competent Authorities & Grievance Redressal",
        [
            Clause(
                clause_ref="Clause 12.0",
                clause_title="Competent Transfer Authorities",
                clause_text=(
                    "12.1 Delegated Approval Matrix: The authorities empowered to approve transfers of executives are:\n"
                    "   (a) Grades E0 to E4 (Graduate Trainee to Superintending Engineer / Chief Manager): Executive Director – Chief Corporate HR, "
                    "in consultation with respective Cadre Heads.\n"
                    "   (b) Grades E5 to E6 (Deputy General Manager to Joint General Manager / Addl. GM): Director (HR).\n"
                    "   (c) Grades E7 to E9 (General Manager, Chief General Manager, Executive Director): Chairman & Managing Director (CMD).\n"
                    "   (d) Functional Directors & Board Members: Competent Authority in the Ministry of Petroleum & Natural Gas (MoPNG) / Appointments Committee of Cabinet (ACC)."
                ),
                subclauses=[
                    Subclause("12.1", "Grade Approval Hierarchy", "ED-HR for E0–E4; Director HR for E5–E6; CMD for E7–E9.")
                ],
                maps_to_question_ids="E2; H10",
                source_basis="P1-04"
            ),
            Clause(
                clause_ref="Clause 13.0",
                clause_title="Transfer Grievance Redressal Mechanism",
                clause_text=(
                    "13.1 Representation Timeline: Any executive aggrieved by a transfer order may submit a formal representation to the Transfer Grievance Redressal Committee (TGRC) "
                    "within 15 (fifteen) calendar days from the date of official publication of the transfer order on the intranet portal.\n"
                    "13.2 Grounds for Representation: Representations shall be entertained strictly on specified grounds: (a) genuine medical emergency certified by Medical Board; "
                    "(b) child appearing in Class X or XII Board examination in the current academic year; (c) spouse working in central/state government or CPSE at the current station "
                    "(DOPT guidelines); or (d) superannuation within 2–3 years.\n"
                    "13.3 Time-Bound Disposal: The TGRC, chaired by an Executive Director, shall examine each representation and convey its recommendations to Director (HR) "
                    "within 30 days. Filing a representation does not confer an automatic right to stay at the station unless stay is granted in writing by Director (HR)."
                ),
                subclauses=[
                    Subclause("13.1", "15-Day Representation Window", "Appeals must be lodged within 15 days of order."),
                    Subclause("13.2", "Qualifying Appeal Grounds", "Board examinations, working spouse, medical grounds, superannuation."),
                    Subclause("13.3", "30-Day Resolution", "Committee disposes of appeals within 30 days.")
                ],
                maps_to_question_ids="E2",
                source_basis="J-03"
            )
        ]
    )

    annex1 = Annexure(
        "Annexure I", "Schedule of Geographic Clusters & Work Centres",
        "Official register of geographic clusters established under JRTP Clause 5.0.",
        table_headers=["Cluster ID", "Cluster Name", "Constituent Work Centres", "Primary Sector"],
        table_rows=[
            ["CL-DEL", "Delhi National Capital Region", "WC-DEL (Corporate HQ New Delhi), Noida, Gurgaon", "Northern / Corporate"],
            ["CL-MUM", "Mumbai–Panvel–Uran", "WC-MUM, WC-BAS, WC-NEH, WC-URN, WC-WOB, WC-IOG, WC-IEO, WC-ROM, WC-DRL, WC-WEL, WC-LOG", "Western / Offshore"],
            ["CL-AHM-MEH", "Ahmedabad–Mehsana", "WC-AHM (Ahmedabad Asset), WC-MEH (Mehsana Asset), WC-IRS (Chandkheda)", "Western Onshore"],
            ["CL-CAM-ANK-VAD", "Cambay–Ankleshwar–Vadodara", "WC-ANK (Ankleshwar), WC-CAM (Cambay), WC-HAZ (Hazira Plant), WC-DAH (Dahej), WC-WNB, WC-CEW, WC-ROV, WC-GLS (Vadodara)", "Western Onshore"],
            ["CL-NE-ASSAM", "Nazira–Jorhat–Silchar", "WC-ASM (Nazira/Sivasagar), WC-JOR (Jorhat Basin), WC-AAB, WC-SIL (Silchar), WC-INB", "North-East / Category C"],
            ["CL-NE-TRIPURA", "Tripura Agartala", "WC-TRI (Agartala Asset)", "North-East / Category C"],
            ["CL-DDN", "Dehradun Complex", "WC-DDN (Tel Bhavan), WC-FRB, WC-KDM (KDMIPE), WC-GEO (GEOPIC), WC-IDW, WC-ACA", "Northern / Corporate Institutes"],
            ["CL-KG", "Rajahmundry–Kakinada", "WC-EAS (Eastern Offshore Kakinada), WC-RAJ (Rajahmundry), WC-KGB", "Southern / KG Basin"],
            ["CL-CAU-CHN", "Cauvery–Chennai", "WC-CAU (Karaikal Asset), WC-CAB, WC-ROC (Chennai)", "Southern Onshore / Offshore"],
            ["CL-KOL", "Kolkata Hub", "WC-MBA (MBA Basin Kolkata), WC-ROK", "Eastern Onshore"],
            ["CL-BOK", "Bokaro CBM Complex", "WC-BOK (Bokaro CBM)", "Eastern / Category C"],
            ["CL-JOD", "Jodhpur Rajasthan Basin", "WC-RAJ-BSN (Jodhpur Asset)", "Western / Category C"],
            ["CL-GOA", "Goa Training Complex", "WC-ATI (IPSHEM Betul Goa)", "Training / Safety Hub"]
        ],
        notes="Transfers within the same Cluster ID do not reset station tenure or cumulative cluster tenure."
    )

    annex2 = Annexure(
        "Annexure II", "Schedule of Category 'C' Hard Stations & Offshore Locations",
        "Official schedule of stations qualifying for mandatory hard station tenure under Clause 6.0 and R&P regulations.",
        table_headers=["Work Centre ID", "Station Name", "State / Basin", "Classification", "Mandatory Min Tenure"],
        table_rows=[
            ["WC-ASM", "Nazira / Sivasagar Asset", "Assam", "Category C (Hard Station)", "3 Years"],
            ["WC-JOR", "Jorhat Basin HQ", "Assam", "Category C (Hard Station)", "3 Years"],
            ["WC-SIL", "Silchar Forward Base", "Assam", "Category C (Hard Station)", "3 Years"],
            ["WC-TRI", "Tripura Asset (Agartala)", "Tripura", "Category C (Hard Station)", "3 Years"],
            ["WC-BOK", "Bokaro CBM Asset", "Jharkhand", "Category C (Hard Station)", "3 Years"],
            ["WC-RAJ-BSN", "Jodhpur Field Base", "Rajasthan", "Category C (Hard Station)", "3 Years"],
            ["WC-MUM / OFF", "Mumbai High Offshore (N/S)", "Offshore Western", "Category C (Offshore 14/14)", "3 Years equivalent"],
            ["WC-BAS / OFF", "Bassein & Satellite Offshore", "Offshore Western", "Category C (Offshore 14/14)", "3 Years equivalent"],
            ["WC-NEH / OFF", "Neelam & Heera Offshore", "Offshore Western", "Category C (Offshore 14/14)", "3 Years equivalent"],
            ["WC-EAS / OFF", "KG Deepwater Offshore", "Offshore Eastern", "Category C (Offshore 14/14)", "3 Years equivalent"]
        ]
    )

    concordance = [
        {"doc_id": "J-03", "title": "Delhi HC LPA Judgment (Kinshuk Mahanty v. ONGC)", "clause_ref": "Clause 1.0, 3.0, 4.0, 7.0, 9.0", "verbatim_quote": "retention and transfer policy of the ONGC"},
        {"doc_id": "P1-16", "title": "ONGC Travelling Allowance Regulations 2016", "clause_ref": "Clause 2.0, 5.0, Annexure I", "verbatim_quote": "Travelling Allowance Regulations"},
        {"doc_id": "P1-01", "title": "ONGC Conduct, Discipline & Appeal Rules, 1994", "clause_ref": "Clause 11.0", "verbatim_quote": "Rule 11 (Unauthorized disclosure of information)"},
        {"doc_id": "J-15", "title": "Supreme Court / Delhi HC (Dwarika Prasad v. ONGC)", "clause_ref": "Clause 6.0", "verbatim_quote": "Modified Recruitment and Promotion Regulations"}
    ]

    return Rulebook(
        doc_id="JRTP",
        title="Job Rotation & Transfer Policy (JRTP)",
        short_title="ONGC JRTP",
        ref_code="ONGC/CORP-HR/POL/JRTP/2016-REV4",
        effective_date="1st July 2016 (Amended up to 31st March 2026)",
        issuer="Corporate Employee Relations & Policy Group, Tel Bhavan, Dehradun",
        approving_authority="Executive Committee & Board of Directors, ONGC",
        classification="INTERNAL CONTROLLED DOCUMENT / DEMO RECONSTRUCTION",
        preamble=(
            "Oil and Natural Gas Corporation Limited (ONGC) operates across diverse onshore basins, offshore continental shelves, "
            "deepwater assets, and refining plants across India. The Job Rotation and Transfer Policy (JRTP) establishes the governing "
            "framework for executive mobility, technical cadre balancing, leadership development, and equitable rotation across standard, "
            "arduous, and hard station assignments. This document synthesizes established internal norms, court judgments, circulars, "
            "and TA regulations into a unified formal rulebook."
        ),
        definitions=definitions,
        chapters=[c1, c2, c3, c4, c5, c6],
        annexures=[annex1, annex2],
        amendment_history=amendments,
        real_excerpts_concordance=concordance
    )


def build_bdp() -> Rulebook:
    """Builds Book of Delegated Powers (BDP 2015 Summary Schedule)."""
    amendments = [
        AmendmentRecord("BDP 1997", "01-Apr-1997", "Board of Directors", "Initial delegation framework post-corporatization of Commission."),
        AmendmentRecord("BDP 2007", "01-Oct-2007", "Board of Directors", "Substantial revision following grant of Maharatna status and DPE guidelines."),
        AmendmentRecord("BDP 2015", "01-Aug-2015", "Board of Directors", "Comprehensive overhaul aligned with IMMM 2015 and Companies Act 2013."),
        AmendmentRecord("BDP 2019 Amend", "15-Nov-2019", "Executive Committee", "Enhanced procurement limits for Asset Managers and Key Executives; digital SAP concurrence."),
        AmendmentRecord("BDP 2024 Update", "20-Jan-2024", "Board of Directors", "Refinement of emergency offshore blowout control limits and capex thresholds.")
    ]

    definitions = {
        "Level 1 Authority": "The Chairman & Managing Director (CMD) of the Corporation.",
        "Level 2 Authority": "Whole-Time Functional Directors (Director Finance, Director Offshore, Director Onshore, Director Exploration, Director Production, Director HR).",
        "Level 3 Authority": "Executive Committee (EC), Key Executives, Asset Managers, Basin Managers, Chiefs of Services, and Executive Directors (E9).",
        "Level 4 Authority": "General Managers (E7), Chief General Managers (E8), and Head of Departments.",
        "Level 5 Authority": "Deputy General Managers (E5), Joint General Managers (E6), and Section Heads.",
        "Technical Sanction": "Formal sanction by competent technical authority confirming the engineering design, necessity, and specifications of a proposed project or work.",
        "Expenditure Sanction": "Financial authorization granted by the competent financial authority committing corporate funds for execution of approved works.",
        "Associate Finance": "The designated Finance & Accounts executive or department attached to an operational unit whose formal financial concurrence is mandatory prior to expenditure."
    }

    c1 = Chapter(
        1, "Principles of Financial Delegation & Governance Structure",
        [
            Clause(
                clause_ref="Clause 1.0",
                clause_title="Principles of Financial Delegation",
                clause_text=(
                    "1.1 Constitutional Authority: Under Section 179 of the Companies Act, 2013, the Board of Directors of ONGC delegates financial "
                    "and administrative powers to specified executive levels to facilitate agile and decentralised operational decision-making.\n"
                    "1.2 Fundamental Delegation Principles:\n"
                    "   (a) Powers are delegated to posts, not individuals. Powers shall be exercised only by the substantive holder of a post or an officer "
                    "formally designated as in-charge by an office order.\n"
                    "   (b) Exercise of powers is subject to approved budgetary provisions (BE/RE), technical sanction, and established procurement procedures.\n"
                    "   (c) No authority may sanction expenditure for their own personal benefit or override higher authority reservations.\n"
                    "   (d) Five-tier governance structure: Level 1 (CMD), Level 2 (Functional Directors), Level 3 (Key Executives / Asset Managers / EC), "
                    "Level 4 (GMs/CGMs), and Level 5 (Sectional In-charges)."
                ),
                subclauses=[
                    Subclause("1.1", "Legal Authority", "Delegation framed under Companies Act 2013 and ONGC Articles of Association."),
                    Subclause("1.2", "Fundamental Principles", "Delegation to posts, requirement of budget provision, and non-self-sanctioning rule.")
                ],
                maps_to_question_ids="P16; P19",
                source_basis="P1-04"
            )
        ]
    )

    c2 = Chapter(
        2, "Asset Managers & Key Executives Delegated Powers (Level 3)",
        [
            Clause(
                clause_ref="Clause 2.0",
                clause_title="Asset Managers & Key Executives Powers",
                clause_text=(
                    "2.1 Operational Procurement Sanction: Asset Managers, Basin Managers, Chiefs of Services, and Executive Directors heading independent "
                    "work centres (Level 3 Authorities) are empowered to sanction procurement of materials, spares, and services up to ₹10 Crore "
                    "per transaction under open/advertised tender procedures with Associate Finance concurrence.\n"
                    "2.2 Limited / Proprietary Tender Sanction: For limited tenders, sanctioning power is capped at ₹2.5 Crore; for single/proprietary tenders (OEM), "
                    "power is capped at ₹1.0 Crore, subject to proprietary article certificate (PAC).\n"
                    "2.3 Operational Expenditure (Opex) Limits: Sanctioning of routine field operational expenditure, maintenance contracts, logistics charters, "
                    "and production enhancement works is capped at ₹25 Crore per transaction, provided items are within approved annual operating plan (AOP).\n"
                    "2.4 Variation / Amendment Powers: Power to approve contract value variations is limited to 10% of original contract value, not exceeding cumulative limit of ₹2 Crore."
                ),
                subclauses=[
                    Subclause("2.1", "Open Tender Limit ₹10 Cr", "Capped at ₹10 Crore for procurement under open tender."),
                    Subclause("2.2", "Proprietary Limit ₹1 Cr", "Capped at ₹1 Crore for single tender / OEM procurement."),
                    Subclause("2.3", "Opex Authorization ₹25 Cr", "Operational expenditure sanction capped at ₹25 Crore."),
                    Subclause("2.4", "Contract Amendment Limit", "Permissible variation capped at 10% or ₹2 Crore.")
                ],
                maps_to_question_ids="P16; P19",
                source_basis="P1-04"
            )
        ]
    )

    c3 = Chapter(
        3, "Whole-Time Directors Financial Limits (Level 2)",
        [
            Clause(
                clause_ref="Clause 3.0",
                clause_title="Whole-Time Directors Financial Limits",
                clause_text=(
                    "3.1 Whole-Time Functional Directors (Director Finance, Director Offshore, Director Onshore, Director Exploration, Director Production, "
                    "Director HR) are empowered to sanction financial commitments, contracts, and work awards up to ₹50 Crore per transaction for items "
                    "within their functional purview and approved capital/operating budgets.\n"
                    "3.2 Capital Expenditure (Capex) Projects: Approval of detailed project reports (DPR), engineering procurement contracts, and facility creation "
                    "from ₹25 Crore up to ₹50 Crore.\n"
                    "3.3 Drilling & Well Service Contracts: Award of onshore/offshore drilling rig charters, coil tubing, and well stimulation contracts "
                    "up to ₹50 Crore with concurrence of Director (Finance).\n"
                    "3.4 Full Schedule of Director Powers: Functional Directors possess full sanctioning powers within ₹50 Crore across: (i) Capital expenditure; "
                    "(ii) Revenue expenditure; (iii) Service contracts; (iv) Sale of scrap / obsolete assets; (v) Settlement of audit paras and claims; "
                    "(vi) Write-off of losses up to ₹1 Crore."
                ),
                subclauses=[
                    Subclause("3.1", "Director Limit ₹50 Cr", "Sanctioning power up to ₹50 Crore for functional works."),
                    Subclause("3.2", "Capex Authority ₹25–50 Cr", "Facility development and capital contracts up to ₹50 Crore."),
                    Subclause("3.3", "Drilling Contracts Purview", "Drilling rig charter contracts up to ₹50 Crore require Director approval."),
                    Subclause("3.4", "Full Financial Scope", "Full schedule covering capex, opex, services, asset sales, and write-offs.")
                ],
                maps_to_question_ids="P16; P19",
                source_basis="J-18"
            )
        ]
    )

    c4 = Chapter(
        4, "Executive Committee & CMD Powers (Level 1 & Apex)",
        [
            Clause(
                clause_ref="Clause 4.0",
                clause_title="Executive Committee (EC) Financial Limits",
                clause_text=(
                    "4.1 Constitution of Executive Committee: Comprises CMD and all Whole-Time Functional Directors.\n"
                    "4.2 Delegated Sanctioning Range: The Executive Committee is empowered to approve tenders, work awards, project capex, "
                    "and operational contracts valued from ₹50 Crore up to ₹100 Crore.\n"
                    "4.3 Pre-Board Appraisal: All proposals exceeding ₹100 Crore must be appraised and recommended by the Executive Committee "
                    "prior to submission to the Board of Directors."
                ),
                subclauses=[
                    Subclause("4.1", "EC Composition", "Apex executive body consisting of CMD and all Whole-Time Directors."),
                    Subclause("4.2", "EC Range ₹50–100 Cr", "Approve major contracts between ₹50 Crore and ₹100 Crore."),
                    Subclause("4.3", "Screening for Board", "Mandatory appraisal for all matters exceeding ₹100 Crore.")
                ],
                maps_to_question_ids="P16; P19",
                source_basis="P1-04"
            ),
            Clause(
                clause_ref="Clause 5.0",
                clause_title="Chairman & Managing Director (CMD) Powers",
                clause_text=(
                    "5.1 Independent Financial Limit: The Chairman & Managing Director (CMD) possesses independent financial approval authority "
                    "up to ₹100 Crore for corporate capital schemes, strategic exploration works, and major contracts.\n"
                    "5.2 Emergency Operational Powers: In situations of extreme operational emergency (such as offshore platform fires, well blowouts, "
                    "critical submarine pipeline ruptures, or deepwater well control exigencies), CMD is empowered to sanction procurement, specialized "
                    "services (e.g. international well control blowout experts, emergency rigs) up to ₹250 Crore without prior Board approval, "
                    "subject to post-facto reporting to the Board of Directors at its immediately succeeding meeting."
                ),
                subclauses=[
                    Subclause("5.1", "CMD Normal Limit ₹100 Cr", "Sanctioning power up to ₹100 Crore."),
                    Subclause("5.2", "Emergency Limit ₹250 Cr", "Blowout control and life safety emergencies up to ₹250 Crore.")
                ],
                maps_to_question_ids="P16; P19",
                source_basis="P1-04"
            )
        ]
    )

    c5 = Chapter(
        5, "Board Reserved Matters & Interlocks",
        [
            Clause(
                clause_ref="Clause 6.0",
                clause_title="Board of Directors Reserved Matters",
                clause_text=(
                    "6.1 Statutory & Apex Reservations: Under the Maharatna governance guidelines and Companies Act, 2013, the following matters "
                    "are strictly reserved for approval by the full Board of Directors:\n"
                    "   (a) Any contract, tender, or expenditure exceeding ₹100 Crore (except emergency blowout powers exercised by CMD).\n"
                    "   (b) Major deepwater drilling rig charters, jack-up rig fleet acquisitions, and offshore EPC turnkey platform contracts.\n"
                    "   (c) Annual Capital Expenditure Budget (Capex) and Revised Estimates (RE).\n"
                    "   (d) Farm-out, divestment, equity sale, or monetization of domestic or overseas oil and gas fields / blocks.\n"
                    "   (e) Equity investment in domestic or international subsidiaries (OVL), joint ventures, and mergers/acquisitions.\n"
                    "   (f) Borrowings, bond issuances, and commercial loan facilities exceeding statutory thresholds.\n"
                    "6.2 Non-Delegation Principle: No sub-committee or executive authority can exercise powers reserved for the Board."
                ),
                subclauses=[
                    Subclause("6.1", "Reserved Matters Threshold", "All commitments exceeding ₹100 Crore reserved for Board."),
                    Subclause("6.2", "Strategic Assets & Divestments", "Field farm-outs, asset monetization, and joint ventures require Board sanction.")
                ],
                maps_to_question_ids="P16; D4; M4",
                source_basis="G-11"
            ),
            Clause(
                clause_ref="Clause 7.0",
                clause_title="Technical and Expenditure Sanction Interlocks",
                clause_text=(
                    "7.1 Mandatory Financial Concurrence: No financial commitment or expenditure sanction shall be issued without prior formal concurrence "
                    "of the designated Associate Finance department in accordance with IMMM Clause 6.7.2.\n"
                    "7.2 Interlock Sequence: Every procurement transaction requires three mandatory sequential stages: (a) Administrative Approval; "
                    "(b) Technical Sanction by designated engineering head; and (c) Financial Sanction with Associate Finance concurrence.\n"
                    "7.3 Splitting of Contracts Prohibited: Intentionally splitting work orders or purchases to circumvent higher delegated financial limits "
                    "is strictly prohibited and constitutes gross financial irregularity under CDA Rule 4."
                ),
                subclauses=[
                    Subclause("7.1", "Associate Finance Concurrence", "Mandatory finance sign-off before financial commitment."),
                    Subclause("7.2", "Three-Tier Interlock", "Administrative, Technical, and Financial approvals required."),
                    Subclause("7.3", "Contract Splitting Ban", "Strict prohibition against splitting tenders to evade threshold.")
                ],
                maps_to_question_ids="P16",
                source_basis="P1-04"
            ),
            Clause(
                clause_ref="Clause 8.0",
                clause_title="Commercial Confidentiality of Operational Schedules",
                clause_text=(
                    "8.1 Commercial Sensitivity: The detailed schedules of delegated powers, proprietary procurement limits, field-specific financial delegations, "
                    "and vendor sanction thresholds constitute commercially sensitive internal information.\n"
                    "8.2 Internal Controlled Classification: This Book of Delegated Powers is classified as an Internal Controlled Document. Unauthorized publication, "
                    "sharing with external contractors, or public disclosure is prohibited under corporate confidentiality regulations."
                ),
                subclauses=[
                    Subclause("8.1", "Proprietary Sensitivity", "Financial limits classified as internal proprietary operational data."),
                    Subclause("8.2", "Controlled Access", "Strict access restrictions to prevent commercial exploitation.")
                ],
                maps_to_question_ids="D4; M4",
                source_basis="P1-04"
            )
        ]
    )

    annex1 = Annexure(
        "Schedule I", "Comprehensive Financial Delegation Matrix",
        "Summary schedule of financial approval limits by authority level under BDP 2015.",
        table_headers=["Authority Level", "Designation / Body", "Open Tender Procurement", "Operational Expenditure (Opex)", "Capex / Contracts"],
        table_rows=[
            ["Level 1", "Chairman & Managing Director (CMD)", "Up to ₹100 Crore", "Up to ₹100 Crore", "Up to ₹100 Crore (Emergency: ₹250 Cr)"],
            ["Apex Executive", "Executive Committee (EC)", "₹50 Cr to ₹100 Cr", "₹50 Cr to ₹100 Cr", "₹50 Cr to ₹100 Cr"],
            ["Level 2", "Whole-Time Functional Directors", "Up to ₹50 Crore", "Up to ₹50 Crore", "Up to ₹50 Crore"],
            ["Level 3", "Asset Managers / Key Executives / EDs", "Up to ₹10 Crore", "Up to ₹25 Crore", "Up to ₹10 Crore"],
            ["Level 4", "General Managers / Chief General Managers", "Up to ₹2 Crore", "Up to ₹5 Crore", "Up to ₹2 Crore"],
            ["Level 5", "Deputy General Managers / Section Heads", "Up to ₹50 Lakh", "Up to ₹1 Crore", "Up to ₹25 Lakh"],
            ["Apex Body", "Board of Directors", "Exceeding ₹100 Crore", "Exceeding ₹100 Crore", "All items exceeding ₹100 Crore"]
        ]
    )

    concordance = [
        {"doc_id": "P1-04", "title": "Integrated Materials Management Manual (IMMM 2019)", "clause_ref": "Clause 1.0, 2.0, 7.0", "verbatim_quote": "Clause 6.7.2 (Delegation of Powers in MM)"},
        {"doc_id": "J-18", "title": "Gauhati HC Judgment (Prasant Kumar Baruah v. ONGC)", "clause_ref": "Clause 3.0, 4.0, 5.0", "verbatim_quote": "Book of Delegated Powers"},
        {"doc_id": "G-11", "title": "Companies Act, 2013", "clause_ref": "Clause 1.0, 6.0", "verbatim_quote": "Section 179 (Powers of Board)"}
    ]

    return Rulebook(
        doc_id="BDP summary",
        title="Book of Delegated Powers (BDP 2015 Summary)",
        short_title="ONGC BDP Summary",
        ref_code="ONGC/FIN/CORP/BDP/2015-REV2",
        effective_date="1st August 2015 (Updated with Amendments up to 31st March 2026)",
        issuer="Corporate Finance & Accounts Group, New Delhi / Tel Bhavan Dehradun",
        approving_authority="Board of Directors, ONGC",
        classification="INTERNAL CONTROLLED DOCUMENT / DEMO RECONSTRUCTION",
        preamble=(
            "The Book of Delegated Powers (BDP) outlines the financial, procurement, and administrative sanctioning authorities "
            "delegated by the Board of Directors of ONGC to executive levels across corporate offices, exploration basins, operational assets, "
            "and offshore institutes. It ensures transparent corporate governance, operational speed, and strict fiscal discipline "
            "consistent with Maharatna guidelines, CVC manuals, General Financial Rules (GFR), and the Companies Act, 2013."
        ),
        definitions=definitions,
        chapters=[c1, c2, c3, c4, c5],
        annexures=[annex1],
        amendment_history=amendments,
        real_excerpts_concordance=concordance
    )


def build_leave_rules() -> Rulebook:
    """Builds ONGC Leave Rules, 1995."""
    amendments = [
        AmendmentRecord("Leave 1968", "01-Jan-1968", "Oil & Natural Gas Commission", "Initial leave regulations under ONGC Act 1959."),
        AmendmentRecord("Leave 1995", "01-Apr-1995", "Board of Directors", "Re-notification of Leave Rules upon incorporation as Company under Companies Act 1956."),
        AmendmentRecord("Leave 2008 Amend", "01-Jan-2008", "Executive Committee", "Enhancement of Earned Leave accumulation ceiling to 300 days aligned with Central Govt."),
        AmendmentRecord("Leave 2017 Amend", "01-Jul-2017", "Board of Directors", "Revision of study leave bond conditions and encashment calculation based on 3rd PRC IDA basic pay."),
        AmendmentRecord("Leave 2023 Digital", "01-Oct-2023", "Director (HR)", "Mandatory electronic leave management system (e-Leave) on ESS portal.")
    ]

    definitions = {
        "Earned Leave (EL)": "Leave earned in respect of completed periods of duty, credited semi-annually in advance.",
        "Half Pay Leave (HPL)": "Leave earned on completion of service, calculated at the rate of 20 days per completed year of service.",
        "Commuted Leave": "Leave granted on medical certificate by commuting half-pay leave to full-pay leave, debited at double the rate against HPL balance.",
        "Extraordinary Leave (EOL)": "Leave granted in special circumstances without pay and allowances when no other leave is admissible.",
        "Study Leave": "Special leave granted for pursuing specialized academic or technical studies directly relevant to the operations of the Corporation.",
        "Encashment of Leave": "Payment of cash equivalent of Basic Pay plus IDA in lieu of accumulated unutilized Earned Leave / Half Pay Leave upon retirement or during service."
    }

    c1 = Chapter(
        1, "Preliminary, Commencement & Categories of Leave",
        [
            Clause(
                clause_ref="Clause 1.0",
                clause_title="Short Title and Commencement",
                clause_text=(
                    "1.1 These rules shall be called the 'ONGC Leave Rules, 1995' (Amended up to 2026).\n"
                    "1.2 They shall apply to all regular employees (executives and non-executives) of the Corporation across all establishments in India.\n"
                    "1.3 Right to Leave: Leave cannot be claimed as a matter of right. When the exigencies of public service so require, "
                    "the Competent Authority reserves the discretion to refuse, revoke, curtail, or postpone leave of any description."
                ),
                subclauses=[
                    Subclause("1.1", "Short Title", "Designated as ONGC Leave Rules, 1995."),
                    Subclause("1.2", "Universal Applicability", "Applicable to all regular workforce across all work centres."),
                    Subclause("1.3", "Discretionary Nature of Leave", "Leave subject to operational exigencies of the Corporation.")
                ],
                maps_to_question_ids="P4; P5",
                source_basis="J-09"
            ),
            Clause(
                clause_ref="Clause 2.0",
                clause_title="Categories of Leave",
                clause_text=(
                    "2.1 The following categories of leave are admissible under these rules:\n"
                    "   (a) Earned Leave (EL);\n"
                    "   (b) Half Pay Leave (HPL) / Commuted Leave;\n"
                    "   (c) Casual Leave (CL) & Special Casual Leave (SCL);\n"
                    "   (d) Extraordinary Leave (EOL);\n"
                    "   (e) Study Leave;\n"
                    "   (f) Maternity Leave & Paternity Leave;\n"
                    "   (g) Special Disability Leave for injuries sustained during hydrocarbon operations.\n"
                    "2.2 Combination of Leave: Any kind of leave under these rules may be granted in combination with or in continuation of "
                    "any other kind of leave, except Casual Leave, which shall not be combined with Earned Leave."
                ),
                subclauses=[
                    Subclause("2.1", "Recognized Leave Classes", "Full inventory of 7 recognized leave categories."),
                    Subclause("2.2", "Combination Restrictions", "Casual leave cannot be conjoined with earned leave.")
                ],
                maps_to_question_ids="P4",
                source_basis="J-09"
            )
        ]
    )

    c2 = Chapter(
        2, "Earned Leave (EL) Accrual, Accumulation & Encashment",
        [
            Clause(
                clause_ref="Clause 3.0",
                clause_title="Earned Leave Accrual & Accumulation",
                clause_text=(
                    "3.1 Annual Accrual Rate: Regular employees shall earn 30 (thirty) calendar days of Earned Leave in each calendar year.\n"
                    "3.2 Advance Credit: EL shall be credited in advance in two equal installments of 15 days each on 1st January and 1st July of every calendar year.\n"
                    "3.3 Maximum Accumulation Ceiling: Earned Leave may be accumulated up to a strict maximum ceiling of 300 (three hundred) days.\n"
                    "3.4 Treatment of Excess Accrual: Where an employee has 300 days of EL at the beginning of a half-year, the advance credit of 15 days "
                    "shall be maintained in a separate reserve. If the employee does not utilize leave during that half-year, the excess beyond 300 days "
                    "shall lapse on 30th June / 31st December, unless encashed in accordance with encashment rules."
                ),
                subclauses=[
                    Subclause("3.1", "30 Days Annual Rate", "Statutory accrual rate of 30 days per calendar year."),
                    Subclause("3.2", "Bi-Annual Advance Credit", "15 days credited on 1st Jan and 1st July."),
                    Subclause("3.3", "300-Day Ceiling", "Strict accumulation cap of 300 days."),
                    Subclause("3.4", "Lapse of Excess Balance", "Unencashed days beyond 300 lapse automatically.")
                ],
                maps_to_question_ids="P4",
                source_basis="J-09"
            ),
            Clause(
                clause_ref="Clause 4.0",
                clause_title="Encashment of Earned Leave",
                clause_text=(
                    "4.1 Encashment on Superannuation: An employee retiring on superannuation, voluntary retirement, or upon death in service "
                    "shall be entitled to receive lump-sum cash equivalent of unutilized Earned Leave standing to their credit, subject to a maximum "
                    "aggregate ceiling of 300 (three hundred) days.\n"
                    "4.2 Encashment Calculation Formula: The cash equivalent of leave salary for encashment shall be calculated strictly as:\n"
                    "   Cash Amount = [(Basic Pay on date of retirement + IDA applicable) / 30] × Number of Unutilized EL Days (up to max 300).\n"
                    "   No house rent allowance (HRA), cafeteria perks, or performance related pay (PRP) shall be included in the encashment calculation.\n"
                    "4.3 Running Encashment during Service: An employee may encash up to 30 days EL once in a calendar year, provided a minimum balance "
                    "of 30 days EL is retained in their leave account after such encashment."
                ),
                subclauses=[
                    Subclause("4.1", "300-Day Retirement Cap", "Maximum 300 days encashable at superannuation."),
                    Subclause("4.2", "Statutory Computation Formula", "(Basic Pay + IDA) / 30 per encashable day."),
                    Subclause("4.3", "Running In-Service Encashment", "Annual encashment permitted subject to retaining 30-day balance.")
                ],
                maps_to_question_ids="P4",
                source_basis="J-09"
            )
        ]
    )

    c3 = Chapter(
        3, "Half Pay Leave (HPL) & Commuted Leave",
        [
            Clause(
                clause_ref="Clause 5.0",
                clause_title="Half Pay Leave (HPL) Accrual & Encashment",
                clause_text=(
                    "5.1 Accrual Rate: Half Pay Leave (HPL) shall be credited at the rate of 20 (twenty) days for each completed year of service, "
                    "credited in advance as 10 days on 1st January and 10 days on 1st July.\n"
                    "5.2 Commuted Leave: HPL may be converted into Commuted Leave on medical certificate at the option of the employee. When commuted leave "
                    "is granted, twice the amount of such leave shall be debited against the HPL balance, and the employee shall receive full pay.\n"
                    "5.3 Encashment of HPL at Retirement: Where the accumulated Earned Leave at retirement falls short of the 300-day ceiling, "
                    "unutilized HPL may be encashed to bridge the deficit up to the combined aggregate ceiling of 300 days, subject to DPE guidelines. "
                    "For such encashment, two days of HPL shall equal one day of cash salary (equivalent to half pay)."
                ),
                subclauses=[
                    Subclause("5.1", "20 Days Annual HPL", "Accrual of 20 days per completed year of service."),
                    Subclause("5.2", "Commuted Medical Conversion", "2 days HPL debited for 1 day commuted full pay."),
                    Subclause("5.3", "Deficit Encashment Bridge", "HPL encashable to make up shortfall in 300-day aggregate limit.")
                ],
                maps_to_question_ids="P4",
                source_basis="J-09"
            )
        ]
    )

    c4 = Chapter(
        4, "Study Leave & Service Bond Obligations",
        [
            Clause(
                clause_ref="Clause 6.0",
                clause_title="Study Leave Eligibility & Approval",
                clause_text=(
                    "6.1 Purpose & Eligibility: Study leave may be granted to an executive to undergo specialized postgraduate study, executive fellowship, "
                    "or research directly relevant to the hydrocarbon exploration, reservoir development, drilling engineering, or corporate finance operations "
                    "of the Corporation.\n"
                    "6.2 Minimum Service Prerequisite: An executive must have completed a minimum of 5 (five) years of continuous regular service in ONGC "
                    "to be eligible for consideration for study leave.\n"
                    "6.3 Maximum Duration: The maximum duration of study leave that may be granted during an executive's entire service shall be 24 (twenty-four) months. "
                    "This may be extended to a maximum of 36 months for an approved doctoral research program (Ph.D.) with the specific sanction of Director (HR).\n"
                    "6.4 Competent Sanctioning Authority: Study leave within India shall be sanctioned by Director (HR); study leave outside India shall require "
                    "the approval of the Chairman & Managing Director (CMD)."
                ),
                subclauses=[
                    Subclause("6.1", "Hydrocarbon Domain Relevance", "Study must directly benefit ONGC core business areas."),
                    Subclause("6.2", "Five-Year Service Prerequisite", "Minimum 5 years continuous service required."),
                    Subclause("6.3", "24-Month Maximum Limit", "Capped at 24 months (36 months for Ph.D.)."),
                    Subclause("6.4", "Sanctioning Authority", "Director (HR) for domestic studies; CMD for overseas.")
                ],
                maps_to_question_ids="P5",
                source_basis="J-10"
            ),
            Clause(
                clause_ref="Clause 7.0",
                clause_title="Study Leave Service Bond",
                clause_text=(
                    "7.1 Mandatory Service Bond Execution: Every executive granted study leave shall execute a formal legal service bond with two solvent sureties "
                    "prior to proceeding on leave, binding themselves to serve the Corporation for a minimum period of 3 (three) completed years upon resumption "
                    "of duty following completion of the study course.\n"
                    "7.2 Financial Penalty on Breach: In the event of resignation, abandonment of service, or dismissal within 3 years of returning from study leave, "
                    "the executive shall be liable to refund in full to the Corporation:\n"
                    "   (a) The entire amount of leave salary, allowances, tuition fees, and book grants paid during the period of study leave;\n"
                    "   (b) Travel costs, airfares, and visa fees incurred by the Corporation; and\n"
                    "   (c) Compound interest thereon calculated at the prevailing commercial bank lending rate plus 2% per annum from the date of payment."
                ),
                subclauses=[
                    Subclause("7.1", "Three-Year Service Bond", "Mandatory bond to serve 3 years after study leave."),
                    Subclause("7.2", "Full Financial Clawback", "Mandatory refund of all salary, fees, allowances, and interest on breach.")
                ],
                maps_to_question_ids="P5",
                source_basis="J-10"
            )
        ]
    )

    c5 = Chapter(
        5, "Extraordinary Leave, Rule 14(5) & Disciplinary Forfeiture",
        [
            Clause(
                clause_ref="Clause 8.0",
                clause_title="Extraordinary Leave (EOL) & Rule 14(5)",
                clause_text=(
                    "8.1 Extraordinary Leave without Pay: EOL may be granted when no other leave is admissible, or when the employee applies in writing for EOL. "
                    "No salary, perks, or allowances shall accrue during EOL.\n"
                    "8.2 Maximum Continuous Absence Ceiling: The continuous period of absence from duty on leave of any description (including EOL) shall not exceed "
                    "5 (five) continuous years. Any employee remaining absent beyond 5 years shall be deemed to have abandoned service.\n"
                    "8.3 Deemed Resignation under Rule 14(5): Remaining absent from duty without prior sanctioned leave for a continuous period exceeding 90 days "
                    "or failing to report upon expiry of sanctioned leave shall be deemed to constitute voluntary abandonment and resignation under Rule 14(5) "
                    "of ONGC Service Rules / CDA Rules, 1994, warranting initiation of major penalty disciplinary proceedings."
                ),
                subclauses=[
                    Subclause("8.1", "EOL Provisions", "Granted without allowances when no leave is available."),
                    Subclause("8.2", "Five-Year Continuous Cap", "Maximum continuous absence capped at 5 years."),
                    Subclause("8.3", "Rule 14(5) Deemed Resignation", "Absence over 90 days treated as deemed resignation under Rule 14(5).")
                ],
                maps_to_question_ids="P4",
                source_basis="J-10"
            ),
            Clause(
                clause_ref="Clause 9.0",
                clause_title="Forfeiture on Disciplinary Dismissal",
                clause_text=(
                    "9.1 Punitive Forfeiture of Leave Credit: Where an employee is dismissed, removed, or compulsorily retired from the service of the Corporation "
                    "as a measure of major penalty under Rule 14 of the ONGC Conduct, Discipline and Appeal Rules, 1994, all accumulated Earned Leave and "
                    "Half Pay Leave standing to their credit shall automatically lapse and be completely forfeited.\n"
                    "9.2 Absolute Bar on Encashment: No cash equivalent, encashment, or monetary compensation in lieu of unutilized leave shall be admissible "
                    "or payable to any employee dismissed or removed for disciplinary misconduct.\n"
                    "9.3 Recovery of Erroneous Encashment: Where an employee facing dismissal has previously availed running encashment during the period "
                    "of alleged misconduct, the Corporation reserves the right to adjust and recover such amounts from other statutory terminal dues."
                ),
                subclauses=[
                    Subclause("9.1", "Automatic Forfeiture", "Complete forfeiture of leave credit upon disciplinary dismissal."),
                    Subclause("9.2", "Bar on Encashment", "Strict prohibition on terminal leave encashment for dismissed employees."),
                    Subclause("9.3", "Terminal Recovery", "Recovery from terminal dues permitted.")
                ],
                maps_to_question_ids="P4",
                source_basis="P1-01"
            )
        ]
    )

    annex1 = Annexure(
        "Schedule I", "Leave Entitlement & Accumulation Summary",
        "Comprehensive matrix of leave types, annual entitlements, ceilings, and encashability under ONGC Leave Rules.",
        table_headers=["Category of Leave", "Annual Accrual", "Credit Frequency", "Max Accumulation Ceiling", "Encashability at Retirement"],
        table_rows=[
            ["Earned Leave (EL)", "30 Days", "15 days on Jan 1 & Jul 1", "300 Days", "Yes (up to 300 days)"],
            ["Half Pay Leave (HPL)", "20 Days", "10 days on Jan 1 & Jul 1", "No Ceiling", "Yes (to cover EL shortfall up to 300 days combined)"],
            ["Commuted Leave", "Against HPL (2:1)", "As required on Medical Cert.", "Limited by HPL balance", "No (consumed as medical leave)"],
            ["Casual Leave (CL)", "12 Days (15 in NE)", "Annual calendar year", "Zero (Lapses Dec 31)", "No encashment"],
            ["Study Leave", "Max 24 Months", "Once in service", "24 Months (36 for Ph.D.)", "No (requires 3-year service bond)"],
            ["Maternity Leave", "180 Days", "Per pregnancy (up to 2)", "180 Days", "No encashment"],
            ["Paternity Leave", "15 Days", "Within 6 months of birth", "15 Days", "No encashment"]
        ]
    )

    concordance = [
        {"doc_id": "J-09", "title": "Gujarat HC Judgment (ONGC v. D.C. Shukla)", "clause_ref": "Clause 1.0, 3.0, 4.0, 5.0", "verbatim_quote": "Leave Rules"},
        {"doc_id": "J-10", "title": "Gauhati HC Judgment (Karna Kishore Deb Barma v. ONGC)", "clause_ref": "Clause 6.0, 7.0, 8.0", "verbatim_quote": "Study Leave Service Bond"}
    ]

    return Rulebook(
        doc_id="Leave Rules",
        title="ONGC Leave Rules, 1995",
        short_title="ONGC Leave Rules",
        ref_code="ONGC/CORP-HR/LR/1995-REV3",
        effective_date="1st April 1995 (Amended up to 31st March 2026)",
        issuer="Corporate Employee Relations Group, Tel Bhavan, Dehradun",
        approving_authority="Executive Committee & Board of Directors, ONGC",
        classification="INTERNAL CONTROLLED DOCUMENT / DEMO RECONSTRUCTION",
        preamble=(
            "The ONGC Leave Rules, 1995 govern the grant, accrual, accumulation, encashment, and revocation of leave for regular employees "
            "of the Corporation. Framed in accordance with statutory guidelines for Central Public Sector Enterprises, DPE directives, and "
            "judicial precedents, these rules ensure adequate rest, recuperation, academic advancement, and medical security while maintaining "
            "operational vigilance across continuous oilfield operations."
        ),
        definitions=definitions,
        chapters=[c1, c2, c3, c4, c5],
        annexures=[annex1],
        amendment_history=amendments,
        real_excerpts_concordance=concordance
    )


def build_rp_regulations() -> Rulebook:
    """Builds Modified Recruitment & Promotion Regulations 1980 & DPC Guidelines."""
    amendments = [
        AmendmentRecord("R&P 1980", "01-Jan-1980", "Commission", "Promulgation of Modified R&P Regulations under ONGC Act 1959."),
        AmendmentRecord("R&P 1997", "01-Jul-1997", "Board of Directors", "Introduction of dual-track progression (Time-Bound E1–E4 and Merit DPC E4–E9)."),
        AmendmentRecord("R&P 2011", "01-Apr-2011", "Board of Directors", "Institutionalization of mandatory North-East hard station tenure for E4→E5 merit review."),
        AmendmentRecord("R&P 2018", "01-Jan-2018", "Executive Committee", "Alignment of qualification benchmarks and DPC scoring weights with 3rd PRC pay structures."),
        AmendmentRecord("R&P 2024", "15-May-2024", "Board of Directors", "Digitization of e-APAR benchmarking and refinement of sealed cover procedures.")
    ]

    definitions = {
        "Executive Cadre": "Regular officers holding appointments in Pay Scales E0 through E9.",
        "Residency Period": "The minimum number of completed qualifying years of substantive service in a lower grade required before becoming eligible for consideration for promotion to the next higher grade.",
        "Time-Bound Promotion": "Progression through executive grades E1 to E4 based on completion of specified residency and attainment of prescribed APAR benchmark.",
        "Merit Promotion": "Selection-based promotion through competitive evaluation by a Departmental Promotion Committee (DPC) based on composite evaluation of APARs, professional interview, qualification, and leadership assessment.",
        "Zone of Consideration": "The number of eligible senior candidates considered for a specified number of merit vacancies, normally in the ratio of 1:3.",
        "Sealed Cover Procedure": "The procedure whereby DPC findings regarding an officer facing vigilance inquiry, charge-sheet, or court prosecution are kept in a sealed envelope until exoneration.",
        "Benchmark APAR": "The minimum cumulative appraisal score required across the qualifying residency years (e.g. 'Very Good' or 70%)."
    }

    c1 = Chapter(
        1, "Executive Cadre Structure & General Eligibility",
        [
            Clause(
                clause_ref="Clause 1.0",
                clause_title="Executive Cadre Structure",
                clause_text=(
                    "1.1 Structure of Executive Cadre: The executive hierarchy of the Corporation is organized into ten distinct grades:\n"
                    "   (a) E0: Assistant Officer / Graduate Trainee (₹30,000–1,20,000);\n"
                    "   (b) E1: Assistant Executive Engineer (AEE) / Officer (₹60,000–1,80,000);\n"
                    "   (c) E2: Assistant Executive Engineer (AEE) / Deputy Manager (₹70,000–2,00,000);\n"
                    "   (d) E3: Executive Engineer (EE) / Manager (₹80,000–2,20,000);\n"
                    "   (e) E4: Superintending Engineer (SE) / Chief Manager (₹90,000–2,40,000);\n"
                    "   (f) E5: Deputy General Manager (DGM) (₹1,00,000–2,60,000);\n"
                    "   (g) E6: Joint General Manager (JGM) / Addl. GM (₹1,20,000–2,80,000);\n"
                    "   (h) E7: General Manager (GM) (₹1,20,000–2,80,000);\n"
                    "   (i) E8: Chief General Manager (CGM) (₹1,30,000–2,80,000);\n"
                    "   (j) E9: Executive Director (ED) / Group General Manager (₹1,50,000–3,00,000).\n"
                    "1.2 Professional Disciplines: Cadres are established across core technical and support disciplines: Drilling (DISC-DRL), "
                    "Production (DISC-PRD), Reservoir (DISC-RES), Geology (DISC-GEO), Geophysics Surface & Wells (DISC-GPS, DISC-GPW), Chemistry (DISC-CHM), "
                    "Mechanical (DISC-MEC), Electrical (DISC-ELE), Instrumentation (DISC-INS), Civil (DISC-CIV), Marine (DISC-MAR), Well Services (DISC-WEL), "
                    "Finance & Accounts (DISC-FIN), Human Resources (DISC-HR), Materials Management (DISC-MM), and Support Services."
                ),
                subclauses=[
                    Subclause("1.1", "Ten Executive Grades", "Defines grades E0 through E9 with pay scales."),
                    Subclause("1.2", "Cadre Disciplines", "Enumerates 20+ specialized disciplines matching world_bible.")
                ],
                maps_to_question_ids="E4; P10",
                source_basis="P1-05"
            )
        ]
    )

    c2 = Chapter(
        2, "Time-Bound Promotion Channel (E1 to E4)",
        [
            Clause(
                clause_ref="Clause 2.0",
                clause_title="Time-Bound Promotion Channel (E1→E4)",
                clause_text=(
                    "2.1 Qualifying Residency Requirements: Promotions within the junior executive ranks (E1 through E4) shall be governed "
                    "by the Time-Bound Promotion Channel subject to completing prescribed residency and meeting the APAR benchmark:\n"
                    "   (a) Promotion from E1 to E2: 3 (three) completed years of qualifying residency service at Grade E1.\n"
                    "   (b) Promotion from E2 to E3: 3 (three) completed years of qualifying residency service at Grade E2.\n"
                    "   (c) Promotion from E3 to E4: 3 to 4 (three to four) completed years of qualifying residency service at Grade E3.\n"
                    "2.2 Non-Vacancy Based Progression: In the time-bound channel, promotions are not constrained by fixed budgetary post vacancies; "
                    "all officers who complete the qualifying residency and achieve the required performance rating and vigilance clearance shall be promoted.\n"
                    "2.3 Effective Date of Promotion: Time-bound promotions shall take effect from 1st January or 1st July following completion of qualifying residency."
                ),
                subclauses=[
                    Subclause("2.1", "Residency Requirements", "3 years at E1, 3 years at E2, and 3-4 years at E3."),
                    Subclause("2.2", "Non-Vacancy Driven", "Guaranteed advancement upon meeting performance threshold."),
                    Subclause("2.3", "Effective Dates", "Effective January 1 or July 1 bi-annually.")
                ],
                maps_to_question_ids="E4; P10; H5_FU3",
                source_basis="J-15"
            ),
            Clause(
                clause_ref="Clause 3.0",
                clause_title="APAR Benchmark for Time-Bound Promotion",
                clause_text=(
                    "3.1 Performance Benchmark Threshold: To qualify for time-bound promotion, an executive must maintain a consistent track record "
                    "of satisfactory performance across the qualifying residency years:\n"
                    "   (a) For E1→E2: Minimum cumulative rating of 'Good' (score ≥ 3.0 / 60%) in the annual e-APAR ratings for the preceding 3 years.\n"
                    "   (b) For E2→E3: Minimum cumulative rating of 'Good' to 'Very Good' (score ≥ 3.5 / 70%) across the preceding 3 years, with no adverse remark.\n"
                    "   (c) For E3→E4: Minimum cumulative rating of 'Very Good' (score ≥ 3.5 / 70%) across the preceding residency period.\n"
                    "3.2 Adverse Remark Disqualification: Any uncommunicated or sustained adverse remark, or an APAR rating below 'Good' in any single year, "
                    "shall result in deferment of promotion by one year until the benchmark is restored."
                ),
                subclauses=[
                    Subclause("3.1", "APAR Benchmark Scores", "Good for E1→E2; Very Good for E2→E3 and E3→E4."),
                    Subclause("3.2", "Adverse Remarks Bar", "Adverse rating defers promotion by 12 months.")
                ],
                maps_to_question_ids="E4; P10",
                source_basis="J-15"
            )
        ]
    )

    c3 = Chapter(
        3, "Merit Promotion Channel (E4 to E9) & Hard-Station Prerequisite",
        [
            Clause(
                clause_ref="Clause 4.0",
                clause_title="Merit Promotion Channel (E4→E5, E5→E6)",
                clause_text=(
                    "4.1 Selection by Merit: Promotions from Superintending Engineer / Chief Manager (Grade E4) to Deputy General Manager (Grade E5), "
                    "and through higher grades (E6, E7, E8, E9), are strictly vacancy-based and governed by the Merit Promotion Channel through a Departmental Promotion Committee (DPC).\n"
                    "4.2 Zone of Consideration: The zone of consideration of eligible candidates shall be determined in the ratio of 1:3 of declared vacancies "
                    "based on inter-se seniority within the respective discipline.\n"
                    "4.3 Evaluation Matrix: DPC evaluation shall be based on a 100-point composite matrix:\n"
                    "   (a) APAR Track Record (last 5 years): 50 Points;\n"
                    "   (b) Professional Competency & Technical Assessment / Interview: 30 Points;\n"
                    "   (c) Educational Qualifications & Specialized Certifications: 10 Points;\n"
                    "   (d) Seniority & Experience Weighting: 10 Points."
                ),
                subclauses=[
                    Subclause("4.1", "Merit & Vacancy Based", "Promotions E4→E5 and above are merit-selected."),
                    Subclause("4.2", "1:3 Zone Ratio", "Standard 1:3 ratio based on seniority."),
                    Subclause("4.3", "100-Point Matrix", "50 APAR + 30 Interview + 10 Qualifications + 10 Seniority.")
                ],
                maps_to_question_ids="P12",
                source_basis="J-15"
            ),
            Clause(
                clause_ref="Clause 5.0",
                clause_title="Mandatory Hard-Station Prerequisite for Promotion",
                clause_text=(
                    "5.1 Prerequisite for Consideration to Grade E5: No executive belonging to technical cadres (Drilling, Production, Reservoir, Geology, "
                    "Geophysics, Engineering) shall be considered eligible for empanelment or promotion from Grade E4 to Grade E5 (Deputy General Manager) "
                    "unless they have successfully completed at least one full tenure of 3 (three) years in a designated Category 'C' Hard Station or North-East work centre "
                    "(Assam Asset, Tripura Asset, Bokaro CBM, Rajasthan Jodhpur, or 14/14 Offshore Production Duty).\n"
                    "5.2 Strict Enforcement: Officers who have reached eligibility residency at E4 but have never completed a Category 'C' hard station posting "
                    "shall be bypassed in the DPC merit review until such mandatory hard-station tenure is completed."
                ),
                subclauses=[
                    Subclause("5.1", "3-Year Cat C Mandatory Stint", "Three years Category C hard station service required before E5 promotion."),
                    Subclause("5.2", "Bypass Clause", "Failure to complete hard posting blocks promotion to DGM.")
                ],
                maps_to_question_ids="P12",
                source_basis="J-15"
            )
        ]
    )

    c4 = Chapter(
        4, "DPC Constitution, Vigilance & Sealed Cover Procedures",
        [
            Clause(
                clause_ref="Clause 6.0",
                clause_title="Departmental Promotion Committee (DPC) Constitution",
                clause_text=(
                    "6.1 Composition: The Departmental Promotion Committee shall be constituted as follows:\n"
                    "   (a) For E4→E5 & E5→E6: Chaired by Director (HR); members include Functional Director of respective discipline, "
                    "ED-Chief ER, external technical expert, and a representative from SC/ST/OBC community.\n"
                    "   (b) For E7→E9: Chaired by CMD; members include all Functional Directors and external government expert.\n"
                    "6.2 Quorum: The quorum for DPC meetings shall be Chairman plus at least two members, including the SC/ST representative."
                ),
                subclauses=[
                    Subclause("6.1", "Committee Makeup", "Director HR/CMD, Functional Directors, external experts, and SC/ST member."),
                    Subclause("6.2", "Mandatory Quorum", "Quorum rules ensure fair representation.")
                ],
                maps_to_question_ids="D3",
                source_basis="J-15"
            ),
            Clause(
                clause_ref="Clause 7.0",
                clause_title="Vigilance Clearance as Pre-Condition",
                clause_text=(
                    "7.1 Mandatory Vigilance Clearance: Clear and unconditional vigilance clearance from the Chief Vigilance Officer (CVO) "
                    "is a non-negotiable mandatory prerequisite for placing any officer on the promotion panel or releasing promotion orders.\n"
                    "7.2 Disqualifying Vigilance Status: An officer shall not be granted promotion if: (a) under suspension; (b) a charge-sheet "
                    "for major penalty disciplinary proceedings under CDA Rule 14 has been issued; or (c) prosecution for a criminal charge is pending."
                ),
                subclauses=[
                    Subclause("7.1", "CVO Clearance Prerequisite", "No promotion without affirmative clearance from CVO."),
                    Subclause("7.2", "Disqualifying Circumstances", "Suspension, major penalty charge-sheet, criminal prosecution.")
                ],
                maps_to_question_ids="D3",
                source_basis="P1-01"
            ),
            Clause(
                clause_ref="Clause 8.0",
                clause_title="Confidentiality of DPC Proceedings & Sealed Cover",
                clause_text=(
                    "8.1 Strict Secrecy of DPC Deliberations: The proceedings, minutes, individual candidate scoring sheets, and recommendations "
                    "of the Departmental Promotion Committee are top-secret privileged documents. No candidate or third party has any right to inspect "
                    "or access DPC deliberations prior to official release of the promotion panel.\n"
                    "8.2 Sealed Cover Procedure: Where an officer eligible for promotion is facing disciplinary proceedings, under suspension, "
                    "or under criminal prosecution at the time of DPC, the DPC shall assess their suitability, but its findings shall be placed "
                    "in a sealed cover envelope marked 'Findings regarding [Name / PERNR]'.\n"
                    "8.3 Opening of Sealed Cover: If the officer is completely exonerated of all charges, the sealed cover shall be opened, and if found fit, "
                    "notional seniority and promotion shall be granted from the date their immediate junior was promoted."
                ),
                subclauses=[
                    Subclause("8.1", "Absolute Secrecy", "DPC minutes are classified top secret."),
                    Subclause("8.2", "Sealed Cover Protocol", "Adjudication sealed during pending inquiry."),
                    Subclause("8.3", "Post-Exoneration Restoration", "Retrospective seniority upon complete clearance.")
                ],
                maps_to_question_ids="D3",
                source_basis="J-15"
            )
        ]
    )

    annex1 = Annexure(
        "Schedule I", "Executive Cadre Progression Matrix",
        "Qualifying residency, promotion mode, evaluation criteria, and salary bands across grades E0 to E9.",
        table_headers=["Grade", "Designation", "Promotion Mode", "Min Residency", "Evaluation Body", "Pay Scale (IDA ₹)"],
        table_rows=[
            ["E0", "Assistant Officer / Graduate Trainee", "Time-Bound / Confirmation", "1 Year", "Screening & Exam", "30,000–1,20,000"],
            ["E1", "Assistant Executive Engineer (AEE)", "Time-Bound", "3 Years", "APAR Assessment (Good)", "60,000–1,80,000"],
            ["E2", "Deputy Manager / AEE", "Time-Bound", "3 Years", "APAR Assessment (V. Good)", "70,000–2,00,000"],
            ["E3", "Executive Engineer / Manager", "Time-Bound", "3–4 Years", "APAR Assessment (V. Good)", "80,000–2,20,000"],
            ["E4", "Superintending Engineer / Chief Mgr", "Merit (DPC)", "4 Years", "DPC + Hard Stn Prereq", "90,000–2,40,000"],
            ["E5", "Deputy General Manager (DGM)", "Merit (DPC)", "4 Years", "DPC Interview & Merit", "1,00,000–2,60,000"],
            ["E6", "Joint General Manager (JGM)", "Merit (DPC)", "3 Years", "Senior DPC Quorum", "1,20,000–2,80,000"],
            ["E7", "General Manager (GM)", "Merit (DPC)", "3 Years", "Apex Leadership DPC", "1,20,000–2,80,000"],
            ["E8", "Chief General Manager (CGM)", "Merit (DPC)", "3 Years", "Apex Board Committee", "1,30,000–2,80,000"],
            ["E9", "Executive Director (ED)", "Merit / Selection", "2 Years", "CMD & Board Committee", "1,50,000–3,00,000"]
        ]
    )

    concordance = [
        {"doc_id": "J-15", "title": "Supreme Court / Delhi HC (Dwarika Prasad v. ONGC)", "clause_ref": "Clause 2.0, 3.0, 4.0, 5.0, 6.0, 8.0", "verbatim_quote": "Modified Recruitment and Promotion Regulations"},
        {"doc_id": "P1-05", "title": "Recruitment Advertisement 1/2024 (GT)", "clause_ref": "Clause 1.0", "verbatim_quote": "Advt. No. 1/2024 (R&P)"},
        {"doc_id": "P1-01", "title": "ONGC Conduct, Discipline and Appeal Rules, 1994", "clause_ref": "Clause 7.0, 8.0", "verbatim_quote": "Rule 14 (Major Penalties)"}
    ]

    return Rulebook(
        doc_id="R&P/Promotion",
        title="Modified Recruitment & Promotion Regulations 1980 & Service Rules 1995",
        short_title="ONGC R&P Regulations",
        ref_code="ONGC/CORP-HR/RP/1980-REV4",
        effective_date="1st January 1980 (Amended up to 31st March 2026)",
        issuer="Corporate Recruitment & Promotion Group, Tel Bhavan, Dehradun",
        approving_authority="Board of Directors, ONGC",
        classification="INTERNAL CONTROLLED DOCUMENT / DEMO RECONSTRUCTION",
        preamble=(
            "The Modified Recruitment and Promotion Regulations, 1980 and associated Departmental Promotion Committee (DPC) guidelines "
            "govern the intake, residency, cadre structuring, time-bound advancement, and competitive merit selection of executives "
            "across all engineering, geosciences, financial, and administrative disciplines in ONGC. Designed to reward high operational "
            "performance and ensure meritocratic progression while balancing arduous field postings, this rulebook establishes the legal "
            "and procedural standards for executive career advancement."
        ),
        definitions=definitions,
        chapters=[c1, c2, c3, c4],
        annexures=[annex1],
        amendment_history=amendments,
        real_excerpts_concordance=concordance
    )


def build_hr_manual() -> Rulebook:
    """Builds ONGC HR Manual: Designations, Pay Scales & Service Conditions."""
    amendments = [
        AmendmentRecord("HRM 1995", "01-Apr-1995", "Board of Directors", "Original post-corporatization compilation of service rules and pay scales."),
        AmendmentRecord("HRM 2008", "01-Jan-2008", "Board of Directors", "Revision of executive pay scales aligned with 2nd PRC DPE OM."),
        AmendmentRecord("HRM 2017", "03-Aug-2017", "Board of Directors", "Implementation of 3rd PRC Pay Revision (DPE OM 03.08.2017), establishing ₹60k–180k E1 scale."),
        AmendmentRecord("HRM 2021", "01-Jan-2021", "Executive Committee", "Digital employee self-service (ESS) data security and compensation confidentiality code."),
        AmendmentRecord("HRM 2025", "01-Apr-2025", "Director (HR)", "Update of cafeteria perks structure and resignation notice rules.")
    ]

    definitions = {
        "Executive Cadre": "Regular officers holding appointments in Pay Scales E0 through E9.",
        "Industrial Dearness Allowance (IDA)": "Dearness allowance calculated quarterly based on the All India Consumer Price Index (AICPI) per DPE guidelines.",
        "Cafeteria Approach": "A flexible allowance system allowing executives to choose perks and allowances up to a maximum ceiling of 35% of Basic Pay.",
        "Employee Self-Service (ESS)": "Authorized corporate digital web portal enabling employees to access their own personnel data, payslips, leave balances, and APARs.",
        "Confidential Personal Information": "Information relating to individual compensation, income tax details, performance appraisal scores, disciplinary matters, or medical records of other employees.",
        "Notice Period": "Mandatory period of 3 calendar months required to be served by an employee upon tendering resignation."
    }

    c1 = Chapter(
        1, "Executive Hierarchy, Designations & Cadre Classification",
        [
            Clause(
                clause_ref="Clause 1.0",
                clause_title="Standard Executive Hierarchy & Designations",
                clause_text=(
                    "1.1 Executive Hierarchy: The executive structure of the Corporation comprises 10 hierarchical levels from Grade E0 to Grade E9:\n"
                    "   (a) E0: Assistant Officer / Graduate Trainee;\n"
                    "   (b) E1: Assistant Executive Engineer (AEE) / Chemist / Geologist / Geophysicist / Materials Officer / Finance Officer / HR Officer;\n"
                    "   (c) E2: Assistant Executive Engineer (AEE) / Deputy Manager;\n"
                    "   (d) E3: Executive Engineer (EE) / Manager;\n"
                    "   (e) E4: Superintending Engineer (SE) / Chief Manager;\n"
                    "   (f) E5: Deputy General Manager (DGM);\n"
                    "   (g) E6: Joint General Manager (JGM) / Additional General Manager;\n"
                    "   (h) E7: General Manager (GM);\n"
                    "   (i) E8: Chief General Manager (CGM);\n"
                    "   (j) E9: Executive Director (ED) / Group General Manager.\n"
                    "1.2 Top Management: Functional Directors (Director Finance, Director Exploration, Director Onshore, Director Offshore, "
                    "Director Production, Director HR) and the Chairman & Managing Director (CMD) constitute Board-level leadership."
                ),
                subclauses=[
                    Subclause("1.1", "Standard Designations", "E0 to E9 functional designations across engineering and finance."),
                    Subclause("1.2", "Board Level Officers", "CMD and Functional Directors.")
                ],
                maps_to_question_ids="D1",
                source_basis="P1-05"
            )
        ]
    )

    c2 = Chapter(
        2, "Pay Scales, Dearness Allowance & Cafeteria Perks",
        [
            Clause(
                clause_ref="Clause 2.0",
                clause_title="IDA Pay Scales by Grade",
                clause_text=(
                    "2.1 3rd PRC Pay Revision Scales: In accordance with DPE OM No. W-02/0028/2017-DPE(WC)-GL-XIII/17 dated 03.08.2017, "
                    "the revised IDA pay scales for executive grades in ONGC are:\n"
                    "   • Grade E0: ₹30,000 – ₹1,20,000 (Annual increment 3%)\n"
                    "   • Grade E1: ₹60,000 – ₹1,80,000 (Entry Grade for Graduate Trainees via GATE)\n"
                    "   • Grade E2: ₹70,000 – ₹2,00,000\n"
                    "   • Grade E3: ₹80,000 – ₹2,20,000\n"
                    "   • Grade E4: ₹90,000 – ₹2,40,000\n"
                    "   • Grade E5: ₹1,00,000 – ₹2,60,000\n"
                    "   • Grade E6: ₹1,20,000 – ₹2,80,000\n"
                    "   • Grade E7: ₹1,20,000 – ₹2,80,000\n"
                    "   • Grade E8: ₹1,30,000 – ₹2,80,000\n"
                    "   • Grade E9: ₹1,50,000 – ₹3,00,000\n"
                    "   • Functional Director: ₹1,80,000 – ₹3,40,000\n"
                    "   • CMD: ₹2,00,000 – ₹3,70,000\n"
                    "2.2 Industrial Dearness Allowance: IDA is payable quarterly on Basic Pay based on price index movements per DPE quarterly notifications.\n"
                    "2.3 Cafeteria Approach Allowances: Perks and allowances under the cafeteria system are capped at 35% of Basic Pay, "
                    "encompassing medical allowance, professional development grant, conveyance, and child education support."
                ),
                subclauses=[
                    Subclause("2.1", "Standard Pay Scales", "Full 3rd PRC scale alignment E0 through E9."),
                    Subclause("2.2", "Quarterly IDA", "Quarterly revision based on AICPI."),
                    Subclause("2.3", "35% Cafeteria Cap", "Perks and allowances capped at 35% of Basic Pay.")
                ],
                maps_to_question_ids="D1",
                source_basis="G-01"
            )
        ]
    )

    c3 = Chapter(
        3, "Probation, Confirmation & Seniority Norms",
        [
            Clause(
                clause_ref="Clause 3.0",
                clause_title="Probation, Confirmation & Seniority",
                clause_text=(
                    "3.1 Probation Period: Every Graduate Trainee appointed at Grade E1 shall be on probation for a period of 1 (one) year "
                    "from the date of reporting for duty. The probation period may be extended up to a maximum of one additional year if performance "
                    "or conduct is found unsatisfactory.\n"
                    "3.2 Confirmation Protocol: Upon successful completion of the probation period, satisfactory appraisal report, and passing "
                    "the prescribed induction examination, the executive shall be formally confirmed in writing in Grade E1.\n"
                    "3.3 Inter-se Seniority: The relative seniority of Graduate Trainees appointed in a recruitment batch shall be determined strictly "
                    "by their merit ranking in the final selection examination / GATE score, and not by the date of joining."
                ),
                subclauses=[
                    Subclause("3.1", "One-Year Probation", "1-year initial probation for direct recruits."),
                    Subclause("3.2", "Confirmation Assessment", "Formal assessment required prior to confirmation."),
                    Subclause("3.3", "Merit Rank Seniority", "Seniority anchored to recruitment rank.")
                ],
                maps_to_question_ids="E4",
                source_basis="P1-05"
            )
        ]
    )

    c4 = Chapter(
        4, "Digital Access, Privacy & Confidentiality of Information",
        [
            Clause(
                clause_ref="Clause 4.0",
                clause_title="Employee Self-Service (ESS) Portal Access",
                clause_text=(
                    "4.1 Authorized Digital Channel: The Employee Self-Service (ESS) web portal is the sole authorized digital system for employees "
                    "to access their individual employment and payroll records.\n"
                    "4.2 Scope of Personal Self-Service Access: Through the authenticated ESS portal, an employee is authorized to view only their OWN personal records:\n"
                    "   (a) Monthly payslip and annual Form 16 / tax computation statement;\n"
                    "   (b) Leave account balance and application status;\n"
                    "   (c) Personal e-APAR scorecards and self-appraisal submissions;\n"
                    "   (d) Personal provident fund (EPF) and PRBS pension corpus balances;\n"
                    "   (e) Official posting history and current work centre profile."
                ),
                subclauses=[
                    Subclause("4.1", "ESS as Sole Channel", "ESS is the authenticated self-service portal."),
                    Subclause("4.2", "Scope of Individual Access", "Access restricted strictly to own payslip, leave, and APAR.")
                ],
                maps_to_question_ids="M3_FU1",
                source_basis="P1-01"
            ),
            Clause(
                clause_ref="Clause 5.0",
                clause_title="Confidentiality of Individual Compensation",
                clause_text=(
                    "5.1 Colleague Data Privacy: The individual salary details, net pay, allowances, deductions, bank accounts, income tax records, "
                    "and performance ratings of colleagues and supervisors are protected personal information under corporate data privacy rules "
                    "and Section 8(1)(j) of the Right to Information Act, 2005.\n"
                    "5.2 Strict Prohibition against Queries: Employees, automated systems, and corporate tools are prohibited from disclosing, "
                    "querying, or facilitating access to individual compensation or appraisal records of any other employee without written statutory authorization.\n"
                    "5.3 Disciplinary Violation: Attempting to access, query, extract, or publish the salary, appraisal rating, or confidential HR profile "
                    "of a reporting officer or colleague constitutes major misconduct under Rule 4 and Rule 11 of the ONGC CDA Rules, 1994."
                ),
                subclauses=[
                    Subclause("5.1", "Personal Data Protection", "Salary and APARs of colleagues are protected personal data."),
                    Subclause("5.2", "Query Refusal Mandate", "Automated tools must refuse queries for colleague salaries."),
                    Subclause("5.3", "CDA Rule 11 Misconduct", "Unauthorized snooping triggers disciplinary proceedings.")
                ],
                maps_to_question_ids="D1",
                source_basis="P1-01"
            )
        ]
    )

    c5 = Chapter(
        5, "Separation, Resignation & Disciplinary Interlocks",
        [
            Clause(
                clause_ref="Clause 6.0",
                clause_title="Resignation Notice Period (Rule 24(4))",
                clause_text=(
                    "6.1 Mandatory Three-Month Notice: Under Rule 24(4) of the ONGC Service Rules, a regular employee intending to resign from "
                    "the service of the Corporation shall give at least 3 (three) calendar months' notice in writing to the Appointing Authority, "
                    "or pay an amount equal to 3 months' salary in lieu of notice.\n"
                    "6.2 Discretion to Withhold Acceptance: The Corporation reserves the absolute right to withhold acceptance of a resignation where:\n"
                    "   (a) Disciplinary proceedings under ONGC CDA Rules, 1994 are pending or contemplated against the employee;\n"
                    "   (b) The employee is under suspension;\n"
                    "   (c) A vigilance inquiry or criminal investigation regarding official acts is in progress;\n"
                    "   (d) The employee has not fulfilled the mandatory service bond executed for study leave or specialized overseas training.\n"
                    "6.3 Judicial Confirmation: The validity of withholding resignation during pending disciplinary inquiries was affirmed "
                    "by the Hon'ble Delhi High Court in Major Raj Mohan v. ONGC (2011)."
                ),
                subclauses=[
                    Subclause("6.1", "Three Months Notice", "Statutory 3-month notice or salary in lieu."),
                    Subclause("6.2", "Right to Withhold Resignation", "Resignation withheld if disciplinary or vigilance cases pending."),
                    Subclause("6.3", "Judicial Precedent", "Cites Delhi HC judgment Major Raj Mohan v. ONGC.")
                ],
                maps_to_question_ids="D1",
                source_basis="J-05"
            )
        ]
    )

    annex1 = Annexure(
        "Schedule I", "Pay Scales & Standard Allowances Schedule",
        "Comprehensive schedule of executive grades, pay bands, annual increments, and cafeteria perk allowances under 3rd PRC.",
        table_headers=["Grade", "Pay Scale (₹ IDA)", "Min Basic Pay", "Max Basic Pay", "Cafeteria Cap (35%)", "Annual Increment"],
        table_rows=[
            ["E0", "30,000–1,20,000", "₹30,000", "₹1,20,000", "₹10,500", "3%"],
            ["E1", "60,000–1,80,000", "₹60,000", "₹1,80,000", "₹21,000", "3%"],
            ["E2", "70,000–2,00,000", "₹70,000", "₹2,00,000", "₹24,500", "3%"],
            ["E3", "80,000–2,20,000", "₹80,000", "₹2,20,000", "₹28,000", "3%"],
            ["E4", "90,000–2,40,000", "₹90,000", "₹2,40,000", "₹31,500", "3%"],
            ["E5", "1,00,000–2,60,000", "₹1,00,000", "₹2,60,000", "₹35,000", "3%"],
            ["E6", "1,20,000–2,80,000", "₹1,20,000", "₹2,80,000", "₹42,000", "3%"],
            ["E7", "1,20,000–2,80,000", "₹1,20,000", "₹2,80,000", "₹42,000", "3%"],
            ["E8", "1,30,000–2,80,000", "₹1,30,000", "₹2,80,000", "₹45,500", "3%"],
            ["E9", "1,50,000–3,00,000", "₹1,50,000", "₹3,00,000", "₹52,500", "3%"],
            ["DIR", "1,80,000–3,40,000", "₹1,80,000", "₹3,40,000", "₹63,000", "3%"],
            ["CMD", "2,00,000–3,70,000", "₹2,00,000", "₹3,70,000", "₹70,000", "3%"]
        ]
    )

    concordance = [
        {"doc_id": "G-01", "title": "DPE OM 03.08.2017 (3rd PRC Pay Revision)", "clause_ref": "Clause 2.0", "verbatim_quote": "Clause 2 (Pay Scales)"},
        {"doc_id": "J-05", "title": "Delhi HC Judgment (Major Raj Mohan v. ONGC)", "clause_ref": "Clause 6.0", "verbatim_quote": "Rule 24(4) Resignation Notice"},
        {"doc_id": "P1-01", "title": "ONGC Conduct, Discipline and Appeal Rules, 1994", "clause_ref": "Clause 5.0", "verbatim_quote": "Rule 11 (Confidentiality)"}
    ]

    return Rulebook(
        doc_id="HR Manual",
        title="ONGC HR Manual: Designations, Pay Scales & Service Conditions",
        short_title="ONGC HR Manual",
        ref_code="ONGC/CORP-HR/MAN/2017-REV3",
        effective_date="3rd August 2017 (Amended up to 31st March 2026)",
        issuer="Corporate HR Policy Group, Deendayal Urja Bhawan, New Delhi",
        approving_authority="Executive Committee & Board of Directors, ONGC",
        classification="INTERNAL CONTROLLED DOCUMENT / DEMO RECONSTRUCTION",
        preamble=(
            "The ONGC HR Manual compiles the fundamental service conditions, executive designations, grade definitions, pay scales, "
            "allowances, performance management, employee self-service protocols, and resignation procedures for regular employees of the Corporation. "
            "Framed in accordance with DPE guidelines, 3rd Pay Revision Committee recommendations, and corporate governance standards, "
            "this manual serves as the primary operational reference for human resource management and employee welfare across ONGC."
        ),
        definitions=definitions,
        chapters=[c1, c2, c3, c4, c5],
        annexures=[annex1],
        amendment_history=amendments,
        real_excerpts_concordance=concordance
    )


def build_prbs() -> Rulebook:
    """Builds PRBS Rulebook (Post Retirement Benefit Scheme)."""
    amendments = [
        AmendmentRecord("PRBS 1990", "01-Apr-1990", "Board of Directors", "Constitution of ONGC Post Retirement & Death-in-Service Superannuation Benefit Trust under Indian Trusts Act."),
        AmendmentRecord("PRBS Circular 71", "26-Nov-2013", "Board of Trustees", "Conversion of scheme from defined benefit to Defined Contribution Pension Scheme per DPE 2007 guidelines."),
        AmendmentRecord("PRBS Circular 73", "20-Apr-2018", "Principal CIT / Trustees", "Dispensation of 15-year minimum service and superannuation condition w.e.f. 01.01.2017."),
        AmendmentRecord("PRBS 2021 Update", "01-Jul-2021", "Board of Trustees", "Operationalization of one-time corpus transfer option to National Pension System (NPS)."),
        AmendmentRecord("PRBS 2025 Review", "01-Jan-2025", "Board of Trustees", "Actuarial review and re-calibration of contribution rates within 30% DPE superannuation ceiling.")
    ]

    definitions = {
        "PRBS Trust": "The ONGC Self-Contributory Post Retirement & Death in Service Benefit Scheme Trust, an irrevocable trust registered at Dehradun.",
        "Defined Contribution Pension Scheme": "A superannuation pension structure where retirement benefits are determined by accumulated employer and employee contributions plus investment returns, rather than a predetermined formula.",
        "DPE 30% Ceiling": "The statutory ceiling prescribed by Department of Public Enterprises stipulating that aggregate expenditure on superannuation benefits (PF, Gratuity, PRBS, Post-Retirement Medical) shall not exceed 30% of Basic Pay plus DA.",
        "Annuity": "Periodic pension payment purchased from Life Insurance Corporation of India (LIC) or registered pension fund managers using the accumulated PRBS corpus upon superannuation or separation.",
        "Accumulated Corpus": "The total monetary value credited to an individual employee's PRBS account comprising contributions and compounded interest earnings."
    }

    c1 = Chapter(
        1, "Constitution, Trust Governance & Scheme Structure",
        [
            Clause(
                clause_ref="Clause 1.0",
                clause_title="Constitution & Governance of PRBS Trust",
                clause_text=(
                    "1.1 Trust Establishment: The Scheme is administered under the 'ONGC Self-Contributory Post Retirement & Death in Service "
                    "Superannuation Benefit Scheme Trust' (PRBS Trust), established by an irrevocable Deed of Trust dated 1990 and recognized "
                    "by the Principal Commissioner of Income Tax (CIT), Dehradun under Part B of the Fourth Schedule to the Income Tax Act, 1961.\n"
                    "1.2 Board of Trustees: The PRBS Trust is governed by a bi-partite Board of Trustees headquartered at Tel Bhavan, Dehradun. "
                    "The Board is chaired by Director (HR) and comprises: (a) Director (Finance) or nominee; (b) ED-Chief Corporate HR; "
                    "(c) Head Corporate Finance; and (d) elected representatives of the Association of Scientific & Technical Officers (ASTO) and recognized unions.\n"
                    "1.3 Fiduciary Duty: The Trustees hold the accumulated funds in trust for the exclusive benefit of member employees and their beneficiaries."
                ),
                subclauses=[
                    Subclause("1.1", "Legal Trust Setup", "Established 1990; tax-approved by Principal CIT Dehradun."),
                    Subclause("1.2", "Bi-Partite Board", "Chaired by Director HR with management and ASTO representatives."),
                    Subclause("1.3", "Fiduciary Obligation", "Exclusive benefit of participating employees and nominees.")
                ],
                maps_to_question_ids="P13",
                source_basis="P1-10"
            ),
            Clause(
                clause_ref="Clause 2.0",
                clause_title="Defined Contribution Pension Structure",
                clause_text=(
                    "2.1 Conversion to Defined Contribution: Pursuant to DPE Guidelines on Pay Revision and PRBS Circular No. 71 dated 26.11.2013, "
                    "the Scheme was converted from a defined-benefit model to a Defined Contribution Pension Scheme with retrospective effect from 01.01.2007.\n"
                    "2.2 Individual Pension Accounts: Every regular employee is allocated a distinct PRBS Account linked to their SAP PERNR. "
                    "Monthly contributions and accrued investment yields are credited directly to the individual member ledger.\n"
                    "2.3 Investment Governance: PRBS funds are invested strictly in accordance with Ministry of Finance / DPE investment patterns "
                    "(Government Securities, State Development Loans, AAA Corporate Bonds, and approved NPS debt instruments) through LIC of India "
                    "and professional fund managers."
                ),
                subclauses=[
                    Subclause("2.1", "Circular 71 Conversion", "Conversion to defined contribution model w.e.f. 26.11.2013."),
                    Subclause("2.2", "PERNR-Linked Ledger", "Individual digital account tracking in SAP."),
                    Subclause("2.3", "Statutory Investment Pattern", "Strict compliance with MoF/DPE investment guidelines via LIC.")
                ],
                maps_to_question_ids="P13",
                source_basis="P1-10"
            )
        ]
    )

    c2 = Chapter(
        2, "Contribution Rates & DPE 30% Superannuation Ceiling",
        [
            Clause(
                clause_ref="Clause 3.0",
                clause_title="Contribution Rates & 30% Superannuation Cap",
                clause_text=(
                    "3.1 DPE 30% Superannuation Ceiling: In accordance with DPE OM dated 26.11.2008 and 03.08.2017, the aggregate employer contribution "
                    "towards all superannuation benefits shall not exceed 30% (thirty percent) of (Basic Pay + IDA). The 30% ceiling comprises:\n"
                    "   (a) Contributory Provident Fund (CPF / EPF): 12.00% of (Basic Pay + IDA);\n"
                    "   (b) Gratuity Contribution: 4.16% to 4.50% of (Basic Pay + IDA) based on actuarial valuation;\n"
                    "   (c) Post-Retirement Medical Benefit Scheme (PRMB): 4.00% of (Basic Pay + IDA);\n"
                    "   (d) PRBS Pension Scheme (Balancing Headroom): Balancing contribution, typically between 6.00% and 9.50% of (Basic Pay + IDA).\n"
                    "3.2 Employee Matching Contribution: Regular employees contribute a mandatory monthly contribution of 6% to 8% of Basic Pay + IDA, "
                    "with voluntary additional contribution options up to statutory limits.\n"
                    "3.3 Annual Headroom Monitoring: Corporate Finance monitors the aggregate superannuation expense quarterly to ensure that total corporate "
                    "superannuation outgo does not breach the 30% threshold."
                ),
                subclauses=[
                    Subclause("3.1", "30% DPE Component Breakdown", "12% EPF + 4.16% Gratuity + 4% Medical + 6–9.5% PRBS balancing."),
                    Subclause("3.2", "Employee Contribution", "6% to 8% monthly contribution from salary."),
                    Subclause("3.3", "Headroom Monitoring", "Quarterly audit ensures adherence to 30% ceiling.")
                ],
                maps_to_question_ids="P13",
                source_basis="G-01"
            )
        ]
    )

    c3 = Chapter(
        3, "Eligibility, Dispensation of Service Condition & Annuity Payouts",
        [
            Clause(
                clause_ref="Clause 4.0",
                clause_title="Dispensation of 15-Year Service Condition",
                clause_text=(
                    "4.1 Removal of 15-Year Prerequisite: Under PRBS Circular No. 73 dated 20.04.2018, approved by the Principal CIT Dehradun, "
                    "the prerequisite condition of completing a minimum of 15 (fifteen) years of continuous service in ONGC and superannuation "
                    "for eligibility for PRBS pension benefits was completely dispensed with w.e.f. 01.01.2017.\n"
                    "4.2 Benefit on Early Separation: An executive who resigns or separates from the Corporation prior to completing 15 years of service "
                    "is entitled to receive their full accumulated PRBS corpus (both employee contribution and accrued investment returns) either as an annuity "
                    "at age 58, or via transfer to the National Pension System (NPS).\n"
                    "4.3 Dismissal / Forfeiture Exception: Where an employee is dismissed from service for proven fraud or financial embezzlement under CDA Rule 14, "
                    "employer contribution may be subject to recovery / forfeiture per trust rules."
                ),
                subclauses=[
                    Subclause("4.1", "Circular 73 Dispensation", "Removal of 15-year condition w.e.f. 01.01.2017 per Principal CIT approval."),
                    Subclause("4.2", "Early Exit Rights", "Corpus preserved and annuitized upon early separation."),
                    Subclause("4.3", "Fraud Exception", "Forfeiture of employer share on dismissal for gross financial fraud.")
                ],
                maps_to_question_ids="P13",
                source_basis="P1-10"
            ),
            Clause(
                clause_ref="Clause 5.0",
                clause_title="Annuity Options & Payout Formulas",
                clause_text=(
                    "5.1 Annuity Procurement: Upon attaining superannuation (age 60) or upon separation, 100% of the accumulated PRBS corpus "
                    "(or 60% if 40% is commuted per tax rules) shall be utilized to purchase an immediate annuity from Life Insurance Corporation of India (LIC) "
                    "or an IRDAI-regulated pension provider.\n"
                    "5.2 Standard Annuity Variants: Retiring executives may select from the following standard annuity options:\n"
                    "   (a) Option A: Life Annuity payable for life of the retiree;\n"
                    "   (b) Option B: Life Annuity with Return of Purchase Price (Capital) to nominee upon death;\n"
                    "   (c) Option C: Joint Life Annuity with 100% pension payable to surviving spouse upon death of member, with/without return of capital;\n"
                    "   (d) Option D: Increasing Life Annuity at 3% compound growth per annum.\n"
                    "5.3 Default Option: Where no specific option is exercised in writing, Option C (Joint Life with Return of Capital) shall be the default."
                ),
                subclauses=[
                    Subclause("5.1", "LIC Annuity Purchase", "100% of corpus utilized for registered annuity purchase."),
                    Subclause("5.2", "Four Standard Options", "Life, Return of Capital, Joint Life Spouse, and Increasing Annuity."),
                    Subclause("5.3", "Default Spouse Cover", "Joint life with return of capital is the automatic default.")
                ],
                maps_to_question_ids="P13",
                source_basis="P1-11"
            ),
            Clause(
                clause_ref="Clause 6.0",
                clause_title="Corpus Transfer Option to NPS",
                clause_text=(
                    "6.1 Portability to National Pension System: In accordance with PFRDA guidelines and ONGC Board resolution, serving executives "
                    "are provided an option to transfer their accumulated PRBS balance to their Tier-I account under the National Pension System (NPS).\n"
                    "6.2 One-Way Portability: The transfer from PRBS to NPS is irrevocable and exempt from income tax under Section 10(13A) of the Income Tax Act.\n"
                    "6.3 Future Contributions: Upon exercising the NPS option, future monthly superannuation contributions by the Corporation "
                    "shall be remitted directly into the employee's PRBS or NPS account as opted."
                ),
                subclauses=[
                    Subclause("6.1", "NPS Transfer Window", "Permits migration of PRBS corpus into PFRDA Tier-I account."),
                    Subclause("6.2", "Tax-Exempt Portability", "One-way irrevocable transfer exempt under IT Act."),
                    Subclause("6.3", "Future Remittance", "Remittance routed to chosen pension vehicle.")
                ],
                maps_to_question_ids="P13",
                source_basis="P1-10"
            )
        ]
    )

    annex1 = Annexure(
        "Schedule I", "Superannuation Benefit Cap & Annuity Matrix",
        "Overview of DPE 30% superannuation components and representative annuity yields per ₹10 Lakh corpus.",
        table_headers=["Component Head", "Statutory Provision", "DPE Ceiling Share", "Administration Body", "Remarks"],
        table_rows=[
            ["Contributory Provident Fund (EPF)", "EPF Act 1952", "12.00% of BP+DA", "ONGC EPF Trust / EPFO", "Mandatory statutory contribution"],
            ["Gratuity", "Payment of Gratuity Act 1972", "4.16%–4.50% of BP+DA", "ONGC Gratuity Trust", "Max ceiling ₹20 Lakh / 3rd PRC"],
            ["Post-Retirement Medical (PRMB)", "ONGC Medical Rules", "4.00% of BP+DA", "Corporate Medical Section", "Requires 15y service (OO 30/2015)"],
            ["PRBS Pension Scheme", "PRBS Trust Deed 1990", "9.50% of BP+DA (Balancing)", "PRBS Trust, Dehradun", "Annuity via LIC; 15y rule dispensed"],
            ["Total Superannuation Outgo", "DPE Guidelines 2017", "30.00% Max Ceiling", "Corporate Finance Monitoring", "Strictly non-breachable cap"]
        ]
    )

    concordance = [
        {"doc_id": "P1-10", "title": "PRBS Circular No. 73 (2018)", "clause_ref": "Clause 1.0, 4.0, 6.0", "verbatim_quote": "approved by the Principal CIT, Dehradun"},
        {"doc_id": "P1-11", "title": "Hamesha Aapke Saath Retiree Compendium", "clause_ref": "Clause 2.0, 5.0", "verbatim_quote": "PRBS Defined Contribution Scheme"},
        {"doc_id": "J-12", "title": "Gauhati HC Judgment (Arpan Chakraborty v. ONGC)", "clause_ref": "Clause 2.0, 3.0", "verbatim_quote": "PRBS Trust"}
    ]

    return Rulebook(
        doc_id="PRBS",
        title="ONGC Self-Contributory Post Retirement & Death in Service Benefit Scheme (PRBS)",
        short_title="ONGC PRBS Scheme Rules",
        ref_code="ONGC/CORP-HR/PRBS/2018-REV3",
        effective_date="20th April 2018 (Amended up to 31st March 2026)",
        issuer="Board of Trustees, PRBS Trust, Tel Bhavan, Dehradun",
        approving_authority="Board of Trustees & Principal CIT, Dehradun",
        classification="INTERNAL CONTROLLED DOCUMENT / DEMO RECONSTRUCTION",
        preamble=(
            "The ONGC Self-Contributory Post Retirement and Death in Service Benefit Scheme (PRBS) provides superannuation security "
            "and pension annuities to executives and employees of the Corporation upon retirement or to surviving families upon death in service. "
            "Operating as an irrevocable tax-approved Trust registered at Dehradun and managed within the DPE 30% superannuation ceiling, "
            "this document sets forth the governing rules, contribution structures, dispensation of tenure requirements, and annuity options."
        ),
        definitions=definitions,
        chapters=[c1, c2, c3],
        annexures=[annex1],
        amendment_history=amendments,
        real_excerpts_concordance=concordance
    )


def build_medical() -> Rulebook:
    """Builds Post-Retirement Medical Scheme & Retiree Welfare Rules."""
    amendments = [
        AmendmentRecord("PRMB 1991", "01-Jan-1991", "Board of Directors", "Original medical scheme for retired ONGC employees."),
        AmendmentRecord("PRMB 2001 (Agrani)", "15-Aug-2001", "Executive Committee", "Introduction of Agrani Samman Scheme for pre-1995 retired employees / destitute widows."),
        AmendmentRecord("PRMB 2013 (Asha Kiran)", "01-Apr-2013", "Board of Directors", "Launch of Asha Kiran Emergency Medical Assistance Scheme for critical illnesses."),
        AmendmentRecord("PRMB OO 30/2015", "01-Jul-2015", "Executive Committee", "Mandatory requirement of 15 years continuous service in ONGC for eligibility (OO 30/2015)."),
        AmendmentRecord("PRMB 2022 Dependent", "01-May-2022", "Director (HR)", "Revision of dependent parent medical reimbursement ceiling and income dependency norms."),
        AmendmentRecord("PRMB 2026 Cashless", "01-Jan-2026", "Corporate Medical", "Universal expansion of digital cashless hospitalization across 450+ empaneled hospitals.")
    ]

    definitions = {
        "Post-Retirement Medical Benefit Scheme (PRMBS)": "The scheme providing comprehensive inpatient and outpatient medical coverage to retired employees and eligible dependents.",
        "Fifteen-Year Service Rule": "The mandatory requirement under Office Order 30/2015 stipulating 15 years continuous service in ONGC for eligibility for post-retirement medical facilities.",
        "Empaneled Hospital": "A hospital or medical institution with which ONGC has executed a formal memorandum of understanding for providing cashless inpatient and specialized healthcare.",
        "Asha Kiran Scheme": "An emergency medical assistance corpus providing non-repayable financial assistance to destitute or severely ill retired ONGCians and surviving spouses.",
        "Agrani Samman": "A monthly ex-gratia financial relief scheme established in 2001 for pre-1995 retirees and destitute surviving spouses.",
        "Dependent Parents": "Mother and father residing with the officer whose combined monthly income from all sources does not exceed statutory limits (₹9,000 + DA per month)."
    }

    c1 = Chapter(
        1, "Eligibility Criteria & Beneficiary Coverage",
        [
            Clause(
                clause_ref="Clause 1.0",
                clause_title="Eligibility Criteria (Office Order 30/2015)",
                clause_text=(
                    "1.1 Mandatory 15-Year Service Prerequisite: In accordance with Corporate Office Order No. 30/2015 dated 01.07.2015, "
                    "a regular employee of the Corporation must have rendered a minimum of 15 (fifteen) completed years of continuous regular service "
                    "in ONGC to become eligible for post-retirement medical facilities upon superannuation or separation.\n"
                    "1.2 Exceptions to 15-Year Rule: The condition of 15 years service shall be waived only in the following exceptional cases:\n"
                    "   (a) Death in service of an employee while on active rolls of the Corporation (surviving spouse and dependents covered immediately);\n"
                    "   (b) Medical boarding out / permanent total disablement certified by an ONGC Standing Medical Board arising out of operational injuries.\n"
                    "1.3 Resignation / Voluntary Exit: Employees who resign or separate from the Corporation with less than 15 years of service "
                    "shall NOT be eligible for post-retirement medical benefits."
                ),
                subclauses=[
                    Subclause("1.1", "Fifteen-Year Service Condition", "Minimum 15 years continuous ONGC service per OO 30/2015."),
                    Subclause("1.2", "Death & Disability Exemption", "Condition waived for death in service or medical boarding out."),
                    Subclause("1.3", "Early Resignation Bar", "No medical benefits for resignation under 15 years.")
                ],
                maps_to_question_ids="P1-19",
                source_basis="P1-19"
            ),
            Clause(
                clause_ref="Clause 2.0",
                clause_title="Coverage of Beneficiaries",
                clause_text=(
                    "2.1 Eligible Beneficiaries: The following persons shall be covered under the Post-Retirement Medical Benefit Scheme:\n"
                    "   (a) The retired employee;\n"
                    "   (b) The legally wedded spouse of the retired employee;\n"
                    "   (c) The surviving spouse of a deceased retired employee or employee who died in service;\n"
                    "   (d) Eligible dependent children (unmarried sons up to age 25 or until gainful employment; unmarried daughters until marriage or employment);\n"
                    "   (e) Permanent physically or mentally challenged dependent children (without any age limit, certified by Govt Medical Board);\n"
                    "   (f) Dependent parents residing with the officer, subject to income dependency criteria.\n"
                    "2.2 Medical Identity Card: Beneficiaries are issued digital biometric / QR-coded ONGC Retiree Medical Cards for cashless hospital access."
                ),
                subclauses=[
                    Subclause("2.1", "Beneficiary Roster", "Retiree, spouse, surviving widow, dependent children, and parents."),
                    Subclause("2.2", "Digital Medical Cards", "QR-coded smart cards for cashless admissions.")
                ],
                maps_to_question_ids="P1-14",
                source_basis="P1-11"
            )
        ]
    )

    c2 = Chapter(
        2, "Outpatient (OPD) & Inpatient Hospitalization Care",
        [
            Clause(
                clause_ref="Clause 3.0",
                clause_title="Outpatient (OPD) Treatment Ceilings",
                clause_text=(
                    "3.1 Annual OPD Reimbursement Limits: Retired executives are entitled to reimbursement of outpatient consultation fees, "
                    "diagnostic tests, and routine medicines up to prescribed annual ceilings based on their grade band at retirement:\n"
                    "   • Grades E0 to E3 (Assistant Officer to Manager): ₹45,000 per financial year;\n"
                    "   • Grades E4 to E6 (Chief Manager to Joint General Manager): ₹65,000 per financial year;\n"
                    "   • Grades E7 to E9 (General Manager to Executive Director): ₹90,000 per financial year;\n"
                    "   • Functional Directors & CMD: Full reimbursement on actuals.\n"
                    "3.2 Chronic Diseases Treatment: Expenses incurred on recognized life-threatening chronic ailments (cancer chemotherapy, "
                    "cardiac maintenance, dialysis, organ transplant immunosuppressants) shall be reimbursed in full without debiting the annual OPD ceiling."
                ),
                subclauses=[
                    Subclause("3.1", "Grade-Wise OPD Limits", "₹45k for E0–E3; ₹65k for E4–E6; ₹90k for E7–E9."),
                    Subclause("3.2", "Chronic Disease Exemption", "Dialysis, cancer, and cardiac care exempt from annual ceiling.")
                ],
                maps_to_question_ids="P1-11",
                source_basis="P1-11"
            ),
            Clause(
                clause_ref="Clause 4.0",
                clause_title="Inpatient Hospitalization & Cashless Network",
                clause_text=(
                    "4.1 Universal Cashless Indoor Treatment: Inpatient hospitalization is fully covered on a cashless basis across more than 450 "
                    "ONGC empaneled corporate, super-specialty, and charitable hospitals nationwide (including Apollo, Fortis, Max, Medanta, "
                    "Tata Memorial Centre, AIIMS, and Manipal Hospitals).\n"
                    "4.2 Room Entitlements by Retiring Grade:\n"
                    "   • Grades E0 to E3: Semi-private / Shared AC Room;\n"
                    "   • Grades E4 to E6: Single AC Private Room;\n"
                    "   • Grades E7 to E9: Deluxe Single AC Private Room;\n"
                    "   • Functional Directors & CMD: Suite / Executive Deluxe Room.\n"
                    "4.3 Emergency Treatment at Non-Empaneled Hospitals: In case of acute medical emergencies, treatment may be taken at any recognized "
                    "hospital, and reimbursement shall be sanctioned by Chief Corporate Medical at CGHS / AIIMS rates."
                ),
                subclauses=[
                    Subclause("4.1", "450+ Empaneled Hospital Network", "Universal cashless hospitalization across major healthcare chains."),
                    Subclause("4.2", "Room Entitlement Scale", "Single AC private room for E4–E6; Deluxe for E7–E9."),
                    Subclause("4.3", "Emergency Non-Empaneled Care", "Reimbursement allowed at CGHS rates in emergencies.")
                ],
                maps_to_question_ids="P1-11",
                source_basis="P1-11"
            )
        ]
    )

    c3 = Chapter(
        3, "Dependent Parents & Retiree Welfare Schemes",
        [
            Clause(
                clause_ref="Clause 5.0",
                clause_title="Dependent Parents Medical Reimbursement",
                clause_text=(
                    "5.1 Eligibility of Dependent Parents: Medical reimbursement for dependent father and mother is admissible subject to "
                    "fulfillment of the income dependency criterion.\n"
                    "5.2 Income Dependency Threshold: Parents shall be deemed dependent only if their combined monthly recurring income from all sources "
                    "(pension, rental income, investments, agriculture) does not exceed ₹9,000/- plus applicable Dearness Relief per month.\n"
                    "5.3 Residence Condition: Dependent parents must normally reside with the employee or retiree, and an annual self-declaration of dependency "
                    "must be submitted on the ESS / Retiree portal."
                ),
                subclauses=[
                    Subclause("5.1", "Parental Coverage", "Admissible subject to verified financial dependency."),
                    Subclause("5.2", "Income Limit ₹9,000 + DA", "Total parental income must not exceed statutory ceiling."),
                    Subclause("5.3", "Annual Dependency Filing", "Mandatory annual declaration on portal.")
                ],
                maps_to_question_ids="P1-14",
                source_basis="P1-12"
            ),
            Clause(
                clause_ref="Clause 6.0",
                clause_title="Welfare Schemes: Asha Kiran & Agrani Samman",
                clause_text=(
                    "6.1 Asha Kiran Scheme (Emergency Medical Assistance, 2013):\n"
                    "   (a) Provides one-time or ongoing non-repayable financial and medical relief to retired employees, surviving widows, "
                    "and dependent children facing extreme financial hardship or terminal illness (e.g. paralysis, advanced malignancy, Alzheimer's).\n"
                    "   (b) Financial assistance up to ₹5,00,000 per case sanctioned by the Corporate Welfare Committee chaired by ED-Chief ER.\n"
                    "6.2 Agrani Samman Scheme (Ex-Gratia Relief, 2001):\n"
                    "   (a) Provides monthly ex-gratia financial relief to surviving pre-1995 retired ONGCians and surviving spouses who retired "
                    "prior to the introduction of formal pension schemes and whose pensionary income is insufficient for basic sustenance.\n"
                    "   (b) Current monthly relief of ₹10,000 to ₹15,000 per month credited directly to the beneficiary's bank account."
                ),
                subclauses=[
                    Subclause("6.1", "Asha Kiran Medical Grants", "Emergency assistance up to ₹5 Lakh for terminal illness."),
                    Subclause("6.2", "Agrani Samman Ex-Gratia", "Monthly ex-gratia relief for pre-1995 retirees and destitute widows.")
                ],
                maps_to_question_ids="P1-11",
                source_basis="P1-12"
            )
        ]
    )

    annex1 = Annexure(
        "Schedule I", "Retiree Medical Entitlements & OPD Ceilings",
        "Summary schedule of annual outpatient reimbursement ceilings and room entitlements by retiring grade band.",
        table_headers=["Retiring Grade Band", "Designation", "Annual OPD Ceiling (₹)", "Hospital Room Category", "Chronic Illness Coverage"],
        table_rows=[
            ["E0 to E3", "Asst. Officer to Manager", "₹45,000 / Year", "Semi-Private / Shared AC Room", "Full Cashless Coverage"],
            ["E4 to E6", "Chief Manager to Joint GM", "₹65,000 / Year", "Single AC Private Room", "Full Cashless Coverage"],
            ["E7 to E9", "General Manager to Executive Director", "₹90,000 / Year", "Deluxe Single AC Private Room", "Full Cashless Coverage"],
            ["Directors / CMD", "Functional Director / CMD", "Actuals / Full Reimbursement", "Executive Suite / Deluxe Room", "Full Cashless Coverage"],
            ["Asha Kiran Beneficiary", "Destitute / Terminally Ill Retirees", "Special Grant up to ₹5,00,000", "Empaneled Hospital Private", "Welfare Committee Grant"],
            ["Agrani Samman", "Pre-1995 Retirees / Widows", "Monthly Ex-Gratia ₹10k–15k", "General Empaneled Hospital", "Monthly Bank Transfer"]
        ]
    )

    concordance = [
        {"doc_id": "P1-19", "title": "Office Order 30/2015 (15-Year Medical Eligibility)", "clause_ref": "Clause 1.0", "verbatim_quote": "Post Retirement Medical Scheme"},
        {"doc_id": "P1-11", "title": "Hamesha Aapke Saath Retiree Compendium", "clause_ref": "Clause 2.0, 3.0, 4.0, 6.0", "verbatim_quote": "Asha Kiran"},
        {"doc_id": "P1-12", "title": "Department Circulars under Welfare Schemes", "clause_ref": "Clause 5.0, 6.0", "verbatim_quote": "Agrani Samman"}
    ]

    return Rulebook(
        doc_id="Post-retirement medical",
        title="ONGC Post-Retirement Medical Benefit Scheme & Retiree Welfare Rules",
        short_title="ONGC Retiree Medical Rules",
        ref_code="ONGC/CORP-HR/MED/2015-REV4",
        effective_date="1st July 2015 (Amended up to 31st March 2026)",
        issuer="Corporate Medical Services & Employee Welfare Section, Tel Bhavan, Dehradun",
        approving_authority="Executive Committee & Board of Directors, ONGC",
        classification="INTERNAL CONTROLLED DOCUMENT / DEMO RECONSTRUCTION",
        preamble=(
            "The ONGC Post-Retirement Medical Benefit Scheme (PRMBS) and Retiree Welfare Rules ensure lifetime comprehensive healthcare, "
            "cashless hospitalization, and emergency welfare assistance for retired employees, surviving spouses, and eligible dependents. "
            "Anchored by the statutory 15-year service prerequisite established under Office Order 30/2015, supported by the Asha Kiran "
            "emergency assistance scheme and Agrani Samman ex-gratia relief, this rulebook codifies entitlements, ceilings, empaneled hospital "
            "access, and dependent eligibility."
        ),
        definitions=definitions,
        chapters=[c1, c2, c3],
        annexures=[annex1],
        amendment_history=amendments,
        real_excerpts_concordance=concordance
    )
