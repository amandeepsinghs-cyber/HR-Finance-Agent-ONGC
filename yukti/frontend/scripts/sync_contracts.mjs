#!/usr/bin/env node
// P4.1: copy single-source contract JSON from yukti/contracts into the frontend so Next.js can bundle it.
// yukti/contracts/*.json is the source of truth (shared with the Python backend); the copies under
// src/contracts/generated/ are build artefacts. `--check` exits 1 when a copy is stale (used by tests/CI).
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const contracts = join(root, '..', 'contracts');
const outDir = join(root, 'src', 'contracts', 'generated');
const FILES = ['statement_line_classes.json'];
const check = process.argv.includes('--check');

let stale = 0;
mkdirSync(outDir, { recursive: true });
for (const f of FILES) {
  const src = readFileSync(join(contracts, f), 'utf8');
  const dst = join(outDir, f);
  const cur = existsSync(dst) ? readFileSync(dst, 'utf8') : null;
  if (cur === src) continue;
  if (check) {
    console.error(`stale: src/contracts/generated/${f} differs from yukti/contracts/${f} (run: npm run contracts)`);
    stale += 1;
  } else {
    writeFileSync(dst, src);
    console.log(`synced ${f}`);
  }
}
process.exit(stale ? 1 : 0);
