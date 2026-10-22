import assert from 'node:assert/strict';
import { normalizeRows, columnsOf } from '../src/charts/normalize';

console.log('Testing normalizeRows & columnsOf...');

// Case 1: Array rows zipped with columns
{
  const columns = ['name', 'age'];
  const rows = [
    ['Alice', 30],
    ['Bob', 25],
  ];
  const out = normalizeRows(columns, rows);
  assert.deepEqual(out, [
    { name: 'Alice', age: 30 },
    { name: 'Bob', age: 25 },
  ]);
}

// Case 2: Object rows passed through (shallow-copied)
{
  const orig = { grade: 'E4', headcount: 410 };
  const rows = [orig];
  const out = normalizeRows(['grade', 'headcount'], rows);
  assert.deepEqual(out, [{ grade: 'E4', headcount: 410 }]);
  assert.notEqual(out[0], orig, 'Must be a shallow copy, not the exact same object reference');
}

// Case 3: Mixed array and object rows
{
  const rows = [
    ['DEL', 2450],
    { wc_id: 'MUM', headcount: 6820 },
  ];
  const out = normalizeRows(['wc_id', 'headcount'], rows);
  assert.deepEqual(out, [
    { wc_id: 'DEL', headcount: 2450 },
    { wc_id: 'MUM', headcount: 6820 },
  ]);
}

// Case 4: Missing column names -> col_<i>
{
  const rows = [
    [10, 20, 30],
  ];
  const out1 = normalizeRows(['first'], rows);
  assert.deepEqual(out1, [{ first: 10, col_1: 20, col_2: 30 }]);

  const out2 = normalizeRows(undefined, rows);
  assert.deepEqual(out2, [{ col_0: 10, col_1: 20, col_2: 30 }]);
}

// Case 5: Empty, null, undefined rows -> []
{
  assert.deepEqual(normalizeRows(['a'], undefined), []);
  assert.deepEqual(normalizeRows(['a'], null as any), []);
  assert.deepEqual(normalizeRows(['a'], []), []);
}

// Case 6: Numeric strings like "1,234" or "₹ 3,200 Cr" left as-is
{
  const rows = [
    ['Delhi', '1,234', '₹ 3,200 Cr'],
  ];
  const out = normalizeRows(['city', 'count', 'revenue'], rows);
  assert.deepEqual(out, [
    { city: 'Delhi', count: '1,234', revenue: '₹ 3,200 Cr' },
  ]);
}

// Case 7: columnsOf preferred order first, then first-seen keys
{
  const rows = [
    { c: 3, a: 1, b: 2 },
    { d: 4, a: 10 },
  ];
  const cols = columnsOf(rows, ['a', 'b']);
  assert.deepEqual(cols, ['a', 'b', 'c', 'd']);
}

// Case 8: columnsOf without preferred returns first-seen order
{
  const rows = [
    { z: 1, x: 2 },
    { y: 3, x: 4 },
  ];
  const cols = columnsOf(rows);
  assert.deepEqual(cols, ['z', 'x', 'y']);
}

console.log('✓ All normalizeRows and columnsOf tests passed successfully (8 cases).');
