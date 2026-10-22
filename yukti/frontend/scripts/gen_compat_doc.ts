/* Generates docs/chart_compatibility.md from the engine itself (U5.7). Run: npx --yes tsx scripts/gen_compat_doc.ts */
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { kindsFor, profile } from '../src/charts/compat';
import type { VisualContainer } from '../src/contracts/answerContract';
import roster from '../src/fixtures/v2/v2_roster_419.json';
import pnl from '../src/fixtures/v2/v2_finance_pnl.json';
import hc from '../src/fixtures/v2/v2_insights_drilldowns.json';
import grades from '../src/fixtures/c1_donut_by_grade.json';

const samples: [string, string, VisualContainer][] = [
  ['Categorical, positive', 'Headcount by work centre (14)', (hc as any).visual],
  ['Categorical with losses', 'Field P&L FY26 (12, some negative)', (pnl as any).visual],
  ['Ordinal, multi-measure', 'Delhi 5+ yrs by grade (count/exempt/due)', (grades as any).visual],
  ['Time series', 'Revenue FY22–FY26', { type: 'chart', mode: 'replace', chart: { kind: 'line', x: 'fy', y: 'revenue_cr', data: ['FY22', 'FY23', 'FY24', 'FY25', 'FY26'].map((fy, i) => ({ fy, revenue_cr: 100 + i })) } } as VisualContainer],
  ['Distribution (binned)', 'Age bands', { type: 'chart', mode: 'replace', chart: { kind: 'histogram', x: 'bin', y: 'count', data: ['21–30', '31–40', '41–50', '51–60'].map((bin, i) => ({ bin, count: 10 + i })) } } as VisualContainer],
  ['Records (named people)', 'Delhi roster (419 rows)', (roster as any).visual],
  ['Single value', 'PAT FY26', { type: 'chart', mode: 'replace', chart: { kind: 'bar', x: 'm', y: 'v', data: [{ m: 'PAT', v: 1 }] } } as VisualContainer],
];
const sym = { native: '✅', transform: '🔄', alternative: '↪️' } as const;
const kinds = kindsFor(samples[0][2]).map((k) => k.kind);
let md = `# Chart compatibility matrix (U5.7)\n\n_Generated from \`src/charts/compat.ts\` by \`scripts/gen_compat_doc.ts\`; do not edit by hand._\n\n`;
md += `One engine (\`replot(visual, kind)\`) serves voice ("show as pie"), typed commands and the toolbar, so all three give the same picture. Re-plots are computed from the answer's original rows (kept in \`visual.source\`), never from the previous re-plot, so switching back and forth never drifts. No backend call.\n\n`;
md += `**Legend:** ✅ native · 🔄 transform (bins → slices, count by category, top-N + Others, measure selection) · ↪️ nearest alternative shown, with a one-line note\n\n`;
md += `| Data shape | Example | ${kinds.join(' | ')} |\n|---|---|${kinds.map(() => ':-:').join('|')}|\n`;
const notes: string[] = [];
for (const [shape, ex, v] of samples) {
  const ks = kindsFor(v);
  md += `| ${shape} (\`${profile(v).shape}\`) | ${ex} | ${ks.map((k) => sym[k.status]).join(' | ')} |\n`;
  ks.filter((k) => k.note).forEach((k) => notes.push(`- **${shape} → ${k.kind}** (${k.status}): ${k.note}`));
}
md += `\n## Transform rules\n- **Histogram → pie/donut/treemap/funnel/bar:** slices (bars) are exactly the histogram bins, in bin order.\n- **Records → pie/bar:** count people by the first low-cardinality column (e.g. grade); records → histogram bins the main numeric column (e.g. years of stay).\n- **Many categories → pie/donut:** top 9 + "Others (n)".\n- **Multi-measure → part-of-whole:** uses the selected metric (Metric menu / \`{ metric }\`).\n- **Losses → pie/donut/treemap/funnel:** not allowed (a part-of-whole can't be negative) → diverging bars.\n- **Time → pie:** shares of periods aren't meaningful → columns over time.\n- **Nominal categories → line/area/histogram:** implies order that doesn't exist → bars (histogram allowed as a value distribution when ≥ 8 items).\n- **Bullet:** needs a target column; otherwise ranked bars. **Scatter:** needs two measures.\n\n## Notes shown to the user\n${notes.join('\n')}\n`;
writeFileSync(fileURLToPath(new URL('../../../docs/chart_compatibility.md', import.meta.url)), md);
console.log('wrote docs/chart_compatibility.md', notes.length, 'notes');
