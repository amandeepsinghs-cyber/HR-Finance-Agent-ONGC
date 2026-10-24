// P4.7 (SPEC-10 §4.8, §4.9): export intents (45 positive EN/HI + 10 negative), uiCommands routing, file names.
// Run: npx --yes tsx scripts/test_export_frontend.ts
import assert from 'node:assert/strict';
import { resolveExportIntent, normalizeExportFormat, EXPORT_MENU } from '../src/services/exportIntent';
import { parseUiCommands } from '../src/services/uiCommands';
import { exportFilename, filenamePartsFromContract, slugToken, NAMING_REGEX } from '../src/charts/exportImage';

let pass = 0;
const fails: string[] = [];
const check = (name: string, fn: () => void) => {
  try {
    fn();
    pass++;
  } catch (e: any) {
    fails.push(`${name}: ${e?.message || e}`);
  }
};

// [utterance, expected format, defaulted?]
const POSITIVE: [string, string, boolean][] = [
  // xlsx
  ['export to excel', 'xlsx', false],
  ['download this as xlsx', 'xlsx', false],
  ['export the table to a spreadsheet', 'xlsx', false],
  ['save it as an excel workbook', 'xlsx', false],
  ['इसे एक्सेल में डाउनलोड करो', 'xlsx', false],
  ['excel mein download karo', 'xlsx', false],
  // csv
  ['export as csv', 'csv', false],
  ['download comma separated file', 'csv', false],
  ['सीएसवी में डाउनलोड करो', 'csv', false],
  ['save the roster as csv', 'csv', false],
  // pdf
  ['export to pdf', 'pdf', false],
  ['download a printable version', 'pdf', false],
  ['save this as pdf', 'pdf', false],
  ['इसे पीडीएफ में डाउनलोड करो', 'pdf', false],
  ['प्रिंट के लिए डाउनलोड करो', 'pdf', false],
  // png
  ['download the chart as png', 'png', false],
  ['export this chart as an image', 'png', false],
  ['save the graph as a picture', 'png', false],
  ['चार्ट को इमेज में डाउनलोड करो', 'png', false],
  ['फोटो डाउनलोड करो', 'png', false],
  // svg
  ['export the chart as svg', 'svg', false],
  ['download as vector', 'svg', false],
  ['एसवीजी में डाउनलोड करो', 'svg', false],
  // docx
  ['export to word', 'docx', false],
  ['download this as a word document', 'docx', false],
  ['save as docx', 'docx', false],
  ['वर्ड में डाउनलोड करो', 'docx', false],
  ['डॉक्यूमेंट डाउनलोड करो', 'docx', false],
  // eml
  ['download the email file', 'eml', false],
  ['export as an outlook draft', 'eml', false],
  ['save as eml', 'eml', false],
  ['ईमेल फ़ाइल डाउनलोड करो', 'eml', false],
  // sheets
  ['export this statement to google sheets', 'sheets', false],
  ['export to gsheet', 'sheets', false],
  ['गूगल शीट में एक्सपोर्ट करो', 'sheets', false],
  // docs
  ['export to google docs', 'docs', false],
  ['download it as a gdoc', 'docs', false],
  ['गूगल डॉक में एक्सपोर्ट करो', 'docs', false],
  // defaults (no format word)
  ['download the chart', 'png', true],
  ['export the table', 'xlsx', true],
  ['export the statement', 'xlsx', true],
  ['चार्ट डाउनलोड करो', 'png', true],
  ['टेबल डाउनलोड करो', 'xlsx', true],
  ['export this', 'auto', true],
  ['इसे डाउनलोड करो', 'auto', true],
];

const NEGATIVE = [
  'how many employees are in delhi',
  'show revenue for fy24',
  'what is the excel formula for wacc',
  'compare pdf policy clauses for leave',
  'show me the numbers in the balance sheet',
  'why did the image of ongc improve',
  'switch to dark mode',
  'show this as a bar chart',
  'email the list to director hr',
  'which document covers transfer policy',
];

assert.equal(POSITIVE.length, 45, 'positive set must be 45');
assert.equal(NEGATIVE.length, 10, 'negative set must be 10');

