/**
 * Explicit chart-kind precedence (SPEC-09 §4.4, BUG-22). TypeScript twin of the backend `chart_rules` precedence,
 * tested against the shared fixture `yukti/contracts/fixtures/kind_precedence_30.json`.
 *
 * Order: (1) an explicit kind word in the utterance (EN + HI) always wins; (2) bridge wording ("bridge",
 * "walk me from …", "from revenue to profit/PAT") → waterfall; (3) trend wording over years → line.
 * Returns null when the utterance names no kind (the data-shape default then applies).
 */
export type PrecedenceKind =
  | 'table' | 'line' | 'bar' | 'hbar' | 'combo' | 'stacked_bar' | 'stacked_100' | 'grouped_bar' | 'pie' | 'donut' | 'area'
  | 'scatter' | 'treemap' | 'heatmap' | 'histogram' | 'box' | 'funnel' | 'gauge' | 'bullet' | 'map' | 'waterfall'
  | 'tornado' | 'sankey' | 'sunburst' | 'bubble';

// Longest / most specific phrases first, so "horizontal bar" never reads as "bar" and "stacked bar" never as "bar".
const LEXICON: [RegExp, PrecedenceKind][] = [
  [/\b100\s*%\s*stacked\b/i, 'stacked_100'],
  [/\bstacked\s+(bar|column)s?\b|\bstacked\b/i, 'stacked_bar'],
  [/\b(grouped|clustered)\s+(bar|column)s?\b/i, 'grouped_bar'],
  [/\bhorizontal\s+bars?\b|\bh-?bar\b/i, 'hbar'],
  [/\bcombo\b|\bdual[-\s]axis\b/i, 'combo'],
  [/\bbox\s*(plot|chart)?\b|\bbox-?and-?whisker\b/i, 'box'],
  [/\bbullet\s+(chart|graph)\b/i, 'bullet'],
  [/\bgauge\b/i, 'gauge'],
  [/\bheat\s*map\b/i, 'heatmap'],
  [/\bhistogram\b/i, 'histogram'],
  [/\bscatter(\s*plot)?\b/i, 'scatter'],
  [/\bbubble\b/i, 'bubble'],
  [/\btree\s*map\b/i, 'treemap'],
  [/\bsunburst\b/i, 'sunburst'],
  [/\bsankey\b/i, 'sankey'],
  [/\btornado\b/i, 'tornado'],
  [/\bfunnel\b/i, 'funnel'],
  [/\bdonut\b|\bdoughnut\b/i, 'donut'],
  [/\bpie\b|पाई/i, 'pie'],
  [/\barea\s+(chart|graph|plot)\b/i, 'area'],
  [/\bwaterfall\b|वॉटरफॉल|वाटरफॉल/i, 'waterfall'],
  [/\bline\s+(chart|graph|plot)\b|\bas\s+a\s+line\b|रेखा/i, 'line'],
  [/\b(bar|column)\s*(chart|graph|plot)?s?\b|कॉलम|बार\s*चार्ट/i, 'bar'],
  [/\btabular\b|\b(in|as)\s+a\s+table\b|\btable\b|सारणी|टेबल|तालिका/i, 'table'],
  [/\b(india|state)\s+map\b|\bon\s+an?\s+(india\s+)?map\b|\bmap\b/i, 'map'],
];

const BRIDGE_RE = /\bbridge\b|\bwalk\s+(me\s+)?from\b|\bfrom\s+revenue\s+to\s+(net\s+)?(profit|pat)\b/i;
const TREND_RE = /\btrend\b|\bover\s+(the\s+)?(last\s+|past\s+)?\d+\s+years?\b/i;

export function resolveKind(utterance: string): PrecedenceKind | null {
  const s = (utterance || '').trim();
  if (!s) return null;
  for (const [re, kind] of LEXICON) if (re.test(s)) return kind;
  if (BRIDGE_RE.test(s)) return 'waterfall';
  if (TREND_RE.test(s)) return 'line';
  return null;
}
