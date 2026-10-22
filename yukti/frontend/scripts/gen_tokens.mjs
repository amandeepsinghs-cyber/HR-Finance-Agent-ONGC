#!/usr/bin/env node
/**
 * Generates src/design/tokens.generated.css from src/design/tokens.json (single source of truth, U1.1).
 * Usage: npm run tokens   (runs automatically via predev/prebuild)
 * Do not edit the generated CSS by hand.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = join(root, 'src/design/tokens.json');
const out = join(root, 'src/design/tokens.generated.css');
const t = JSON.parse(readFileSync(src, 'utf8'));

const decl = (obj) =>
  Object.entries(obj)
    .map(([k, v]) => `  --${k}: ${v};`)
    .join('\n');

const paletteDecl = (p) => {
  const lines = [];
  p.categorical.forEach((c, i) => lines.push(`  --chart-cat-${i + 1}: ${c};`));
  p.sequential.forEach((c, i) => lines.push(`  --chart-seq-${i + 1}: ${c};`));
  Object.entries(p.diverging).forEach(([k, v]) => lines.push(`  --chart-div-${k}: ${v};`));
  return lines.join('\n');
};

const css = `/* AUTO-GENERATED from src/design/tokens.json by scripts/gen_tokens.mjs. DO NOT EDIT. */
:root {
${decl(t.themes.light)}
${paletteDecl(t.chartPalettes.light)}
${decl(t.typography)}
${decl(t.radius)}
${decl(t.motion)}
}

.dark {
${decl(t.themes.dark)}
${paletteDecl(t.chartPalettes.dark)}
}
`;

writeFileSync(out, css);
console.log(`[tokens] wrote ${out.replace(root + '/', '')} (${Object.keys(t.themes.light).length} theme tokens)`);
