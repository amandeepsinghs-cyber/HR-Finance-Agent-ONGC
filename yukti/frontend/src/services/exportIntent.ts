/**
 * P4.7 (SPEC-10 §4.8): export intents for every format, English + Hindi/Hinglish, typed or spoken.
 * Resolution: an explicit format word wins; "the chart" → PNG, "the table/statement" → xlsx; a bare "export this"
 * → xlsx for tables/statements, PNG for charts, and the caller says which default it used.
 */

export const EXPORT_FORMATS = ['xlsx', 'csv', 'pdf', 'png', 'svg', 'docx', 'eml', 'sheets', 'docs'] as const;
export type ExportFormat = (typeof EXPORT_FORMATS)[number];

export interface ExportIntent {
  format: ExportFormat;
  /** true when no format word was given and the visual-type default was applied */
  defaulted: boolean;
  target?: 'chart' | 'table';
}

// Order matters: multi-word / more specific triggers first (google sheets before sheets, email file before email).
// G4 r1 (M2): bare "sheet(s)" is NOT an Excel word ("balance sheet", "fact sheet"); "to/in Sheets" means Google Sheets.
const LEXICON: [ExportFormat, RegExp][] = [
  ['sheets', /\b(google\s*sheets?|g\s?sheets?|(?:to|in|into|as)\s+sheets)\b|गूगल\s*शीट/i],
  ['docs', /\b(google\s*docs?|g\s?docs?)\b|गूगल\s*डॉक/i],
  ['eml', /\b(email\s*file|e-?mail\s*draft\s*file|outlook\s*draft|\.?eml)\b|ईमेल\s*फ़?फ?ाइल/i],
  ['xlsx', /\b(excel|xlsx|xls|spreadsheet|workbook)\b|एक्सेल|स्प्रेडशीट/i],
  ['csv', /\b(csv|comma[\s-]*separated)\b|सीएसवी/i],
  ['pdf', /\b(pdf|printable|print)\b|पीडीएफ|प्रिंट/i],
  ['svg', /\b(svg|vector)\b|एसवीजी/i],
  ['png', /\b(png|image|picture|photo|screenshot)\b|फ़?फ?ोटो|इमेज|चित्र|पीएनजी/i],
  ['docx', /\b(word|docx|doc|document)\b|वर्ड|डॉक्यूमेंट/i],
];

// Dedicated export verbs: may resolve a default format when a target/demonstrative is present.
const STRONG_VERB_RE = /\b(export|download)\b|डाउनलोड|एक्सपोर्ट/i;
// Weaker verbs ("save as", "send as", "में दो"): only count when an explicit format word is present.
const WEAK_VERB_RE =
  /\b(save|send\s+(me\s+)?(it\s+|this\s+)?(as|in)|give\s+(me\s+)?(it|this|that)?\s*(as|in)|get\s+(me\s+)?(it|this|that)?\s*(as|in)|as\s+an?\s+(excel|pdf|png|svg|csv|word|image)\s+file)\b|सेव|में\s+(दो|दे\s*दो)/i;
// What the export applies to: a demonstrative or a visual noun. Required for a formatless default.
const TARGET_RE =
  /\b(this|it|that|the\s+(chart|graph|plot|visual|table|statement|balance\s+sheet|p&l|income\s+statement|cash\s+flow|roster|list|rows|answer))\b|यह|इसे|इसको|(?:^|\s)इस(?:\s|$)|चार्ट|ग्राफ|टेबल|तालिका|सूची/i;
const BARE_EXPORT_RE = /^(export|download|एक्सपोर्ट|डाउनलोड)(\s+(it|this|करो|करें|कीजिए|कर\s*दो))?$/i;
// Recipient-directed sends belong to the backend email flow (P2H.4) unless an .eml file is explicitly asked for.
const RECIPIENT_RE =
  /\b(send|email|e-mail|mail|forward|share)\b.*\b(to|with)\s+(the\s+)?(director|dir|cmd|chairman|hr|finance|board|gm|cgm|ed|officer|team|manager|boss|him|her|them)\b|(डायरेक्टर|निदेशक|सीएमडी|अधिकारी|बोर्ड|टीम|एचआर|मुझे)\s+.*?(को)?\s*(भेजो|भेजें|ईमेल)|को\s+(भेजो|भेजें|ईमेल\s+करो)/i;
// Data questions / domain collocations that merely contain an export-ish word stay with the backend.
const NOT_EXPORT_RE =
  /\b(how\s+many|how\s+much|what\s+is|what\s+are|which|why|compare|trend|show\s+me\s+the\s+(numbers|data)|can\s+we\s+save|export\s+(volume|volumes|credit|duty|duties|tariff|revenue|sales|target|scheme|market|price)|save\s+(cost|costs|money|crore|cr|opex|capex|₹))\b|क्या|कैसे|कितना|कितने|कितनी|क्यों|कौन/i;

