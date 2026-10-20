# ONGC HR & Finance Agent: Question Bank v2 (Draft for Discussion)

> v2 adds §5 Policy questions, §6 Follow-up chains, §7 What-ifs, §8 Asset Manager persona and §9 Additional themes.

> [!NOTE]
> This draft covers questions only. It does not cover data, UI or Cloud Run. Each question names the **decision** it drives, because that is what makes it a CMD question rather than a report request. Asset and office names are real ONGC locations, used for realism. All figures will be synthetic.

**Personas:** CMD · Director (HR) · Director (Finance) · E1–E4 Officer
**Locations used:** Corporate HQ Delhi (Deendayal Urja Bhawan), Dehradun (Tel Bhavan, KDMIPE, GEOPIC), Mumbai (Mumbai High, Neelam-Heera, Bassein & Satellite), Ahmedabad, Ankleshwar, Mehsana, Cambay, Rajahmundry (KG), Karaikal (Cauvery), Sivasagar/Nazira & Jorhat (Assam), Agartala (Tripura), Silchar

---

## 1. CMD: Cross-functional, decision-grade questions

The CMD's questions combine HR and Finance. That combination is what breaking the data silos means in practice.

### 1A. People and transfers
| # | Question | Decision it drives |
|---|---|---|
| C1 | How many executives have been posted in the Delhi office for 5 years or more? Break down by grade and discipline. | Transfer rotation *(from verbatim)* |
| C2 | Who is overdue for transfer under the rotation policy, and which hard or remote stations (NE, offshore) are short of people to receive them? | Annual transfer order |
| C3 | Which areas saw no headcount increase in the last 5 years, and which saw the most? | Manpower rebalancing *(from verbatim)* |
| C4 | How many E7+ (GM and above) officers retire in the next 3 years, and which of those roles have no ready successor? | Succession planning |
| C5 | Which disciplines (geoscience, drilling, reservoir, production) face the biggest retirement-driven skill gap by 2030? | Recruitment and campus hiring |

### 1B. Money and assets
| # | Question | Decision it drives |
|---|---|---|
| C6 | Which fields or assets were the most profitable and which made losses in FY26? | Portfolio focus *(from verbatim)* |
| C7 | Where have we invested the most capex in the last 5 years, and which fields are under-invested relative to their reserves? | Capex reallocation *(from verbatim)* |
| C8 | Which loss-making mature fields are candidates for divestment, a Production Enhancement Contract, or a marginal-field offer? | Monetise or exit |
| C9 | Which major projects are behind schedule or over budget, and by how many crore? | Project intervention |
| C10 | How are we tracking against our MoU targets with MoPNG/DPE for this year? | Board and Ministry review |

### 1C. Cross-silo (HR × Finance), the showcase questions
| # | Question | Decision it drives |
|---|---|---|
| C11 | Which assets added headcount but lost production over 5 years? | Productivity correction |
| C12 | What is the manpower cost per barrel of oil equivalent (BOE), by asset? | Benchmarking and restructuring |
| C13 | If we move 200 executives from Delhi/Dehradun to field assets, what changes in cost and coverage? | Transfer impact simulation |
| C14 | Prepare a one-page board note on the top 5 loss-making fields: production, cost, staffing and a recommendation. | **Document output** |

---

## 2. Director (HR)

| # | Question | Decision it drives |
|---|---|---|
| H1 | List the executives with more than 3 years at their current station (rotation policy), by asset and grade. | Draft transfer list |
| H2 | Which employees have never served in a hard or remote station? | Fair rotation |
| H3 | What is the vacancy position (sanctioned vs. in-position) by asset and discipline? | Recruitment plan |
| H4 | What are attrition and voluntary-exit numbers by grade over the last 3 years? Is mid-career attrition (E3–E5) rising? | Retention measures |
| H5 | How many DPC (promotion) cases are pending, and for how long? | Clear the promotion backlog |
| H6 | Are we compliant with reservation norms (SC/ST/OBC/EWS/PwD) by grade? | Statutory compliance |
| H7 | What is women's representation by grade and asset, and what has it been for offshore postings? | Diversity targets |
| H8 | What were training hours per executive last year, and which disciplines are below target? | L&D budget (ONGC Academy, IOGPT, KDMIPE) |
| H9 | How many grievances and service litigations are pending, and how old are they? | Grievance resolution |
| H10 | Generate an Excel transfer proposal for FY27 using rotation rules. | **Sheet output** |

## 3. Director (Finance)

