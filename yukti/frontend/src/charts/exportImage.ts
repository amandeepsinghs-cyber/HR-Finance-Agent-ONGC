/**
 * P4.7 (SPEC-10 §4.4, §4.9): client-side chart export.
 *  - PNG: the live chart(s) at ≥ 1600 px width, composited under a title + subtitle (unit / as-of) and above a
 *    source footnote, so the image is self-describing.
 *  - SVG: the same chart(s) re-rendered by a hidden `renderer:'svg'` instance, wrapped with the same texts.
 *  - File names follow the SPEC-10 §4.9 rule (mirrors backend export_audit.build_export_filename).
 * Tables/statements are not imaged on the client (no html-to-image dependency); they export as xlsx/csv/pdf.
 */
import * as echarts from 'echarts';
import type { ECharts } from 'echarts';

export const MIN_EXPORT_WIDTH = 1600;
export const NAMING_REGEX = /^yukti_[a-z0-9_-]+_\d{8}-\d{4}(_aggregate)?\.(xlsx|csv|pdf|png|svg|docx|eml)$/;

export interface ImageMeta {
  title: string;
  subtitle?: string; // unit · as-of
  source?: string; // "Source: ONGC Annual Report FY2023-24, p. 212"
  background: string;
  ink: string;
  ink2: string;
  fontFamily?: string;
}

// ---------------------------------------------------------------------------------------------------------------
// File naming (SPEC-10 §4.9)
// ---------------------------------------------------------------------------------------------------------------

// Mirrors backend export_audit._HINDI_TRANSLIT (longest phrases first) so client and server names agree.
const HI_TRANSLIT: [RegExp, string][] = [
  [/ओएनजीसी/g, 'ongc'],
  [/राजस्व/g, 'rajasva'],
  [/शुद्ध\s*लाभ/g, 'shuddh_labh'],
  [/लाभ/g, 'labh'],
  [/वित्तीय/g, 'vittiya'],
  [/सारांश/g, 'saransh'],
  [/दिल्ली/g, 'delhi'],
  [/मुम्बई/g, 'mumbai'],
  [/मुंबई/g, 'mumbai'],
  [/अधिकारी/g, 'adhikari'],
  [/कर्मचारी/g, 'karmachari'],
  [/वेतन/g, 'vetan'],
  [/स्थानांतरण/g, 'transfer'],
  [/सूची/g, 'roster'],
  [/रिपोर्ट/g, 'report'],
];

/** Lowercase ASCII snake_case token `[a-z0-9_-]`; Hindi words transliterated when known, else dropped. */
export function slugToken(text: string, fallback = 'report', maxLen = 28): string {
  let raw = String(text || '').trim();
  for (const [re, en] of HI_TRANSLIT) raw = raw.replace(re, ` ${en} `);
  raw = raw
    .toLowerCase()
    .replace(/>=/g, 'ge')
    .replace(/<=/g, 'le')
    .replace(/>/g, 'gt')
    .replace(/</g, 'lt')
    .replace(/&/g, 'and')
    .replace(/[–—]/g, '-');
  // eslint-disable-next-line no-control-regex
  const ascii = raw.replace(/[^\x00-\x7f]/g, '');
  const slug = ascii.replace(/[^a-z0-9-]+/g, '_').replace(/_+/g, '_').replace(/^[_-]+|[_-]+$/g, '');
  const cut = slug.slice(0, maxLen).replace(/^[_-]+|[_-]+$/g, '');
  return cut || fallback;
}

