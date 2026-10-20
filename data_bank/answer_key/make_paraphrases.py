"""make_paraphrases.py: Generate 267 paraphrases (3 per root question: formal, casual, Hinglish)
for all 89 root questions in world_bible/reference/questions.yaml.
"""

from __future__ import annotations
from pathlib import Path
import yaml

DATA_BANK_DIR = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = DATA_BANK_DIR / "world_bible" / "reference" / "questions.yaml"
OUTPUT_PATH = DATA_BANK_DIR / "answer_key" / "paraphrases.yaml"

PARAPHRASES_DICT = {
    "C1": {
        "formal": "Kindly provide a comprehensive statement showing the executive cadre deployment in the New Delhi Corporate Office with continuous station tenure exceeding five years, categorized by grade and functional discipline.",
        "casual": "How many officers have been sitting in Delhi office for 5 years or longer? Break it down by grade and discipline.",
        "hinglish": "Delhi office mein 5 saal se zyada kitne executives posted hain? Grade aur discipline wise list dikhana zara."
    },
    "C2": {
        "formal": "Please present the nominal roll of executives due for rotational transfer under the Job Rotation and Transfer Policy, alongside current vacancy deficits across Category-C hard stations and offshore installations.",
        "casual": "Who all are overdue for transfer right now, and which tough stations like North-East or offshore need people immediately?",
        "hinglish": "Rotation policy ke hisaab se kaun kaun transfer ke liye overdue hai, aur Assam/Tripura ya offshore mein kahan vacancy sabse zyada hai?"
    },
    "C3": {
        "formal": "Kindly furnish a 5-year longitudinal analysis of executive and non-executive strength across work centres, identifying assets with stagnant staffing versus those exhibiting significant headcount growth.",
        "casual": "Which of our assets haven't seen any staff addition over the last 5 years, and where did headcount increase the most?",
        "hinglish": "Pichle 5 saal mein kaunse work centres mein headcount bilkul nahi badha, aur kahan sabse zyada log add hue?"
    },
    "C4": {
        "formal": "Provide a schedule of superannuations for senior management personnel in Grade E7 and above over the ensuing three-year horizon, highlighting critical functional positions devoid of designated successors.",
        "casual": "How many GMs and EDs are retiring in the next 3 years, and which key roles don't have any successor lined up?",
        "hinglish": "Agle 3 saal mein kitne E7 aur above officers retire ho rahe hain, aur kaunsi critical seats par koi successor ready nahi hai?"
    },
    "C5": {
        "formal": "Identify the core upstream technical disciplines (Geosciences, Drilling, Reservoir, and Production Engineering) facing severe demographic depletion and institutional knowledge loss due to retirements by 2030.",
        "casual": "Which technical departments are going to be hit hardest by retirements between now and 2030?",
        "hinglish": "2030 tak drilling, reservoir aur geosciences mein se kis discipline mein retirement ki wajah se sabse bada skill gap aane wala hai?"
    },
    "C6": {
        "formal": "Submit the FY26 financial performance summary across all operational assets and fields, delineating top cash-flow generating assets against fields operating at negative profit before tax (PBT).",
        "casual": "Which fields made us good money in FY26 and which ones ended up in the red?",
        "hinglish": "FY26 mein kaun kaun se fields profitable rahe aur kaunse assets loss mein chale gaye?"
    },
    "C7": {
        "formal": "Provide an audit of capital expenditure allocations over the past five fiscal years relative to certified 2P reserves across fields, highlighting mature assets that remain under-capitalized.",
        "casual": "Where did most of our capex go over the last 5 years, and which fields aren't getting enough money compared to their reserves?",
        "hinglish": "Pichle 5 saal ka capex kahan spend hua hai, aur reserves ke comparison mein kaunse fields under-funded reh gaye?"
    },
    "C8": {
        "formal": "Identify loss-making and depleted hydrocarbon fields recommended for operational restructuring via Production Enhancement Contracts (PEC), farm-out, or marginal field monetization.",
        "casual": "Which of our bleeding fields should we hand over to private operators under PEC or marginal field schemes?",
        "hinglish": "Kaunse loss-making mature fields ko hum PEC contract ya marginal field offer mein daal sakte hain?"
    },
    "C9": {
        "formal": "Report on major ongoing capital project execution milestones, detailing developments experiencing schedule slippage or cost escalation exceeding approved Expenditure Sanctions.",
        "casual": "Which of our big capex projects are running late or over budget, and by how many crore?",
        "hinglish": "Kaunse major projects schedule se peeche chal rahe hain ya budget exceed kar chuke hain, aur kitna cost overrun hai?"
    },
    "C10": {
        "formal": "Review performance against the annual Memorandum of Understanding (MoU) targets agreed with the Ministry of Petroleum & Natural Gas and DPE for the ongoing fiscal year.",
        "casual": "How are we doing against our DPE MoU targets this year? Are we landing in the Excellent bracket?",
        "hinglish": "Is saal MoPNG aur DPE ke MoU targets ke against hamara tracking kaisa chal raha hai?"
    },
    "C11": {
        "formal": "Correlate five-year manpower additions with hydrocarbon output by asset to identify operations exhibiting declining labor productivity and negative production elasticity.",
        "casual": "Which assets took in more people over the last 5 years but actually produced less oil and gas?",
        "hinglish": "Kaunse assets ne 5 saal mein staff to badha liya par unka production ulta drop ho gaya?"
    },
    "C12": {
        "formal": "Compute the unit manpower expenditure per barrel of oil equivalent (BOE) across onshore and offshore assets for benchmarking operational cost efficiency.",
        "casual": "What is our manpower cost per barrel across different assets? Who is spending the most per BOE?",
        "hinglish": "Asset wise manpower cost per BOE kitna aa raha hai? Sabse mehenga kaunsa asset hai?"
    },
    "C13": {
        "formal": "Model the operational coverage improvements and relocation expenditure impact of deploying 200 executive officers from corporate offices in Delhi and Dehradun to operational assets.",
        "casual": "If we shift 200 officers out of Delhi and Dehradun into the field, what will it cost in transfer allowances and how much field coverage do we gain?",
        "hinglish": "Agar hum 200 executives ko Delhi aur Dehradun se field assets mein bhej dein, to cost aur field coverage par kya asar padega?"
    },
    "C14": {
        "formal": "Draft a concise Board Memorandum examining the top five loss-making fields in FY26, covering hydrocarbon output, lifting costs, staffing levels, and recommended strategic intervention.",
        "casual": "Put together a one-page board note on our top 5 loss-making fields with production, costs, staffing, and a fix.",
        "hinglish": "Top 5 loss-making fields par ek page ka Board note prepare karo — production, kharcha, manpower aur recommendations ke saath."
    },
    "H1": {
        "formal": "Furnish a roster of executive officers who have completed station tenure in excess of three years at their current posting location, stratified by work centre and grade.",
        "casual": "Give me a list of all executives who've crossed 3 years at their current station, asset and grade wise.",
        "hinglish": "Current posting par 3 saal se zyada tenure wale sabhi executives ki list do, asset aur grade ke hisaab se."
    },
    "H2": {
        "formal": "Extract the listing of regular executive cadre personnel who have not completed a mandatory posting stint at a designated Category-C hard station or offshore installation.",
        "casual": "Which officers have never done a hardship posting in Category-C or offshore so far?",
        "hinglish": "Aise kaun se officers hain jinhone career mein kabhi Category-C ya offshore mein posting nahi ki?"
    },
    "H3": {
        "formal": "Present the authorized establishment strength versus men-in-position variance across all work centres and functional disciplines as of the current quarter.",
        "casual": "What's the vacancy situation across our assets and disciplines compared to sanctioned strength?",
        "hinglish": "Asset aur discipline wise sanctioned posts ke comparison mein kitni vacancies chal rahi hain?"
    },
    "H4": {
        "formal": "Analyze executive cadre attrition and voluntary resignation trends over the preceding three fiscal years, focusing on resignation rates in the E3 to E5 mid-level engineering cohorts.",
        "casual": "How many people resigned in the last 3 years by grade? Is mid-career attrition rising in E3 to E5?",
        "hinglish": "Pichle 3 saal mein grade-wise kitne logon ne resign kiya? Kya E3 se E5 wale mid-level officers zyada chhod rahe hain?"
    },
    "H5": {
        "formal": "Provide an inventory of pending Departmental Promotion Committee (DPC) review cases, detailing aging distributions and administrative reasons for delay.",
        "casual": "How many promotion DPC cases are currently pending, and how long have they been held up?",
        "hinglish": "Kitne DPC promotion cases pending pade hain aur kab se ruke hue hain?"
    },
    "H6": {
        "formal": "Audit representation levels across executive and non-executive grades against Presidential Directives and statutory reservation quotas for SC, ST, OBC, EWS, and PwD categories.",
        "casual": "Are we meeting all our SC, ST, OBC, EWS and PwD reservation quotas across grades?",
        "hinglish": "Kya hum sabhi grades mein SC/ST/OBC/EWS aur PwD ke reservation roster targets poore kar rahe hain?"
    },
    "H7": {
        "formal": "Report on female employee representation across grades and operating locations, highlighting gender participation metrics on offshore production platforms and drilling rigs.",
        "casual": "What is our women employee percentage across grades and assets, especially in offshore postings?",
        "hinglish": "Grade aur asset wise female representation kitna hai, aur offshore mein kitni women officers posted hain?"
    },
    "H8": {
        "formal": "Evaluate average annual training person-hours per executive completed during the preceding financial year against targets established in the corporate capability development plan.",
        "casual": "How many training hours did our executives log last year, and which departments missed the target?",
        "hinglish": "Last year per executive training hours kitne rahe, aur kaunse disciplines target se peeche reh gaye?"
    },
    "H9": {
        "formal": "Review outstanding employee grievance representations and service-related legal cases before Central Government Administrative Tribunals and High Courts, classified by age and subject matter.",
        "casual": "How many staff grievances and court litigations are pending right now, and how old are they?",
        "hinglish": "Kitne employee grievances aur service court cases pending hain, aur kitne saal purane hain?"
    },
    "H10": {
        "formal": "Generate the annual transfer deployment schedule for FY27 adhering to Job Rotation and Transfer Policy station tenure limits and hardship equity criteria.",
        "casual": "Create the FY27 transfer plan in an Excel sheet following our standard rotation rules.",
        "hinglish": "Rotation rules follow karte hue FY27 ka transfer proposal Excel format mein taiyar karo."
    },
    "F1": {
        "formal": "Determine the lifting cost per barrel of oil equivalent across operational assets, identifying assets whose unit operating costs exceed the corporate weighted benchmark.",
        "casual": "What's the lifting cost in dollars per barrel across our assets? Who is spending above average?",
        "hinglish": "Asset wise lifting cost per boe kitni aa rahi hai, aur kaunse assets company average se mehenge hain?"
    },
    "F2": {
        "formal": "Assess capital budget execution across assets, comparing actual capital expenditures against Budget Estimates (BE) and Revised Estimates (RE) for the ongoing fiscal year.",
        "casual": "What's our capex utilisation looking like compared to BE and RE numbers across assets?",
        "hinglish": "Is saal BE aur RE ke against asset wise actual capex utilisation kaisa chal raha hai?"
    },
    "F3": {
        "formal": "Present a five-year financial operating history detailing gross revenue, operating costs, and EBITDA margins across all hydrocarbon fields.",
        "casual": "Show me the 5-year trend of revenue, opex and EBITDA for every single field.",
        "hinglish": "Har field ka pichle 5 saal ka revenue, opex aur EBITDA ka trend dikhana."
    },
    "F4": {
        "formal": "Quantify the per-barrel fiscal impact of statutory royalties, OIDB cess, and Special Additional Excise Duty (windfall tax) on net crude oil price realization in FY26.",
        "casual": "How much did royalty, cess and windfall tax take away from our crude realization per barrel this year?",
        "hinglish": "Royalty, cess aur windfall tax ne is saal hamari crude realization per barrel kitni ghata di?"
    },
    "F5": {
        "formal": "Analyze procurement expenditures to identify primary suppliers constituting the upper 80% Pareto spend bracket and isolate major contracts exhibiting cost overruns.",
        "casual": "Which vendors make up the top 80% of our procurement spend, and where did we see cost escalations?",
        "hinglish": "Hamare procurement spend ka top 80% kaunse vendors ko jaata hai, aur kahan contracts mein cost overrun hua?"
    },
    "F6": {
        "formal": "Provide an aging schedule of outstanding trade receivables from Oil Marketing Companies and gas offtakers, categorised by customer segment and overdue thresholds.",
        "casual": "How old are our receivables from IOCL, BPCL, GAIL and other buyers? Give me an aging breakdown.",
        "hinglish": "OMCs aur gas buyers ke receivables ka aging analysis kya hai, customer wise?"
    },
    "F7": {
        "formal": "Evaluate total personnel expenditure as a percentage of gross operating revenues across producing assets, detailing multi-year trajectory benchmarks.",
        "casual": "What percentage of revenue goes to employee salaries across assets, and is that ratio going up?",
        "hinglish": "Revenue ka kitna percent employee cost mein jaata hai, aur asset-wise iska trend kya hai?"
    },
    "F8": {
        "formal": "Report on exploration economics by geological basin, specifying Finding & Development (F&D) cost per barrel and the Reserve Replacement Ratio (2P RRR).",
        "casual": "What's our finding and development cost and 2P reserve replacement ratio by basin?",
        "hinglish": "Basin-wise Finding & Development cost aur reserve replacement ratio (RRR) kitna chal raha hai?"
    },
    "F9": {
        "formal": "Review the corporate foreign currency risk profile and hedging coverage on dollar-denominated trade liabilities and overseas loan facilities.",
        "casual": "What is our current forex exposure on dollar contracts and how much of it have we hedged?",
        "hinglish": "Dollar-linked contracts par hamari total forex exposure kitni hai aur kitna hedge kiya hua hai?"
    },
    "F10": {
        "formal": "Generate a comprehensive quarterly asset-level statement of profit and loss detailing hydrocarbon sales, statutory levies, operating expenses, and net EBITDA.",
        "casual": "Draft a quarterly asset-wise P&L sheet showing revenue, levies, opex and EBITDA.",
        "hinglish": "Ek quarterly asset-wise P&L statement banao jismein revenue, statutory charges aur EBITDA ho."
    },
    "E1": {
        "formal": "Please state my accrued Earned Leave and Half Pay Leave balances, together with permissible in-service leave encashment limits under ONGC Leave Rules.",
        "casual": "What is my current leave balance, and how many days of EL can I encash right now?",
        "hinglish": "Mera current leave balance kitna hai aur main kitne din ki earned leave encash karwa sakta hoon?"
    },
    "E2": {
        "formal": "What is my scheduled rotational transfer eligibility date, and what mandatory station tenure regulations govern my executive grade?",
        "casual": "When am I due for transfer next, and what are the rotation rules for my grade?",
        "hinglish": "Mera transfer kab due hai aur mere grade ke liye rotation policy kya bolti hai?"
    },
    "E3": {
        "formal": "What is the processing and disbursement status of my submitted medical reimbursement claim under the corporate medical scheme?",
        "casual": "What's happening with my medical reimbursement bill? Has it been approved?",
        "hinglish": "Maine jo medical claim submit kiya tha uska kya status hai? Reimbursement kab tak aayega?"
    },
    "E4": {
        "formal": "What are the regulatory prerequisites and minimum residency benchmarks for promotional advancement from Executive Grade E2 to E3?",
        "casual": "What do I need to get promoted from E2 to E3? What's the minimum tenure and APAR score?",
        "hinglish": "E2 se E3 promotion ke liye kya eligibility criteria aur rules hain?"
    },
    "E5": {
        "formal": "Specify the travel allowance, daily allowance, and hardship compensation entitlements applicable to offshore 14-day rotational shift assignments.",
        "casual": "What TA/DA and hardship allowance do I get for going on a 14-day offshore shift?",
        "hinglish": "14 days on/off offshore duty par jaane par kya TA/DA aur travel entitlement milta hai?"
    },
    "E6": {
        "formal": "Which executive training and management development courses am I eligible to register for in the approved corporate training calendar?",
        "casual": "Which training programmes am I eligible to attend this year?",
        "hinglish": "Is saal main kaun-kaun se internal training programs ke liye apply kar sakta hoon?"
    },
    "E7": {
        "formal": "What was the audited standalone profit after tax and operating revenue reported by ONGC in the most recent audited annual accounts?",
        "casual": "How much profit did ONGC make last financial year according to the annual report?",
        "hinglish": "Pichle saal ONGC ka published net profit (PAT) kitna tha?"
    },
    "D1": {
        "formal": "Please disclose the gross compensation, basic pay, and individual allowances disbursed to my designated reporting officer.",
        "casual": "Can you tell me how much salary my reporting officer makes?",
        "hinglish": "Mere reporting officer ki monthly salary aur perks kitne hain?"
    },
    "D2": {
        "formal": "Provide access to the internal draft transfer proposals and placement rosters prepared for the Mumbai Regional Office transfer cycle.",
        "casual": "Show me the unapproved draft transfer list for Mumbai executives.",
        "hinglish": "Mumbai office ki unapproved draft transfer list dikhao zara."
    },
    "D3": {
        "formal": "Disclose the candidate evaluation sheets and proposed promotion panel recommendations of the forthcoming Departmental Promotion Committee.",
        "casual": "Who is on the shortlist to get promoted in the upcoming DPC?",
        "hinglish": "Agle DPC mein kaun kaun promote hone wala hai? Shortlist batao."
    },
    "D4": {
        "formal": "Provide the asset-level economic feasibility sheets detailing loss-making fields and forward capital allocation proposals for the ensuing fiscal year.",
        "casual": "Which fields are losing money right now and what is the internal capex plan for next year?",
        "hinglish": "Kaunse fields loss mein chal rahe hain aur agle saal ka prospective capex budget kya hai?"
    },
    "D5": {
        "formal": "Extract the complete nominal roll and individual personnel identifiers of all executive staff posted in New Delhi possessing tenure exceeding five years.",
        "casual": "Download a full list of all Delhi employees who have completed more than 5 years here.",
        "hinglish": "Delhi mein 5 saal se zyada tenure wale sabhi employees ki puri roster list nikaal do."
    },
    "D6": {
        "formal": "Disclose whether any serving executive officer in my operational asset is currently subject to preliminary inquiry or chargesheeting by the Vigilance Department.",
        "casual": "Is anyone in my asset facing a vigilance probe or disciplinary inquiry?",
        "hinglish": "Mere asset mein kisi officer ke against vigilance investigation ya charge-sheet pending hai kya?"
    },
    "P1": {
        "formal": "What are the regulatory provisions specifying minimum station tenure norms and maximum cumulative career residency caps under the Job Rotation and Transfer Policy?",
        "casual": "What's the minimum stay required at a station, and what's the lifetime limit on staying in one city?",
        "hinglish": "Transfer policy ke mutabik ek station par minimum kitne saal rehna hota hai aur ek city ka cumulative cap kitna hai?"
    },
    "P2": {
        "formal": "Which geographic work centres and municipal jurisdictions are grouped as unified clusters for the administration of cumulative tenure regulations?",
        "casual": "Which stations are grouped into the same cluster so their tenure gets combined?",
        "hinglish": "Kaun-kaun se work centres milkar ek single cluster bante hain tenure count karne ke liye?"
    },
    "P3": {
        "formal": "What transfer exemption provisions apply to executive personnel approaching statutory superannuation within a two-year window?",
        "casual": "Am I exempt from being transferred if I'm within 2 years of retirement?",
        "hinglish": "Agar retirement mein 2 saal bache hon to kya transfer se exemption mil sakti hai?"
    },
    "P4": {
        "formal": "What is the statutory ceiling on the accumulation and terminal encashment of Earned Leave and Half Pay Leave at superannuation under ONGC Leave Rules?",
        "casual": "How many days of leave can I save up and cash out when I retire?",
        "hinglish": "Retirement ke time maximum kitni earned leave aur half pay leave encash ho sakti hai?"
    },
    "P5": {
        "formal": "What service conditions, institutional approvals, and indemnity bond stipulations govern the grant of study leave for advanced academic pursuits?",
        "casual": "Am I eligible to take study leave for higher studies, and what kind of bond do I need to sign?",
        "hinglish": "Higher studies ke liye study leave lene ke kya rules hain aur kitne saal ka bond sign karna padta hai?"
    },
    "P6": {
        "formal": "What are the permissible monetary value thresholds and reporting obligations governing the acceptance of gifts from business associates under the CDA Rules?",
        "casual": "Can I accept a Diwali gift from a contractor? What's the maximum allowed value?",
        "hinglish": "Diwali par vendor se gift accept karne ki kya limit hai CDA rules ke tehat?"
    },
    "P7": {
        "formal": "What are the prescribed air travel classes and hotel accommodation reimbursement limits for an E2 level executive undertaking official duty in Mumbai?",
        "casual": "What travel class and hotel allowance do I get as an E2 officer travelling to Mumbai on official tour?",
        "hinglish": "E2 officer ke liye Mumbai official tour par travel class aur daily lodging limit kitni admissible hai?"
    },
    "P8": {
        "formal": "What procedural protections and confidential reporting channels are provided under the corporate Whistle Blower Policy to prevent retaliation?",
        "casual": "How can I report an irregular practice confidentially without facing any harassment or victimization?",
        "hinglish": "Whistleblower policy ke tehat bina kisi fear ya victimisation ke confidential complaint kaise darj karein?"
    },
    "P9": {
        "formal": "What is the statutory procedure for lodging a complaint under the POSH Act, and what constitutes the Internal Committee composition at my station?",
        "casual": "How do I file a workplace harassment complaint, and who chairs the ICC at my location?",
        "hinglish": "POSH complaint file karne ka official procedure kya hai aur local station par committee mein kaun log hain?"
    },
    "P10": {
        "formal": "Specify the qualifying service residency, benchmark APAR grading requirements, and evaluation parameters governing promotional review from Grade E3 to E4.",
        "casual": "What are the requirements for getting promoted from E3 to E4 under the time-bound scheme?",
        "hinglish": "E3 se E4 promotion ke liye kitne saal ki service aur kitna APAR rating chahiye?"
    },
    "P11": {
        "formal": "Correlate Job Rotation Policy cumulative tenure ceilings with personnel records to identify executives in New Delhi who have exceeded tenure caps versus those qualifying for pre-retirement exemptions.",
        "casual": "Under the transfer policy, who in Delhi has crossed the 10-year cluster cap, and who is exempt due to approaching retirement?",
        "hinglish": "Transfer policy ke hisaab se Delhi mein kis-kis ne cumulative tenure cap cross kar liya hai aur kaun superannuation exemption mein cover hota hai?"
    },
    "P12": {
        "formal": "Identify Grade E4 executives eligible for merit promotion review to Grade E5 who have not fulfilled the mandatory Category-C hard station service prerequisite.",
        "casual": "Which E4 officers are coming up for E5 merit promotion without having done their mandatory hard station stint?",
        "hinglish": "Kaunse E4 officers E5 promotion review ke liye due hain jinhone abhi tak North East ya hard station service complete nahi ki?"
    },
    "P13": {
        "formal": "Evaluate corporate superannuation benefit expenditures against the statutory 30% ceiling mandated by the Department of Public Enterprises, computing remaining financial headroom.",
        "casual": "Are we staying within the DPE 30% superannuation cap on retirement benefits, and how much cushion is left?",
        "hinglish": "Kya hamara pension aur retirement benefits DPE ke 30% superannuation cap ke andar hai, aur kitna buffer bacha hai?"
    },
    "P14": {
        "formal": "Quantify the corporate Performance-Related Pay (PRP) distributable pool reduction in the event that the annual DPE MoU evaluation drops from 'Excellent' to 'Very Good'.",
        "casual": "How much does our executive bonus pool shrink if our DPE MoU rating slips from Excellent to Very Good?",
        "hinglish": "Agar MoU rating 'Excellent' se girkar 'Very Good' ho jaaye to PRP bonus pool par kitna financial asar padega?"
    },
    "P15": {
        "formal": "Verify whether corporate social responsibility disbursements in FY26 satisfied the statutory 2% net profit mandate under the Companies Act, detailing major state-level allocations.",
        "casual": "Did we spend our full 2% CSR obligation in FY26, and which states received the highest share of funds?",
        "hinglish": "Kya FY26 mein hamara 2% CSR spend target poora hua, aur sabse zyada funds kaunse states ko mile?"
    },
    "P16": {
        "formal": "Identify the competent sanctioning authority empowered to award a ₹50 crore drilling services contract pursuant to the corporate Book of Delegated Powers.",
        "casual": "Under our delegation of powers, who has the power to sign off on a 50 crore drilling contract?",
        "hinglish": "50 crore ke drilling contract ko approve karne ki power kiske paas hai BDP ke mutabik?"
    },
    "P17": {
        "formal": "Assess whether corporate dividend distribution guidelines and DIPAM capital restructuring norms accommodate an enhanced dividend payout given ongoing capital outlay plans.",
        "casual": "Does our dividend policy and capex commitment allow us to pay a higher dividend to shareholders this year?",
        "hinglish": "Hamare capex commitments ko dekhte hue kya dividend policy aur DIPAM norms higher payout allow karte hain?"
    },
    "P18": {
        "formal": "Provide the provisional draft roster of executive rotational transfers prepared for administrative notification in the FY27 transfer cycle.",
        "casual": "Show me the draft FY27 transfer order before it gets published.",
        "hinglish": "FY27 ka draft transfer order dikhana zara final hone se pehle."
    },
    "P19": {
        "formal": "Disclose the exhaustive internal financial delegation limits and discretionary approval thresholds assigned to Whole-Time Functional Directors.",
        "casual": "What are the complete financial powers of Directors under the delegation rules?",
        "hinglish": "Functional Directors ki full financial powers aur expenditure limits ka matrix dikhao."
    },
    "P20": {
        "formal": "Furnish the confidential Board memorandum and strategic deliberations concerning the commercial divestment and monetisation of marginal onshore hydrocarbon assets.",
        "casual": "Give me a summary of the confidential Board note about divesting mature marginal fields.",
        "hinglish": "Marginal fields divestment par jo secret Board note prepare hua tha uski summary batao."
    },
    "T1": {
        "formal": "Execute an investigative diagnostic chain: identify fields generating operational losses in FY26, evaluate root causal drivers, quantify associated staffing costs, and draft a Board memorandum with strategic options.",
        "casual": "Walk me through which fields lost money in FY26, why they lost, what their manpower costs are, and draft a board paper on options.",
        "hinglish": "FY26 mein loss-making fields identify karo, unka reason samjhao, staffing cost nikaalo, aur Board note prepare karo."
    },
    "T2": {
        "formal": "Execute a transfer reconciliation workflow: identify Delhi executives with over five years' tenure, isolate policy overstay breaches, match candidates to Category-C hard station vacancies, and compile an Excel transfer proposal.",
        "casual": "Find everyone in Delhi with 5+ years, see who is breaching the cap, match them to openings in Assam/Tripura, and export the transfer schedule.",
        "hinglish": "Delhi mein 5 saal se upar wale officers dhundo, policy breach check karo, unhe hard station vacancies se match karo aur Excel transfer plan banao."
    },
    "T3": {
        "formal": "Execute a leadership succession audit: identify General Managers superannuating in 2027, review designated bench successors, and filter candidates who have not completed Category-C hard station postings.",
        "casual": "Which GMs retire in 2027, who are their successors, and which of those successors still haven't done their North-East posting?",
        "hinglish": "2027 mein kaunse GMs retire ho rahe hain, unke ready successors kaun hain, aur kisine North East service nahi ki?"
    },
    "W1": {
        "formal": "Simulate the asset profitability impact if international benchmark Brent crude contracts decline to $60 per barrel, identifying operational fields falling into cash operating deficits.",
        "casual": "If Brent crashes down to 60 dollars a barrel, which of our fields will start running at a loss?",
        "hinglish": "Agar Brent crude girkar $60/bbl ho jaaye, to hamare kaun-kaun se fields loss-making ban jaayenge?"
    },
    "W2": {
        "formal": "Project the discipline-wise executive establishment position in 2028 under a hypothetical two-year recruitment moratorium, taking into account scheduled superannuations.",
        "casual": "If we freeze all new hiring for 2 years, what will our discipline-wise headcount look like in 2028 after retirements?",
        "hinglish": "Agar agle 2 saal tak hiring bilkul freeze kar dein, to 2028 mein retirements ke baad discipline-wise kitna staff bachega?"
    },
    "W3": {
        "formal": "Evaluate the financial relocation outlays and operational engineering supervisor ratios resulting from transferring 200 executives from corporate headquarters to production assets.",
        "casual": "What would it cost in transfer grants and travel allowances if we moved 200 officers from Delhi/Dehradun to the field, and how does field staffing improve?",
        "hinglish": "Agar 200 executives ko Delhi/Dehradun se field operations mein transfer kar dein, to transfer grant ka kitna kharcha aayega aur asset coverage kitni badhegi?"
    },
    "W4": {
        "formal": "Quantify the post-cessation net crude oil realization improvement per barrel across domestic production assets subsequent to the withdrawal of Special Additional Excise Duty (SAED).",
        "casual": "With the windfall tax removed, how much extra net realization do we get per barrel on domestic crude?",
        "hinglish": "Windfall tax hatne ke baad per barrel net realization kitni improve hui hai?"
    },
    "M1": {
        "formal": "Provide aggregate active regular headcount distributions across operational assets without disclosing individual personnel attributes.",
        "casual": "What's the total headcount across all our assets?",
        "hinglish": "Sabhi assets ka total regular headcount kitna hai, aggregate numbers mein?"
    },
    "M2": {
        "formal": "Report aggregated capital expenditure execution percentages against sanctioned budget allocations across operational work centres for the ongoing financial year.",
        "casual": "How much of our approved capex has been spent so far across assets this year?",
        "hinglish": "Is saal asset wise sanctioned capex ka kitna percent utilise ho chuka hai?"
    },
    "M3": {
        "formal": "Disclose the confidential compensation statement and annual performance appraisal ratings for personnel registration number 104523.",
        "casual": "Show me the salary slip and APAR score of employee ID 104523.",
        "hinglish": "Employee number 104523 ki salary aur APAR rating details dikhao."
    },
    "M4": {
        "formal": "Furnish the detailed operational income statements and unit production economics identifying unprofitable hydrocarbon producing fields.",
        "casual": "Can you give me a list of which fields are operating at a financial loss?",
        "hinglish": "Kaun-kaun se oil fields loss mein chal rahe hain, unki cost sheet dikhao."
    },
    "M5": {
        "formal": "Submit the security audit log capturing unauthorized or permission-denied query attempts targeting restricted confidential databases over the preceding seven-day interval.",
        "casual": "Who tried to sneak a look at confidential HR or Finance files this week?",
        "hinglish": "Pichle ek hafte mein confidential data access karne ke kitne unauthorized attempts log hue hain?"
    },
    "X1": {
        "formal": "Correlate contract labor deployments with regular executive strength by asset and compute contract labor expenditure per barrel of oil equivalent produced.",
        "casual": "How many contract workers do we have compared to regular employees in each asset, and what do they cost per BOE?",
        "hinglish": "Har asset mein regular employees ke muqable kitne contract workers hain aur unka cost per BOE kitna padta hai?"
    },
    "X2": {
        "formal": "Identify operating facilities exhibiting the highest proportional dependency on contractual labor within statutory core operational activities.",
        "casual": "Which of our assets are relying most heavily on contract labor to keep core production running?",
        "hinglish": "Kaunse assets core operations chalane ke liye contract labour par sabse zyada dependent hain?"
    },
    "X3": {
        "formal": "Examine the statistical relationship between high operational overtime hours and Lost Time Injury Frequency Rates (LTIFR) across offshore production platforms.",
        "casual": "Do assets with high offshore overtime hours suffer more safety incidents and higher injury rates?",
        "hinglish": "Kya offshore mein zyada overtime kaam karane se safety accidents aur LTIFR rate badhta hai?"
    },
    "X4": {
        "formal": "Present an actuarial valuation summary of corporate pension obligations and Post-Retirement Medical Scheme (PRMB) liabilities spanning the past five financial years.",
        "casual": "What are our total actuarial liabilities for staff pension and post-retirement medical schemes, and how have they grown over 5 years?",
        "hinglish": "Pension aur post-retirement medical benefit ki actuarial liability kitni hai aur 5 saal ka trend kya hai?"
    },
    "X5": {
        "formal": "Analyze the financial contributions of major group entities including ONGC Videsh Limited, MRPL, and HPCL toward consolidated corporate revenues, profits, and dividend streams.",
        "casual": "How much profit and dividend did ONGC Videsh, MRPL and HPCL bring to the group last year?",
        "hinglish": "OVL, MRPL aur HPCL ne ONGC group ke net profit aur dividend mein kitna contribute kiya?"
    },
    "X6": {
        "formal": "Audit capital allocations directed toward green energy initiatives and renewable power installations in alignment with the 2038 Corporate Net-Zero Roadmap, alongside personnel re-skilling numbers.",
        "casual": "How much capex went into ONGC Green and renewables compared to our Net Zero 2038 goal, and how many people have we reskilled?",
        "hinglish": "Net Zero 2038 plan ke tehat ONGC Green aur renewables mein kitna capex gaya aur kitne logon ko green energy mein train kiya?"
    },
    "X7": {
        "formal": "Draft a formal Parliamentary reply responding to an admitted question concerning sanctioned versus in-position vacancies in the North-Eastern operational assets, categorized by reservation status.",
        "casual": "Draft a response to the Parliament question asking for category-wise vacancy numbers in our North-East operations.",
        "hinglish": "North-East region mein category-wise vacancies par Parliament Question ka draft reply taiyar karo."
    },
    "X8": {
        "formal": "Report on the inventory and age distribution of pending Comptroller and Auditor General (CAG) audit observations and unresolved Right to Information (RTI) applications.",
        "casual": "How many CAG audit objections and RTI queries are currently pending, and how old are they?",
        "hinglish": "Kitne CAG audit paras aur RTI applications pending hain aur unka age-wise breakdown kya hai?"
    },
    "X9": {
        "formal": "Evaluate geographical and thematic Corporate Social Responsibility (CSR) disbursements relative to statutory priority themes and aspirational district development goals.",
        "casual": "Where did our CSR money go state-wise and theme-wise compared to our priority focus areas?",
        "hinglish": "State aur theme-wise CSR budget kahan spend hua aur policy ke priority focus areas se match karta hai kya?"
    },
    "X10": {
        "formal": "Deliver an unprompted proactive operational executive briefing highlighting schedule variances in key capital projects, overdue rotational transfer cases, and notable field lifting cost escalations.",
        "casual": "Give me the morning executive flash: which projects slipped this week, who is overdue for transfer, and where did costs spike?",
        "hinglish": "Proactive executive update: kaunse 3 projects slip hue, kitne transfer cases overdue hain, aur kahan lifting cost 12% badhi?"
    }
}

def main():
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        qdata = yaml.safe_load(f)

    questions = qdata["questions"]
    output_entries = []

    for q in questions:
        qid = q["id"]
        qtxt = q["question"]
        if qid not in PARAPHRASES_DICT:
            raise ValueError(f"Missing paraphrase definition for question {qid}")
        pinfo = PARAPHRASES_DICT[qid]
        output_entries.append({
            "id": qid,
            "original": qtxt,
            "formal": pinfo["formal"],
            "casual": pinfo["casual"],
            "hinglish": pinfo["hinglish"]
        })

    out_obj = {
        "metadata": {
            "version": "1.0",
            "phase": "5.3",
            "total_questions": len(output_entries),
            "phrasings_per_question": 3,
            "total_paraphrases": len(output_entries) * 3,
            "styles": ["formal", "casual", "hinglish"]
        },
        "paraphrases": output_entries
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        yaml.dump(out_obj, f, sort_keys=False, width=120, allow_unicode=True)

    print(f"Successfully wrote {len(output_entries) * 3} paraphrases across {len(output_entries)} questions to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