| # | Question | Decision it drives |
|---|---|---|
| F1 | What is the lifting cost ($/bbl) by asset, and which assets are above the company average? | Cost optimisation |
| F2 | What is capex utilisation (budget vs. revised estimate vs. actual) by asset for the current year? | Mid-year budget revision |
| F3 | What is the revenue, opex and EBITDA for each field over 5 years? | Field P&L review |
| F4 | How much did royalty, cess and windfall tax reduce realisation per barrel this year? | Policy representation to the Ministry |
| F5 | Which contracts or vendors make up the top 80% of spend, and where were the cost overruns? | Contract renegotiation |
| F6 | How old are receivables from oil marketing companies and gas buyers, by customer? | Working capital |
| F7 | What is the employee cost as a percentage of revenue, by asset, and how has it trended? | Manpower cost control |
| F8 | What is the finding & development cost and reserve replacement ratio, by basin? | Exploration budget |
| F9 | What are the forex exposure and hedging position on dollar-linked contracts? | Treasury |
| F10 | Generate a quarterly asset-wise P&L sheet. | **Sheet output** |

---

## 4. E1–E4 Officer: Allowed vs. denied (the RBAC showcase)

### 4A. Allowed (self-service and published policy)
| # | Question |
|---|---|
| E1 | What is my leave balance, and how many earned leave days can I encash? |
| E2 | When am I due for transfer, and what is the rotation policy for my grade? |
| E3 | What is my medical reimbursement claim status? |
| E4 | What are the eligibility criteria for promotion from E2 to E3? |
| E5 | What is the TA/DA entitlement for an offshore posting? |
| E6 | Which training programmes can I take this year? |
| E7 | What was ONGC's published annual profit last year? *(public data)* |

### 4B. Denied (should trigger a clear refusal)
| # | Question | Why denied |
|---|---|---|
| D1 | What is the salary of my reporting officer? | Personal data of another employee |
| D2 | Show me the draft transfer list for Mumbai. | Confidential and pre-decision |
| D3 | Who is getting promoted in the next DPC? | Confidential |
| D4 | Which fields are loss-making, and what is the capex plan for next year? | Unpublished commercial data |
| D5 | List all employees in Delhi with more than 5 years' tenure. | Bulk HR data; management only |
| D6 | Is any officer in my asset under vigilance inquiry? | Highly restricted |

### 4C. Same question, different answer (best demo moment)
| Question | CMD | Dir (HR) | Dir (Finance) | E2 Officer |
|---|---|---|---|---|
| "Which fields are loss-making?" | Full | Summary | Full | Denied |
| "Who in Delhi has 5+ years' tenure?" | Full | Full | Count only | Denied |
| "What is the manpower cost per BOE by asset?" | Full | Full | Full | Denied |

---

## 5. Policy questions *(v2, the "policies at your fingertips" win)*

