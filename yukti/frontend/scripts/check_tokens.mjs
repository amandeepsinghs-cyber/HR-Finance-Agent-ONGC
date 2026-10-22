#!/usr/bin/env node
// Recursively scans src/**/*.{ts,tsx,css} for hard-coded colour literals (hex, and rgb/rgba/hsl/hsla
// that are not neutral black/white/grey shadows), excluding src/design/, src/fixtures/, and src/data/.
// Also verifies src/design/tokens.generated.css is in sync with tokens.json. NOTE: this check
// regenerates the file in place; if it was stale the lint fails (exit 1) and leaves the fresh file to commit.
// Fails if any are found. Use `token-lint-ignore` on a line to allow an exception;
// TEMP_ALLOW lists whole files scheduled for replacement (each with the step that removes it).
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const srcDir = join(root, 'src');

const EXCLUDED_DIRS = ['src/design', 'src/fixtures', 'src/data'];
// Files allowed temporarily because a checklist step replaces them wholesale.
const TEMP_ALLOW = {
  'src/components/VoiceOrb.tsx': 'U3.1 (infinity-ribbon orb rewrite)',
};

function getFiles(dir) {
  let results = [];
  const list = readdirSync(dir);
  for (const file of list) {
    const filePath = join(dir, file);
    const relPath = relative(root, filePath);
    if (EXCLUDED_DIRS.some((exc) => relPath === exc || relPath.startsWith(exc + '/'))) {
      continue;
    }
    const stat = statSync(filePath);
    if (stat && stat.isDirectory()) {
      results = results.concat(getFiles(filePath));
    } else if (/\.(ts|tsx|css)$/.test(file)) {
      results.push(filePath);
    }
  }
  return results;
}

function stripComments(content, isCss) {
  let out = '';
  let state = 'NORMAL';
  let i = 0;
  while (i < content.length) {
    const ch = content[i];
    const next = i + 1 < content.length ? content[i + 1] : '';

    if (state === 'NORMAL') {
      if (ch === '"' || ch === "'" || ch === '`') {
        state = ch;
        out += ch;
        i++;
      } else if (!isCss && ch === '/' && next === '/') {
        state = 'LINE_COMMENT';
        out += '  ';
        i += 2;
      } else if (ch === '/' && next === '*') {
        state = 'BLOCK_COMMENT';
        out += '  ';
        i += 2;
      } else {
        out += ch;
        i++;
      }
    } else if (state === '"' || state === "'" || state === '`') {
      if (ch === '\\') {
        out += ch + next;
        i += 2;
      } else if (ch === state) {
        out += ch;
        state = 'NORMAL';
        i++;
      } else {
        out += ch;
        i++;
      }
    } else if (state === 'LINE_COMMENT') {
      if (ch === '\n') {
        out += '\n';
        state = 'NORMAL';
      } else {
        out += ' ';
      }
      i++;
    } else if (state === 'BLOCK_COMMENT') {
      if (ch === '*' && next === '/') {
        out += '  ';
        state = 'NORMAL';
        i += 2;
      } else {
        out += ch === '\n' ? '\n' : ' ';
        i++;
      }
    }
  }
  return out;
}

const HEX_RE = /#[0-9a-fA-F]{3,8}\b/g;
const FN_RE = /\b(?:rgba?|hsla?)\(\s*([^)]*)\)/g;
// Neutral shadows/overlays are allowed: black, white, ink (31,31,31), grey (128,134,139).
const NEUTRAL = /^(0\s*,\s*0\s*,\s*0|255\s*,\s*255\s*,\s*255|31\s*,\s*31\s*,\s*31|128\s*,\s*134\s*,\s*139)\b/;
// rgb(var(--xRgb) / a) and template-built colours (`${...}`) are token-driven or dynamic.
const isAllowedFn = (args) => NEUTRAL.test(args) || args.includes('var(--') || args.includes('${');

const files = getFiles(srcDir).sort();
const matches = [];

for (const filePath of files) {
  const relPath = relative(root, filePath);
  if (TEMP_ALLOW[relPath]) continue;
  const raw = readFileSync(filePath, 'utf8');
  const rawLines = raw.split('\n');
  const stripped = stripComments(raw, filePath.endsWith('.css'));
  const strippedLines = stripped.split('\n');

  for (let l = 0; l < strippedLines.length; l++) {
    if (rawLines[l].includes('token-lint-ignore')) {
      continue;
    }
    const lineMatches = strippedLines[l].match(HEX_RE);
    if (lineMatches) {
      for (const m of lineMatches) {
        matches.push(`${relPath}:${l + 1}: ${m}`);
      }
    }
    for (const fm of strippedLines[l].matchAll(FN_RE)) {
      if (!isAllowedFn(fm[1])) matches.push(`${relPath}:${l + 1}: ${fm[0]}`);
    }
  }
}

// Generated CSS must match tokens.json (regenerate into memory and compare).
const genPath = join(root, 'src/design/tokens.generated.css');
const before = readFileSync(genPath, 'utf8');
execFileSync(process.execPath, [join(root, 'scripts/gen_tokens.mjs')], { stdio: 'ignore' });
const after = readFileSync(genPath, 'utf8');
if (before !== after) {
  matches.push('src/design/tokens.generated.css: was stale vs tokens.json (now regenerated; re-run and commit)');
}

if (matches.length > 0) {
  for (const m of matches) {
    console.error(m);
  }
  process.exit(1);
}

const allowed = Object.entries(TEMP_ALLOW).map(([f, why]) => `${f} → ${why}`).join('; ');
console.log(`[lint:tokens] OK (${files.length} files scanned; generated CSS in sync; temporarily allowed: ${allowed || 'none'})`);
process.exit(0);
