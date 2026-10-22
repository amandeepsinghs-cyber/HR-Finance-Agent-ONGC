/**
 * Normalizes tabular data rows into array of objects.
 * Array-shaped rows are zipped with column names; missing column names become `col_<i>`.
 * Object rows are shallow-copied.
 * Null/undefined rows return `[]`.
 * Numeric strings (e.g. "1,234" or "₹ 3,200 Cr") are left as-is (numeric conversion stays in `toNumber`).
 */
export function normalizeRows(
  columns: string[] | undefined,
  rows: unknown[] | undefined
): Record<string, any>[] {
  if (!rows || !Array.isArray(rows)) {
    return [];
  }

  const cols = Array.isArray(columns) ? columns : [];

  return rows.map((row) => {
    if (row === null || row === undefined) {
      return {};
    }

    if (Array.isArray(row)) {
      const obj: Record<string, any> = {};
      for (let i = 0; i < row.length; i++) {
        const colName =
          cols[i] !== undefined && cols[i] !== null && String(cols[i]).trim() !== ''
            ? String(cols[i])
            : `col_${i}`;
        obj[colName] = row[i];
      }
      return obj;
    }

    if (typeof row === 'object') {
      return { ...(row as Record<string, any>) };
    }

    // Primitive fallback
    const colName = cols[0] ? String(cols[0]) : 'col_0';
    return { [colName]: row };
  });
}

/**
 * Extracts distinct column keys across all rows in order.
 * If `preferred` is given, keys in `preferred` are ordered first (if present in any row),
 * followed by remaining keys in first-seen order.
 */
export function columnsOf(
  rows: Record<string, any>[],
  preferred?: string[]
): string[] {
  if (!rows || !Array.isArray(rows)) {
    return [];
  }

  const seenKeys = new Set<string>();
  const firstSeenOrder: string[] = [];

  for (const row of rows) {
    if (row && typeof row === 'object') {
      for (const k of Object.keys(row)) {
        if (!seenKeys.has(k)) {
          seenKeys.add(k);
          firstSeenOrder.push(k);
        }
      }
    }
  }

  const result: string[] = [];
  const added = new Set<string>();

  if (preferred && Array.isArray(preferred)) {
    for (const p of preferred) {
      if (seenKeys.has(p) && !added.has(p)) {
        result.push(p);
        added.add(p);
      }
    }
  }

  for (const k of firstSeenOrder) {
    if (!added.has(k)) {
      result.push(k);
      added.add(k);
    }
  }

  return result;
}