Document IDs (A1, B1, …) refer to [policy_corpus.md](file:///usr/local/google/home/amandeepsinghs/.gemini/jetski/brain/fd024626-b38e-48a5-ae39-8b4b562295c0/policy_corpus.md).

### 5A. Policy look-up (any employee)
| # | Question | Source | Persona |
|---|---|---|---|
| P1 | What is the minimum tenure at a station, and the maximum cumulative stay in one city? | B1 JRTP | All |
| P2 | Which stations count as one cluster for tenure purposes? | B1 JRTP | All |
| P3 | Am I exempt from transfer if I retire in 2 years? | B1 JRTP | All |
| P4 | How many earned leave days can I accumulate and encash at retirement? | B3 Leave Rules | All |
| P5 | Am I eligible for study leave, and what bond applies? | B3 Leave Rules | All |
| P6 | Can I accept a gift from a vendor at Diwali? What is the limit? | B4 CDA Rules | All |
| P7 | What is my travel class and lodging allowance for official travel to Mumbai as an E2? | B6 TA/DA | All |
| P8 | How do I raise a concern confidentially without being victimised? | A1 Whistle Blower | All |
| P9 | How do I file a POSH complaint, and who is on the committee at my station? | A17 POSH | All |
| P10 | What are the criteria for promotion from E3 to E4? | B5 R&P Regs | All |

### 5B. Policy + live data (management, the strongest showcase)
| # | Question | Combines | Persona |
|---|---|---|---|
| P11 | Under the transfer policy, who in Delhi has exceeded the cumulative-tenure cap, and who is exempt because they retire soon? | B1 + HR data | CMD, Dir HR |
| P12 | Which executives are due for an E4→E5 merit review and have **not** done a North-East or hard posting? | B1, B5 + HR data | Dir HR |
| P13 | Are we within the DPE 30% superannuation cap on benefits? How much headroom is left? | A13 + Finance data | Dir Fin |
| P14 | Our MoU rating sets the performance-related pay pool. What's the pay impact if we drop from "Excellent" to "Very Good"? | A13, A14 + Finance data | CMD, Dir Fin |
| P15 | Did we meet the 2% CSR obligation in FY26? Which states got the most? | A16, A2 + Finance data | Dir Fin |
| P16 | Who has the authority to approve a ₹50 crore drilling contract under the delegated powers? | B2 BDP | E5+ |
| P17 | Does our dividend policy allow a higher payout this year, given the capex plan? | A3 + Finance data | CMD, Dir Fin |

### 5C. Policy refusals
| # | Question | Persona | Result |
|---|---|---|---|
| P18 | Show me the Draft FY27 Transfer Order. | E2 | **Denied.** The agent offers the *Transfer Policy* instead. |
| P19 | What are the full financial limits for Directors in the delegated powers? | E2 | **Denied.** Summary only. |
| P20 | Summarise the Board note on divesting marginal fields. | Dir HR | **Denied.** Finance and CMD only. |

---

## 6. Follow-up chains *(v2)*
| Chain | Steps |
|---|---|
| T1: Loss-making fields | "Which fields lost money in FY26?" → "Why is Field X losing?" → "How many people work there, and what do they cost?" → "Draft a board note with options." |
| T2: Delhi transfers | "Who in Delhi has 5+ years?" → "Which of them breach the transfer policy?" → "Match them to vacancies at hard stations." → "Export as an Excel transfer proposal." |
| T3: Succession | "Which GMs retire in 2027?" → "Who is ready to succeed each?" → "Which successors haven't served in the North East?" |

## 7. What-if questions *(v2)*
| # | Question | Persona |
|---|---|---|
| W1 | If Brent falls to $60/bbl, which fields go into loss? | CMD, Dir Fin |
| W2 | If we freeze hiring for 2 years, what will headcount be by discipline in 2028, given retirements? | CMD, Dir HR |
| W3 | If we move 200 executives from Delhi/Dehradun to field assets, what happens to transfer-grant cost and asset coverage? | CMD |
| W4 | If the windfall tax is removed, how much does net realisation per barrel improve? | Dir Fin |

## 8. E1–E4 functional split: HR officer vs. Finance officer *(v2.1; replaces the Asset Manager persona)*
| # | Question | E1–E4 HR officer | E1–E4 Finance officer |
|---|---|---|---|
| M1 | "What is the total headcount by asset?" (aggregate, non-identifying) | Allowed | **Denied** |
| M2 | "What is the capex utilisation by asset this year?" (aggregate) | **Denied** | Allowed |
| M3 | "Show me the salary and APAR of employee 104523." | **Denied** | **Denied** |
| M4 | "Which fields are loss-making?" | **Denied** | **Denied** (Board-level commercial data) |
| M5 | CMD: "Who tried to access confidential data this week?" | n/a (CMD only, audit trail of refusals) | |

## 9. Additional themes *(v2)*
| # | Theme | Question | Persona |
|---|---|---|---|
| X1 | Contract workforce | How many contract workers vs. regular employees per asset, and at what cost per BOE? | CMD, Dir HR |
| X2 | Contract workforce | Which assets rely most on contract labour for core operations? | Dir HR |
| X3 | Safety (HSE) × HR | Do assets with higher offshore overtime show a higher lost-time injury rate? | CMD |
| X4 | Retirement liabilities | What is our pension and post-retirement medical liability, and its 5-year trend? | Dir Fin |
| X5 | Subsidiaries | How did ONGC Videsh, MRPL and HPCL contribute to group profit and dividend? | CMD |
| X6 | Energy transition | How much capex went to ONGC Green / renewables vs. the Net Zero 2038 path, and how many people have been reskilled? | CMD |
| X7 | Parliament | Draft a reply to a Parliament question: "Vacancies in ONGC in the North-East region, category-wise." | CMD, Dir HR (**document output**) |
| X8 | Audit (CAG) / RTI | How many audit (CAG) objections and right-to-information (RTI) applications are pending, and how old are they? | CMD |
| X9 | CSR | CSR spend by state and theme vs. the policy's priority areas | Dir Fin |
| X10 | Morning briefing | *Unprompted:* "3 projects slipped this week; 42 rotation cases overdue; Field X lifting cost up 12%." | CMD |

---

## Open points for discussion
1. **Title:** at ONGC, "CMD" is *Chairman & Managing Director*. Should the demo use that title?
2. **More directors:** add Director (Onshore), Director (Offshore) or Director (Exploration), or keep only HR and Finance?
3. **E1–E4 scope:** one generic junior persona, or separate E1 and E4 personas (an E4 sees team-level data)?
4. **Size:** now about 95 questions. Pick about 15 "hero" questions plus 2 chains for the live demo?
5. **Internal rulebooks:** do you (or the client) have the real JRTP, Delegated Powers, Leave and TA/DA documents? If not, should we write demo-faithful synthetic versions?
6. **Questions you planned to share:** send them and I'll merge and de-duplicate.
