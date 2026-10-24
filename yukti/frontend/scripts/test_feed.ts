/* Unit test for the conversation feed reducer (U2.2). Run: npm run test:unit */
import assert from 'node:assert/strict';
import { feedReducer, applyChartKind, latestAnswered, isReplotOf, Turn } from '../src/state/feed';
import type { AnswerContract } from '../src/contracts/answerContract';

const C = (id: string, extra: Partial<AnswerContract> = {}): AnswerContract => ({
  turn_id: id,
  language: 'en',
  spoken_summary: id,
  display_text: id,
  sources: [],
  access: { status: 'allowed' },
  visual: { type: 'chart', mode: 'replace', title: id, chart: { kind: 'bar', x: 'k', y: 'v', data: [{ k: 'a', v: 1 }, { k: 'b', v: 2 }] } },
  ...extra,
});

let passed = 0;
const t = (name: string, fn: () => void) => {
  fn();
  passed++;
  console.log('  ✓', name);
};

t('asking B after A keeps A', () => {
  let s: Turn[] = [];
  s = feedReducer(s, { type: 'ask', id: 'a', question: 'A?' });
  s = feedReducer(s, { type: 'answer', id: 'a', contract: C('A') });
  s = feedReducer(s, { type: 'ask', id: 'b', question: 'B?' });
  s = feedReducer(s, { type: 'answer', id: 'b', contract: C('B') });
  assert.equal(s.length, 2);
  assert.equal(s[0].contract?.turn_id, 'A');
  assert.equal(s[1].contract?.turn_id, 'B');
  assert.ok(s.every((x) => x.status === 'done'));
});

t('voice + text turns interleave (answer without id fills latest pending)', () => {
  let s: Turn[] = [];
  s = feedReducer(s, { type: 'ask', id: 'v1', question: 'Delhi', viaVoice: true });
  s = feedReducer(s, { type: 'question', id: 'v1', question: 'Delhi five years' });
  s = feedReducer(s, { type: 'answer', contract: C('V1') });
  s = feedReducer(s, { type: 'ask', id: 't1', question: 'typed' });
  s = feedReducer(s, { type: 'answer', id: 't1', contract: C('T1') });
  assert.deepEqual(s.map((x) => [x.id, x.question, x.contract?.turn_id]), [['v1', 'Delhi five years', 'V1'], ['t1', 'typed', 'T1']]);
  assert.equal(s[0].viaVoice, true);
});

t('answer with no pending turn appends', () => {
  let s: Turn[] = [];
  s = feedReducer(s, { type: 'answer', contract: C('X'), question: 'q', newId: 'n1' });
  assert.equal(s.length, 1);
  assert.equal(s[0].id, 'n1');
  assert.equal(s[0].fresh, true);
});

t('fail marks error; duplicate ask ignored', () => {
  let s: Turn[] = [];
  s = feedReducer(s, { type: 'ask', id: 'a', question: 'A?' });
  s = feedReducer(s, { type: 'ask', id: 'a', question: 'A?' });
  s = feedReducer(s, { type: 'fail', id: 'a', error: 'boom' });
  assert.equal(s.length, 1);
  assert.equal(s[0].status, 'error');
});

t('settle: empty voice turn dropped, spoken-only reply kept as text answer', () => {
  let s: Turn[] = [];
  s = feedReducer(s, { type: 'ask', id: 'v1', question: 'hello', viaVoice: true });
  s = feedReducer(s, { type: 'settle', id: 'v1', text: '' });
  assert.equal(s.length, 0);
  s = feedReducer(s, { type: 'ask', id: 'v2', question: 'hi', viaVoice: true });
  s = feedReducer(s, { type: 'settle', id: 'v2', text: 'Namaste, how can I help?' });
  assert.equal(s[0].status, 'done');
  assert.equal(s[0].contract?.visual?.type, 'none');
  assert.equal(s[0].contract?.display_text, 'Namaste, how can I help?');
});