export function resolveExportIntent(text: string, visualType?: string): ExportIntent | null {
  const s = String(text || '').trim();
  if (!s || NOT_EXPORT_RE.test(s)) return null;
  const strong = STRONG_VERB_RE.test(s);
  const weak = WEAK_VERB_RE.test(s);
  if (!strong && !weak) return null;
  let explicit: ExportFormat | null = null;
  for (const [fmt, re] of LEXICON) {
    if (re.test(s)) {
      explicit = fmt;
      break;
    }
  }
  if (RECIPIENT_RE.test(s) && explicit !== 'eml') return null;
  const target: ExportIntent['target'] = /\b(chart|graph|plot|visual)\b|चार्ट|ग्राफ/i.test(s)
    ? 'chart'
    : /\b(table|statement|balance\s+sheet|p&l|income\s+statement|cash\s+flow|roster|list|rows)\b|टेबल|तालिका|सूची/i.test(s)
      ? 'table'
      : undefined;
  if (explicit) return { format: explicit, defaulted: false, target };
  // Formatless: only a dedicated export verb with a target/demonstrative (or a bare "export" / "डाउनलोड करो").
  if (!strong || !(TARGET_RE.test(s) || BARE_EXPORT_RE.test(s))) return null;
  if (target === 'chart') return { format: 'png', defaulted: true, target };
  if (target === 'table') return { format: 'xlsx', defaulted: true, target };
  const isChart = visualType === 'chart';
  return { format: isChart ? 'png' : 'xlsx', defaulted: true, target };
}

/** Normalise a backend/voice `ui_action.value` (e.g. "excel", "word", "google sheets") to an ExportFormat. */
export function normalizeExportFormat(v?: string | null): ExportFormat | 'auto' {
  const s = String(v || '').trim().toLowerCase();
  if (!s || s === 'auto' || s === 'default') return 'auto';
  if ((EXPORT_FORMATS as readonly string[]).includes(s)) return s as ExportFormat;
  for (const [fmt, re] of LEXICON) if (re.test(s)) return fmt;
  return 'auto';
}

export const EXPORT_MENU: { format: ExportFormat; label: string; chartOnly?: boolean }[] = [
  { format: 'xlsx', label: 'Excel (.xlsx)' },
  { format: 'csv', label: 'CSV' },
  { format: 'pdf', label: 'PDF' },
  { format: 'png', label: 'Image (.png)', chartOnly: true },
  { format: 'svg', label: 'Vector (.svg)', chartOnly: true },
  { format: 'docx', label: 'Word (.docx)' },
  { format: 'sheets', label: 'Google Sheets' },
  { format: 'docs', label: 'Google Docs' },
];

/** Spoken/visible confirmations (SPEC-10 §4.8) — only after the artifact exists. */
export function readyCopy(format: ExportFormat, lang: string | undefined): string {
  const hi = lang === 'hi';
  const name: Record<ExportFormat, [string, string]> = {
    xlsx: ['Excel file', 'एक्सेल फ़ाइल'],
    csv: ['CSV file', 'सीएसवी फ़ाइल'],
    pdf: ['PDF', 'पीडीएफ'],
    png: ['image', 'इमेज'],
    svg: ['SVG', 'एसवीजी'],
    docx: ['Word document', 'वर्ड डॉक्यूमेंट'],
    eml: ['email draft', 'ईमेल ड्राफ़्ट'],
    sheets: ['Excel file', 'एक्सेल फ़ाइल'],
    docs: ['Word document', 'वर्ड डॉक्यूमेंट'],
  };
  return hi ? `आपकी ${name[format][1]} तैयार है।` : `Your ${name[format][0]} is ready.`;
}

/** SPEC-10 §4.7 honest copy, used when the backend sends no toast (it normally does). */
export function honestWorkspaceCopy(format: 'sheets' | 'docs', lang: string | undefined): string {
  if (lang === 'hi') {
    return format === 'sheets'
      ? 'Google Sheets अभी जुड़ा नहीं है, इसलिए मैंने एक्सेल फ़ाइल डाउनलोड कर दी है। Sheets में File → Import से इसे खोलें।'
      : 'Google Docs अभी जुड़ा नहीं है, इसलिए मैंने वर्ड फ़ाइल डाउनलोड कर दी है। Docs में File → Open से इसे खोलें।';
  }
  return format === 'sheets'
    ? "Google Sheets isn't connected yet, so I've downloaded an Excel file. In Sheets, use File → Import to open it."
    : "Google Docs isn't connected yet, so I've downloaded a Word file. In Docs, use File → Open to open it.";
}

export function defaultedCopy(format: ExportFormat, lang: string | undefined): string {
  const fmt = format === 'png' ? 'a PNG image' : 'an Excel file';
  return lang === 'hi' ? `कोई फ़ॉर्मैट नहीं बताया गया, इसलिए ${format === 'png' ? 'PNG इमेज' : 'एक्सेल फ़ाइल'} बनाई।` : `No format given, so I made ${fmt}.`;
}
