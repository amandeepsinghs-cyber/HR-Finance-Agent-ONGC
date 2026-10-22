#!/usr/bin/env node
// Automated contrast check for design tokens (WCAG 2.1 AA)
// Evaluates foreground/background token pairs across light and dark themes.
// Alpha-composites rgba colors over canvas/background before computing luminance.

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..');
const tokensPath = join(root, 'src', 'design', 'tokens.json');

export function parseColor(str) {
  str = str.trim();
  if (str.startsWith('#')) {
    let hex = str.slice(1);
    if (hex.length === 3) {
      hex = hex.split('').map((c) => c + c).join('');
    }
    const num = parseInt(hex, 16);
    return {
      r: (num >> 16) & 255,
      g: (num >> 8) & 255,
      b: num & 255,
      a: 1,
      raw: str,
    };
  }
  const match = str.match(/^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)$/i);
  if (match) {
    return {
      r: parseFloat(match[1]),
      g: parseFloat(match[2]),
      b: parseFloat(match[3]),
      a: match[4] !== undefined ? parseFloat(match[4]) : 1,
      raw: str,
    };
  }
  throw new Error(`Unsupported color format: ${str}`);
}

export function composite(overlay, base) {
  const a = overlay.a;
  return {
    r: overlay.r * a + base.r * (1 - a),
    g: overlay.g * a + base.g * (1 - a),
    b: overlay.b * a + base.b * (1 - a),
    a: 1,
  };
}