t('refine updates the latest answered card in place (no new card)', () => {
  let s: Turn[] = [];
  s = feedReducer(s, { type: 'answer', contract: C('A'), newId: 'a' });
  s = feedReducer(s, { type: 'answer', contract: C('B'), newId: 'b' });
  s = feedReducer(s, { type: 'refine', update: (c) => applyChartKind(c, 'pie') });
  assert.equal(s.length, 2);
  assert.equal(s[1].contract?.visual?.chart?.kind, 'pie');
  assert.equal(s[0].contract?.visual?.chart?.kind, 'bar');
  // a refine while a new question is pending still targets the latest ANSWERED card
  s = feedReducer(s, { type: 'ask', id: 'c', question: 'C?' });
  s = feedReducer(s, { type: 'refine', update: (c) => applyChartKind(c, 'table') });
  assert.equal(s[1].contract?.visual?.type, 'table');
  assert.equal(latestAnswered(s)?.id, 'b');
});

t('applyChartKind: no-op for text answers and unknown kinds', () => {
  const txt = C('t', { visual: { type: 'none', mode: 'replace' } });
  assert.equal(applyChartKind(txt, 'pie'), txt);
  const c = C('c');
  assert.equal(applyChartKind(c, 'sparkles'), c);
});

t('isReplotOf: same title + rows + refine = re-plot; new question with refine mode = append', () => {
  const cur = C('A');
  const replot = { ...C('A2'), visual: { ...cur.visual!, mode: 'refine' as const, chart: { ...cur.visual!.chart!, kind: 'pie' as const } } };
  assert.equal(isReplotOf(replot, cur), true);
  const narrowed = { ...C('E5'), visual: { ...cur.visual!, mode: 'refine' as const, title: 'Only E5+', chart: { ...cur.visual!.chart!, data: [{ k: 'a', v: 1 }] } } };
  assert.equal(isReplotOf(narrowed, cur), false);
  let s: Turn[] = [];
  s = feedReducer(s, { type: 'ask', id: 'v', question: 'show as pie', viaVoice: true });
  s = feedReducer(s, { type: 'drop', id: 'v' });
  assert.equal(s.length, 0);
});

t('stale answer with an unknown explicit id is ignored (never fills another card)', () => {
  let s: Turn[] = [];
  s = feedReducer(s, { type: 'ask', id: 'new', question: 'New?' });
  s = feedReducer(s, { type: 'answer', id: 'old_dropped', contract: C('OLD') });
  assert.equal(s.length, 1);
  assert.equal(s[0].status, 'pending');
  assert.equal(s[0].contract, undefined);
});

t('re-plot false positive: same title + same row count + different values = append (G4 #2)', () => {
  const cur = C('A');
  const fy25 = { ...C('A_FY25'), visual: { ...cur.visual!, mode: 'refine' as const, chart: { ...cur.visual!.chart!, data: [{ k: 'a', v: 7 }, { k: 'b', v: 9 }] } } };
  assert.equal(isReplotOf(fy25, cur), false);
  const flagged = { ...C('X'), replot: true } as any;
  assert.equal(isReplotOf(flagged, cur), true);
  // backend table re-plot of the same rows is a re-plot
  const asTable = { ...C('T'), visual: { type: 'table' as const, mode: 'refine' as const, title: cur.visual!.title, table: { columns: ['k', 'v'], rows: [['b', 2], ['a', 1]] } } };
  assert.equal(isReplotOf(asTable, cur), true);
});

t('applyChartKind table keeps the source column names', () => {
  const c = C('A');
  const t = applyChartKind(c, 'table');
  assert.deepEqual(t.visual?.table?.columns, ['k', 'v']);
});

t('reset clears the feed', () => {
  let s: Turn[] = [];
  s = feedReducer(s, { type: 'answer', contract: C('A') });
  s = feedReducer(s, { type: 'reset' });
  assert.equal(s.length, 0);
});

t('P5.2 (BEH-07.31, BUG-18): duplicate turn_id updates in place and settle ignores speakId turns', () => {
  let s: Turn[] = [];
  s = feedReducer(s, { type: 'answer', contract: C('T1'), newId: 'card1', speakId: 'sp-1' });
  assert.equal(s.length, 1);
  // Duplicate answer with same turn_id updates existing card instead of appending a second card
  s = feedReducer(s, { type: 'answer', contract: C('T1', { display_text: 'Updated T1' }) });
  assert.equal(s.length, 1);
  assert.equal(s[0].contract?.display_text, 'Updated T1');
  // Settle on a turn with speakId does not overwrite the contract
  s = feedReducer(s, { type: 'settle', id: 'card1', text: 'raw live echo' });
  assert.equal(s.length, 1);
  assert.equal(s[0].contract?.display_text, 'Updated T1');
});

console.log(`feed reducer: ${passed} passed`);
