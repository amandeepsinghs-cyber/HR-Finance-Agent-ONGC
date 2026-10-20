import { AnswerContract } from '@/contracts/answerContract';

import c1Donut from './c1_donut_by_grade.json';
import c1Refine from './c1_refine_e5_plus.json';
import c11Combo from './c11_combo_headcount_prod.json';
import c6Hbar from './c6_hbar_loss_fields.json';
import w1Waterfall from './w1_waterfall_brent60.json';
import x7Parliament from './x7_parliament_reply.json';
import p1Clause from './p1_clause_card.json';
import d2Refusal from './d2_refusal_e2.json';
import mapHeadcount from './map_headcount_by_asset.json';
import c10Mou from './c10_mou_bullet.json';
import f6Receivables from './f6_receivables_ageing.json';
import h10Transfer from './h10_transfer_proposal_table.json';

export interface FixtureMeta {
  id: string;
  name: string;
  question: string;
  persona: string;
  type: string;
  data: AnswerContract;
}

export const FIXTURES: FixtureMeta[] = [
  {
    id: 'c1_donut',
    name: 'C1 Delhi Tenure Donut',
    question: 'How many executives have been posted in the Delhi office for 5 years or more? Break down by grade and discipline.',
    persona: 'CMD',
    type: 'chart (donut)',
    data: c1Donut as unknown as AnswerContract,
  },
  {
    id: 'c1_refine',
    name: 'C1 Refine (E5+ Senior)',
    question: 'Only E5 and above.',
    persona: 'CMD',
    type: 'chart (bar refine)',
    data: c1Refine as unknown as AnswerContract,
  },
  {
    id: 'c11_combo',
    name: 'C11 Headcount vs Production',
    question: 'Which assets added headcount but lost production over 5 years?',
    persona: 'CMD',
    type: 'chart (grouped bar)',
    data: c11Combo as unknown as AnswerContract,
  },
  {
    id: 'c6_hbar',
    name: 'C6 Profit vs Loss Fields',
    question: 'Which fields or assets were the most profitable and which made losses in FY26?',
    persona: 'CMD',
    type: 'chart (hbar)',
    data: c6Hbar as unknown as AnswerContract,
  },
  {
    id: 'w1_waterfall',
    name: 'W1 Brent $60 Stress Test',
    question: 'If Brent falls to $60/bbl, which fields go into loss?',
    persona: 'CMD',
    type: 'chart (waterfall)',
    data: w1Waterfall as unknown as AnswerContract,
  },
  {
    id: 'x7_parliament',
    name: 'X7 Parliament Reply',
    question: 'Draft a reply to a Parliament question: "Vacancies in ONGC in the North-East region, category-wise."',
    persona: 'CMD',
    type: 'document (preview)',
    data: x7Parliament as unknown as AnswerContract,
  },
  {
    id: 'p1_clause',
    name: 'P1 Tenure Policy Clause',
    question: 'What is the minimum tenure at a station, and the maximum cumulative stay in one city?',
    persona: 'CMD',
    type: 'clause card',
    data: p1Clause as unknown as AnswerContract,
  },
  {
    id: 'd2_refusal',
    name: 'D2 Refusal (E2 HR Role)',
    question: 'Show me the draft transfer list for Mumbai.',
    persona: 'E2_HR',
    type: 'refusal card',
    data: d2Refusal as unknown as AnswerContract,
  },
  {
    id: 'map_headcount',
    name: 'Map: Headcount by Asset',
    question: 'Show me the geographic distribution of ONGC executives across work centres in India.',
    persona: 'CMD',
    type: 'map (geo)',
    data: mapHeadcount as unknown as AnswerContract,
  },
  {
    id: 'c10_mou',
    name: 'C10 MoU Performance',
    question: 'How are we tracking against our MoU targets with MoPNG/DPE for this year?',
    persona: 'CMD',
    type: 'chart (bullet / gauge)',
    data: c10Mou as unknown as AnswerContract,
  },
  {
    id: 'f6_receivables',
    name: 'F6 Receivables Ageing',
    question: 'How old are receivables from oil marketing companies and gas buyers, by customer?',
    persona: 'CMD',
    type: 'chart (stacked bar)',
    data: f6Receivables as unknown as AnswerContract,
  },
  {
    id: 'h10_transfer',
    name: 'H10 Transfer Proposal Table',
    question: 'Generate an Excel transfer proposal for FY27 using rotation rules.',
    persona: 'DIR_HR',
    type: 'table (paged & sortable)',
    data: h10Transfer as unknown as AnswerContract,
  },
];