export function linearize(c255) {
  const c = c255 / 255;
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

export function luminance(color) {
  return 0.2126 * linearize(color.r) + 0.7152 * linearize(color.g) + 0.0722 * linearize(color.b);
}

export function contrastRatio(c1, c2) {
  const l1 = luminance(c1);
  const l2 = luminance(c2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

function resolveBg(bgStr, canvas) {
  const c = parseColor(bgStr);
  return c.a < 1 ? composite(c, canvas) : c;
}

function resolveFg(fgStr, bgResolved) {
  const c = parseColor(fgStr);
  return c.a < 1 ? composite(c, bgResolved) : c;
}

// Translucent backgrounds (e.g. *-pale chips) can sit on the canvas OR on a card, so they are
// composited over every surface in BASES_BY_THEME and the WORST ratio is reported (G4 U1.4 follow-up).
const BASES_BY_THEME = {};

function evaluatePair(theme, cls, fgName, fgRaw, bgName, bgRaw, min, canvasRaw) {
  const bases = BASES_BY_THEME[theme] && parseColor(bgRaw).a < 1 ? BASES_BY_THEME[theme] : [canvasRaw];
  let ratio = Infinity;
  for (const baseRaw of bases) {
    const bgResolved = resolveBg(bgRaw, parseColor(baseRaw));
    const fgResolved = resolveFg(fgRaw, bgResolved);
    ratio = Math.min(ratio, contrastRatio(fgResolved, bgResolved));
  }
  const isInfo = min === 'INFO';
  const pass = isInfo || ratio >= min;
  const status = isInfo ? 'INFO' : (pass ? 'PASS' : 'FAIL');
  const minStr = isInfo ? 'INFO' : min.toFixed(1);
  return {
    theme,
    cls,
    fgName,
    fgRaw,
    bgName,
    bgRaw,
    ratio,
    ratioStr: ratio.toFixed(2),
    minStr,
    status,
    line: `${theme} | ${cls} | ${fgName} ${fgRaw} | ${bgName} ${bgRaw} | ${ratio.toFixed(2)} | ${minStr} | ${status}`,
  };
}

function runSelftest() {
  console.log('theme | class | fg | bg | ratio | min | status');
  const results = [
    evaluatePair(
      'selftest',
      'Alpha compositing check',
      'positive',
      '#81C995',
      'positive-pale',
      'rgba(129, 201, 149, 0.14)',
      4.5,
      '#121317'
    ),
    evaluatePair(
      'selftest',
      'Fake failure test',
      'test-fg',
      '#777777',
      'test-bg',
      '#888888',
      4.5,
      '#FFFFFF'
    ),
  ];
  for (const r of results) {
    console.log(r.line);
  }
  const fails = results.filter((r) => r.status === 'FAIL');
  // Self-test PASSES (exit 0) only when exactly the planted failure is detected, so CI can run it.
  if (fails.length === 1 && fails[0].fgName === 'test-fg') {
    console.log('[lint:contrast] Selftest OK (planted failure detected; compositing check passed)');
    process.exit(0);
  }
  console.error(`[lint:contrast] Selftest FAILED (expected exactly 1 planted failure, got ${fails.length})`);
  process.exit(1);
}

function main() {
  if (process.argv.includes('--selftest')) {
    runSelftest();
    return;
  }

  const rawTokens = readFileSync(tokensPath, 'utf8');
  const tokens = JSON.parse(rawTokens);

  const themes = ['light', 'dark'];
  const allResults = [];

  for (const theme of themes) {
    console.log(`\n=== Theme: ${theme} ===`);
    console.log('theme | class | fg | bg | ratio | min | status');

    const t = tokens.themes[theme];
    const canvasRaw = t.canvas;
    BASES_BY_THEME[theme] = [t.canvas, t.card, t.surface, t["surface-2"]];

    const pairs = [
      // Body text
      { cls: 'Body text', fg: 'ink', bg: 'canvas', min: 4.5 },
      { cls: 'Body text', fg: 'ink', bg: 'card', min: 4.5 },
      { cls: 'Body text', fg: 'ink', bg: 'surface', min: 4.5 },
      { cls: 'Body text', fg: 'ink', bg: 'surface-2', min: 4.5 },
      // Secondary text
      { cls: 'Secondary text', fg: 'ink-2', bg: 'canvas', min: 4.5 },
      { cls: 'Secondary text', fg: 'ink-2', bg: 'card', min: 4.5 },
      { cls: 'Secondary text', fg: 'ink-2', bg: 'surface', min: 4.5 },
      // Tertiary/caption text
      { cls: 'Tertiary/caption text', fg: 'ink-3', bg: 'card', min: 3.0 },
      // Accent text/links
      {
        cls: 'Accent text/links',
        fg: theme === 'light' ? 'accent-deep' : 'accent-soft',
        bg: 'card',
        min: 4.5,
      },
      // Status text
      { cls: 'Status text', fg: 'positive', bg: 'positive-pale', min: 4.5 },
      { cls: 'Status text', fg: 'warning', bg: 'warning-pale', min: 4.5 },
      { cls: 'Status text', fg: 'maroon', bg: 'maroon-pale', min: 4.5 },
      // On-fill text
      { cls: 'On-fill text', fg: 'on-accent', bg: 'accent', min: 3.0 },
      { cls: 'On-fill text', fg: 'on-accent', bg: 'maroon', min: 3.0 },
      // Small UI text on selected/tonal fills (primitives: Chip selected, Badge tones)
      ...(theme === 'light'
        ? [{ cls: 'Selected chip text', fg: 'on-accent', bg: 'accent-deep', min: 4.5 }]
        : [{ cls: 'Selected chip text', fg: 'accent-soft', bg: 'accent-pale', min: 4.5 }]),
      { cls: 'Badge text', fg: theme === 'light' ? 'accent-deep' : 'accent-soft', bg: 'accent-pale', min: 4.5 },
      { cls: 'Badge text', fg: 'ink-2', bg: 'surface-2', min: 4.5 },
      // Chart text
      { cls: 'Chart text', fg: 'chart-text', bg: 'card', min: 4.5 },
      { cls: 'Chart text', fg: 'chart-sub', bg: 'card', min: 4.5 },
    ];

    for (const p of pairs) {
      const res = evaluatePair(
        theme,
        p.cls,
        p.fg,
        t[p.fg],
        p.bg,
        t[p.bg],
        p.min,
        canvasRaw
      );
      allResults.push(res);
      console.log(res.line);
    }

    // Data marks (non-text)
    const cat = tokens.chartPalettes[theme]?.categorical || [];
    cat.forEach((color, i) => {
      const res = evaluatePair(
        theme,
        'Data marks (non-text)',
        `categorical[${i}]`,
        color,
        'card',
        t.card,
        3.0,
        canvasRaw
      );
      allResults.push(res);
      console.log(res.line);
    });

    // UI boundaries
    const hairlineRes = evaluatePair(
      theme,
      'UI boundaries',
      'hairline',
      t.hairline,
      'card',
      t.card,
      'INFO',
      canvasRaw
    );
    allResults.push(hairlineRes);
    console.log(hairlineRes.line);
  }

  const failures = allResults.filter((r) => r.status === 'FAIL');
  console.log('');
  if (failures.length > 0) {
    console.error(`[lint:contrast] FAILED (${failures.length} pair(s) failed contrast check)`);
    process.exit(1);
  } else {
    console.log(`[lint:contrast] OK (${allResults.length} pairs checked)`);
    process.exit(0);
  }
}

main();
