/**
 * P2H.4 (SPEC-07 §4.4 / AC-04): Frontend export-intent unit test sharing
 * `yukti/contracts/intents/export_intent.json` with the backend (`test_export_intent.py`).
 *
 * Runs both via `npx tsx src/services/__tests__/exportIntent.test.ts` and under Vitest/Node test runners.
 */
import assert from 'node:assert/strict';
import exportIntentSpec from '../../../../contracts/intents/export_intent.json';
import { detectExportIntent, parseUiCommands } from '../uiCommands';

function runExportIntentSuite(): void {
  const positives: string[] = exportIntentSpec.positive_utterances || [];
  const negatives: string[] = exportIntentSpec.negative_utterances || [];

  assert.ok(positives.length >= 40, `Expected >= 40 positive utterances, got ${positives.length}`);
  assert.ok(negatives.length >= 10, `Expected >= 10 negative utterances, got ${negatives.length}`);

  for (const utterance of positives) {
    const det = detectExportIntent(utterance);
    assert.ok(det !== null, `Failed to detect positive export utterance: "${utterance}"`);
    assert.equal(det.action, 'export', `Wrong action for "${utterance}": ${det.action}`);
    assert.equal(det.value, 'xlsx', `Expected xlsx format for "${utterance}", got ${det.value}`);

    const cmds = parseUiCommands(utterance);
    assert.ok(cmds && cmds.length === 1 && cmds[0].action === 'export', `parseUiCommands failed on "${utterance}"`);
  }

  for (const utterance of negatives) {
    const det = detectExportIntent(utterance);
    assert.equal(det, null, `False positive on negative utterance: "${utterance}"`);

    const cmds = parseUiCommands(utterance);
    const hasExport = (cmds || []).some((c) => c.action === 'export');
    assert.equal(hasExport, false, `parseUiCommands returned export on negative utterance: "${utterance}"`);
  }

  // SPEC-07 §4.4 / P2H.4 §6 column-order honouring
  const v19Turn4 =
    'Can you export this as an Excel file? Their names, their designations, their ranks from E1 to whatever level, and their tenure in Delhi';
  const v19Det = detectExportIntent(v19Turn4);
  assert.ok(v19Det !== null);
  assert.deepEqual(v19Det.columns, ['Name', 'Designation', 'Level', 'Tenure in Delhi (yrs)']);

  const hinglishCols = 'sirf naam aur Delhi tenure ko excel mein export karo';
  const hiDet = detectExportIntent(hinglishCols);
  assert.ok(hiDet !== null);
  assert.deepEqual(hiDet.columns, ['Name', 'Tenure in Delhi (yrs)']);
}

runExportIntentSuite();
console.log('✓ exportIntent.test.ts: 40/40 positive, 0/10 negative, column order verified');