function stamp(d: Date): string {
  // UTC, matching the backend (time.gmtime) so client and server names sort together
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getUTCFullYear()}${p(d.getUTCMonth() + 1)}${p(d.getUTCDate())}-${p(d.getUTCHours())}${p(d.getUTCMinutes())}`;
}

export interface FilenameParts {
  subject: string;
  scope?: string;
  period?: string;
  persona?: string;
  ext: 'png' | 'svg' | 'xlsx' | 'csv' | 'pdf' | 'docx' | 'eml';
  aggregate?: boolean;
  now?: Date;
}

export function exportFilename(p: FilenameParts): string {
  const persona = slugToken(p.persona || 'cmd', 'cmd', 12).replace(/-/g, '_');
  const scope = slugToken(p.scope || 'corp', 'corp', 14);
  const period = slugToken(p.period || 'current', 'current', 16);
  const suffix = p.aggregate ? '_aggregate' : '';
  const tail = `_${scope}_${period}_${persona}_${stamp(p.now || new Date())}${suffix}`;
  const maxSubj = Math.max(4, 80 - 'yukti_'.length - tail.length);
  const subject = slugToken(p.subject, 'report', 28).slice(0, maxSubj).replace(/[_-]+$/g, '') || 'report';
  let stem = `yukti_${subject}${tail}`;
  if (stem.length > 80) stem = `yukti_${subject.slice(0, 12)}_${persona}_${stamp(p.now || new Date())}${suffix}`.slice(0, 80);
  const name = `${stem}.${p.ext}`;
  return NAMING_REGEX.test(name) ? name : `yukti_report_${persona}_${stamp(p.now || new Date())}${suffix}.${p.ext}`;
}

/** Subject/scope/period from an answer contract (same heuristics as backend filename_from_contract). */
export function filenamePartsFromContract(c: any, aggregate = false): Pick<FilenameParts, 'subject' | 'scope' | 'period'> {
  const vis = c?.visual || {};
  const qs = c?.query_spec || {};
  const title = String(vis.title || c?.definition_id || qs.subject || 'report');
  const wc = qs?.filters?.wc_id;
  const scope = wc ? String(wc).toLowerCase() : /delhi/i.test(title) ? 'wc-del' : 'corp';
  const asOf = qs.as_of || (c?.sources || []).find((s: any) => s?.as_of)?.as_of;
  let period = 'current';
  if (asOf && /^\d{4}-\d{2}-\d{2}$/.test(String(asOf))) period = `asof-${String(asOf).replace(/-/g, '')}`;
  else {
    const fys = title.toLowerCase().match(/fy\s?\d{2}/g)?.map((x) => x.replace(/\s/g, '')) || [];
    if (fys.length >= 2) period = `${fys[0]}-${fys[fys.length - 1]}`;
    else if (fys.length === 1) period = fys[0];
  }
  let subject = slugToken(title, 'report', 24);
  if (aggregate && subject.endsWith('_roster')) subject = `${subject.slice(0, -7)}_bylevel`; // backend parity
  return { subject, scope, period };
}

// ---------------------------------------------------------------------------------------------------------------
// Image composition
// ---------------------------------------------------------------------------------------------------------------

const HEADER_PX = 76; // CSS px at scale 1 (title 22 + subtitle 14 + padding)
const FOOTER_PX = 34;
const PAD_PX = 24;

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('chart image failed to load'));
    img.src = src;
  });
}

/** PNG data URL of the chart(s), stacked vertically, ≥ MIN_EXPORT_WIDTH px wide, with title/subtitle/source drawn in. */
export async function chartsToPng(charts: ECharts[], meta: ImageMeta): Promise<{ dataUrl: string; width: number; height: number }> {
  if (!charts.length) throw new Error('No chart on screen to export');
  const cssW = Math.max(...charts.map((c) => c.getWidth() || 800));
  const ratio = Math.max(2, Math.ceil(MIN_EXPORT_WIDTH / (cssW + PAD_PX * 2)));
  const images = await Promise.all(
    charts.map((c) =>
      loadImage(c.getDataURL({ type: 'png', pixelRatio: ratio, backgroundColor: meta.background, excludeComponents: ['toolbox'] })),
    ),
  );
  const W = Math.round((cssW + PAD_PX * 2) * ratio);
  const bodyH = images.reduce((s, im) => s + im.height, 0);
  const H = Math.round((HEADER_PX + FOOTER_PX) * ratio) + bodyH;
  const canvas = document.createElement('canvas');
  canvas.width = W;
  canvas.height = H;
  const g = canvas.getContext('2d');
  if (!g) throw new Error('Canvas unavailable');
  const font = meta.fontFamily || 'Inter, "Noto Sans", "Noto Sans Devanagari", system-ui, sans-serif';
  g.fillStyle = meta.background;
  g.fillRect(0, 0, W, H);
  g.textBaseline = 'top';
  g.fillStyle = meta.ink;
  g.font = `600 ${22 * ratio}px ${font}`;
  g.fillText(meta.title, PAD_PX * ratio, 16 * ratio, W - PAD_PX * 2 * ratio);
  if (meta.subtitle) {
    g.fillStyle = meta.ink2;
    g.font = `400 ${14 * ratio}px ${font}`;
    g.fillText(meta.subtitle, PAD_PX * ratio, 46 * ratio, W - PAD_PX * 2 * ratio);
  }
  let y = Math.round(HEADER_PX * ratio);
  for (const im of images) {
    g.drawImage(im, PAD_PX * ratio, y);
    y += im.height;
  }
  if (meta.source) {
    g.fillStyle = meta.ink2;
    g.font = `400 ${12 * ratio}px ${font}`;
    g.fillText(meta.source, PAD_PX * ratio, y + 10 * ratio, W - PAD_PX * 2 * ratio);
  }
  return { dataUrl: canvas.toDataURL('image/png'), width: W, height: H };
}

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/** SVG markup of the chart(s): each re-rendered by a hidden SVG-renderer instance, then wrapped with the texts. */
export function chartsToSvg(charts: ECharts[], meta: ImageMeta): string {
  if (!charts.length) throw new Error('No chart on screen to export');
  const parts: { svg: string; w: number; h: number }[] = [];
  for (const c of charts) {
    const w = c.getWidth() || 800;
    const h = c.getHeight() || 450;
    const host = document.createElement('div');
    host.style.cssText = `position:fixed;left:-10000px;top:0;width:${w}px;height:${h}px;`;
    document.body.appendChild(host);
    const svgInst = echarts.init(host, undefined, { renderer: 'svg', width: w, height: h });
    try {
      const opt = c.getOption() as any;
      svgInst.setOption({ ...opt, animation: false, backgroundColor: meta.background }, { notMerge: true });
      parts.push({ svg: svgInst.renderToSVGString(), w, h });
    } finally {
      svgInst.dispose();
      host.remove();
    }
  }
  const W = Math.max(...parts.map((p) => p.w)) + PAD_PX * 2;
  const bodyH = parts.reduce((s, p) => s + p.h, 0);
  const H = HEADER_PX + bodyH + FOOTER_PX;
  const font = esc(meta.fontFamily || 'Inter, Noto Sans, Noto Sans Devanagari, sans-serif');
  let y = HEADER_PX;
  const bodies = parts
    .map((p) => {
      const inner = p.svg.replace(/^<\?xml[^>]*>\s*/, '').replace(/^<svg\b/, `<svg x="${PAD_PX}" y="${y}"`);
      y += p.h;
      return inner;
    })
    .join('\n');
  return [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" font-family="${font}">`,
    `<rect width="100%" height="100%" fill="${esc(meta.background)}"/>`,
    `<text x="${PAD_PX}" y="38" font-size="22" font-weight="600" fill="${esc(meta.ink)}">${esc(meta.title)}</text>`,
    meta.subtitle ? `<text x="${PAD_PX}" y="62" font-size="14" fill="${esc(meta.ink2)}">${esc(meta.subtitle)}</text>` : '',
    bodies,
    meta.source ? `<text x="${PAD_PX}" y="${HEADER_PX + bodyH + 22}" font-size="12" fill="${esc(meta.ink2)}">${esc(meta.source)}</text>` : '',
    '</svg>',
  ].join('\n');
}

// ---------------------------------------------------------------------------------------------------------------
// Delivery + audit
// ---------------------------------------------------------------------------------------------------------------

export function triggerDownload(href: string, filename: string): void {
  const a = document.createElement('a');
  a.href = href;
  a.download = filename;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  a.remove();
}

export function downloadText(text: string, filename: string, mime: string): void {
  const url = URL.createObjectURL(new Blob([text], { type: mime }));
  triggerDownload(url, filename);
  window.setTimeout(() => URL.revokeObjectURL(url), 4000);
}

/** SPEC-10 §4.4: client-side downloads are still audit-logged server-side. Never blocks the download. */
export async function postExportAudit(body: {
  turn_id: string;
  session_id?: string;
  format: 'png' | 'svg';
  filename: string;
  rows?: number;
  columns?: string[];
  masked?: boolean;
}): Promise<boolean> {
  try {
    const res = await fetch('/api/export/audit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(body),
    });
    return res.ok;
  } catch {
    return false;
  }
}