for (const [q, fmt, defaulted] of POSITIVE) {
  check(`intent "${q}"`, () => {
    const r = resolveExportIntent(q);
    assert.ok(r, 'no intent');
    if (fmt === 'auto') {
      assert.equal(r!.defaulted, true);
      assert.equal(r!.target, undefined);
    } else {
      assert.equal(r!.format, fmt);
      assert.equal(r!.defaulted, defaulted);
    }
    // the instant UI parser routes it to an export command (never to a re-plot or backend)
    const cmds = parseUiCommands(q);
    assert.ok(cmds && cmds.length === 1 && cmds[0].action === 'export', `parseUiCommands → ${JSON.stringify(cmds)}`);
    const v = String(cmds![0].value);
    if (fmt === 'auto') assert.equal(v, 'auto');
    else assert.equal(v.split(':')[0], fmt);
  });
}
let negHits = 0;
for (const q of NEGATIVE) {
  const r = resolveExportIntent(q);
  const cmds = parseUiCommands(q);
  const isExport = !!r || !!cmds?.some((c) => c.action === 'export');
  if (isExport) {
    negHits++;
    fails.push(`negative "${q}" was treated as export`);
  } else pass++;
}

check('visual-type default when no target', () => {
  assert.equal(resolveExportIntent('export this', 'chart')!.format, 'png');
  assert.equal(resolveExportIntent('export this', 'table')!.format, 'xlsx');
  assert.equal(resolveExportIntent('export this', 'statement')!.format, 'xlsx');
});
check('normalizeExportFormat', () => {
  assert.equal(normalizeExportFormat('excel'), 'xlsx');
  assert.equal(normalizeExportFormat('word'), 'docx');
  assert.equal(normalizeExportFormat('google sheets'), 'sheets');
  assert.equal(normalizeExportFormat('PNG'), 'png');
  assert.equal(normalizeExportFormat(''), 'auto');
  assert.equal(normalizeExportFormat('nonsense'), 'auto');
});
check('menu has the 8 SPEC-10 items, PNG/SVG chart-only', () => {
  assert.deepEqual(EXPORT_MENU.map((m) => m.format), ['xlsx', 'csv', 'pdf', 'png', 'svg', 'docx', 'sheets', 'docs']);
  assert.deepEqual(EXPORT_MENU.filter((m) => m.chartOnly).map((m) => m.format), ['png', 'svg']);
});

const NOW = new Date(Date.UTC(2026, 9, 23, 10, 12));
check('filename: SPEC-10 example shape', () => {
  const f = exportFilename({ subject: 'Delhi >5y roster', scope: 'WC-DEL', period: 'asof-20261019', persona: 'CMD', ext: 'png', now: NOW });
  assert.equal(f, 'yukti_delhi_gt5y_roster_wc-del_asof-20261019_cmd_20261023-1012.png');
  assert.ok(NAMING_REGEX.test(f));
});
check('filename: aggregate suffix + persona underscore', () => {
  const f = exportFilename({ subject: 'Delhi by level', scope: 'wc-del', period: 'asof-20261019', persona: 'E2_HR', ext: 'svg', aggregate: true, now: NOW });
  assert.ok(f.endsWith('_e2_hr_20261023-1012_aggregate.svg'), f);
  assert.ok(NAMING_REGEX.test(f));
});
check('filename: Hindi-only title → ASCII, ≤ 80 chars before extension', () => {
  const f = exportFilename({ subject: 'दिल्ली में पाँच साल से अधिक समय वाले कर्मचारियों की बहुत लंबी सूची '.repeat(3), persona: 'DIR_HR', ext: 'png', now: NOW });
  assert.ok(/^[\x00-\x7f]+$/.test(f), f);
  assert.ok(f.replace(/\.png$/, '').length <= 80, `${f.length}`);
  assert.ok(NAMING_REGEX.test(f), f);
});
check('filename parts from contract (FY range, as-of, wc)', () => {
  const p1 = filenamePartsFromContract({ visual: { title: 'P&L FY22–FY26' } });
  assert.equal(p1.period, 'fy22-fy26');
  const p2 = filenamePartsFromContract({ visual: { title: 'Delhi roster' }, query_spec: { as_of: '2026-10-19', filters: { wc_id: 'WC-DEL' } } });
  assert.equal(p2.scope, 'wc-del');
  assert.equal(p2.period, 'asof-20261019');
  assert.equal(slugToken('P&L >= 5%'), 'pandl_ge_5');
});

console.log(`export intents: ${POSITIVE.length - fails.filter((f) => f.startsWith('intent')).length}/45 positive, ${negHits}/10 negatives misfired`);
if (fails.length) {
  console.log(fails.map((f) => '  ✗ ' + f).join('\n'));
  process.exit(1);
}
console.log(`${pass} passed`);
