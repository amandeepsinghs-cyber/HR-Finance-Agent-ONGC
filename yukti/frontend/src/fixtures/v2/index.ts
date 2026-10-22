import { FixtureMeta } from '../index';
import { AnswerContract } from '@/contracts/answerContract';

import v2Roster419 from './v2_roster_419.json';
import v2Roster2000 from './v2_roster_2000.json';
import v2RosterPartialDirfin from './v2_roster_partial_dirfin.json';
import v2RosterAggregateE2 from './v2_roster_aggregate_e2.json';
import v2CompareDelhiMumbai from './v2_compare_delhi_mumbai.json';
import v2InsightsDrilldowns from './v2_insights_drilldowns.json';
import v2FinancePnl from './v2_finance_pnl.json';

export const V2_FIXTURES: FixtureMeta[] = [
  {
    id: 'v2_roster_419',
    name: 'V2 Delhi Roster (419)',
    question: 'Executives posted in Delhi for 5+ years',
    persona: 'CMD',
    type: 'table',
    data: v2Roster419 as unknown as AnswerContract,
  },
  {
    id: 'v2_roster_2000',
    name: 'V2 All-India Roster (2000)',
    question: 'All-India executives with 8+ years continuous stay',
    persona: 'CMD',
    type: 'table',
    data: v2Roster2000 as unknown as AnswerContract,
  },
  {
    id: 'v2_roster_partial_dirfin',
    name: 'V2 Delhi Roster Partial (DIR_FIN)',
    question: 'Executives posted in Delhi for 5+ years',
    persona: 'DIR_FIN',
    type: 'table (partial masking)',
    data: v2RosterPartialDirfin as unknown as AnswerContract,
  },
  {
    id: 'v2_roster_aggregate_e2',
    name: 'V2 Delhi Roster Aggregate (E2_HR)',
    question: 'Delhi executives with 5+ years stay by grade',
    persona: 'E2_HR',
    type: 'table (aggregate)',
    data: v2RosterAggregateE2 as unknown as AnswerContract,
  },
  {
    id: 'v2_compare_delhi_mumbai',
    name: 'V2 Compare Delhi vs Mumbai Headcount',
    question: 'Compare Delhi and Mumbai headcount by grade',
    persona: 'CMD',
    type: 'chart (compare)',
    data: v2CompareDelhiMumbai as unknown as AnswerContract,
  },
  {
    id: 'v2_insights_drilldowns',
    name: 'V2 Work Centre Headcount Insights & Drilldowns',
    question: 'Headcount by work centre, FY26',
    persona: 'CMD',
    type: 'chart (hbar with insights)',
    data: v2InsightsDrilldowns as unknown as AnswerContract,
  },
  {
    id: 'v2_finance_pnl',
    name: 'V2 Field-wise Profit and Loss',
    question: 'Field-wise profit and loss, FY26',
    persona: 'DIR_FIN',
    type: 'chart (hbar finance)',
    data: v2FinancePnl as unknown as AnswerContract,
  },
];
