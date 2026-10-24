import { isJunior } from '@/personas';
import { AnswerContract, PersonaType } from '@/contracts/answerContract';
import { FIXTURES, FixtureMeta } from '@/fixtures';
import { V2_FIXTURES } from '@/fixtures/v2';

export function routeQueryToFixture(
  query: string,
  currentPersona: PersonaType = 'CMD'
): { fixture: FixtureMeta; contract: AnswerContract } {
  const q = query.toLowerCase().trim();

  // Role-based refusal check
  if (isJunior(currentPersona) && 
      (q.includes('mumbai') || q.includes('transfer list') || q.includes('confidential') || q.includes('draft transfer'))) {
    const f = FIXTURES.find(x => x.id === 'd2_refusal')!;
    return { fixture: f, contract: f.data };
  }

  // Contract-v2 demo answers (U5): roster, masking by role, compare, insights + drill-downs, finance P&L
  const v2 = (id: string) => {
    const f = V2_FIXTURES.find((x) => x.id === id);
    return f ? { fixture: f, contract: f.data } : null;
  };
  const hrPeople = /(executive|officer|employee|people|staff)/.test(q);
  const wantsNames = hrPeople && /\b(names?|list|who are|roster|which officers|show me the people)\b/.test(q);
  if (wantsNames && isJunior(currentPersona)) { const r = v2('v2_roster_aggregate_e2'); if (r) return r; }
  if (wantsNames && currentPersona === 'DIR_FIN') { const r = v2('v2_roster_partial_dirfin'); if (r) return r; }
  if (wantsNames && /(all.?india|8 years|eight years|2,?000|everyone)/.test(q)) { const r = v2('v2_roster_2000'); if (r) return r; }
  if (wantsNames && /delhi/.test(q)) { const r = v2('v2_roster_419'); if (r) return r; }
  if ((currentPersona === 'CMD' || currentPersona === 'DIR_HR') && /(compare|\bvs\b|versus)/.test(q) && /delhi/.test(q) && /mumbai/.test(q)) { const r = v2('v2_compare_delhi_mumbai'); if (r) return r; }
  if (/headcount by work cent(re|er)|work cent(re|er) headcount/.test(q)) { const r = v2('v2_insights_drilldowns'); if (r) return r; }
  if (/profit and loss|p&l|p & l/.test(q)) { const r = v2('v2_finance_pnl'); if (r) return r; }

  // Refine E5+
  if (q.includes('e5') || q.includes('senior') || q.includes('only e5')) {
    const f = FIXTURES.find(x => x.id === 'c1_refine')!;
    return { fixture: f, contract: f.data };
  }

  // Brent $60
  if (q.includes('brent') || q.includes('$60') || q.includes('crude drop') || q.includes('waterfall')) {
    const f = FIXTURES.find(x => x.id === 'w1_waterfall')!;
    return { fixture: f, contract: f.data };
  }

  // Headcount vs production
  if (q.includes('production') && (q.includes('headcount') || q.includes('divergence') || q.includes('lost') || q.includes('added'))) {
    const f = FIXTURES.find(x => x.id === 'c11_combo')!;
    return { fixture: f, contract: f.data };
  }

  // Loss fields / Profit fields
  if (q.includes('loss') || q.includes('profitable') || q.includes('mumbai high south') || q.includes('champang') || q.includes('pbt')) {
    const f = FIXTURES.find(x => x.id === 'c6_hbar')!;
    return { fixture: f, contract: f.data };
  }

  // Parliament reply
  if (q.includes('parliament') || q.includes('rajya') || q.includes('lok sabha') || q.includes('north east') || q.includes('vacanc')) {
    const f = FIXTURES.find(x => x.id === 'x7_parliament')!;
    return { fixture: f, contract: f.data };
  }

  // Policy / Clause
  if (q.includes('tenure') || q.includes('clause') || q.includes('cumulative stay') || q.includes('policy') || q.includes('jrtp') || q.includes('srihari')) {
    const f = FIXTURES.find(x => x.id === 'p1_clause')!;
    return { fixture: f, contract: f.data };
  }

  // Map
  if (q.includes('map') || q.includes('geographic') || q.includes('all-india') || q.includes('work centres') || q.includes('footprint') || q.includes('where')) {
    const f = FIXTURES.find(x => x.id === 'map_headcount')!;
    return { fixture: f, contract: f.data };
  }

  // MoU
  if (q.includes('mou') || q.includes('target') || q.includes('mopng') || q.includes('dpe') || q.includes('achievement')) {
    const f = FIXTURES.find(x => x.id === 'c10_mou')!;
    return { fixture: f, contract: f.data };
  }

  // Receivables
  if (q.includes('receivable') || q.includes('aging') || q.includes('ageing') || q.includes('omc') || q.includes('adani') || q.includes('gail') || q.includes('dso')) {
    const f = FIXTURES.find(x => x.id === 'f6_receivables')!;
    return { fixture: f, contract: f.data };
  }

  // Transfer proposal table
  if (q.includes('proposal') || q.includes('roster') || q.includes('excel') || q.includes('table') || q.includes('fy27')) {
    const f = FIXTURES.find(x => x.id === 'h10_transfer')!;
    return { fixture: f, contract: f.data };
  }

  // Delhi tenure C1 default
  if (q.includes('delhi') || q.includes('station') || q.includes('5 year') || q.includes('overstay') || q.includes('executive')) {
    const f = FIXTURES.find(x => x.id === 'c1_donut')!;
    return { fixture: f, contract: f.data };
  }

  // Default to C1
  const defaultFixture = FIXTURES[0];
  return { fixture: defaultFixture, contract: defaultFixture.data };
}
