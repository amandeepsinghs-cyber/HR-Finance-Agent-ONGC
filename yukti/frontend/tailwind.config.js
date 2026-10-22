/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      // All colours resolve to CSS variables generated from src/design/tokens.json (U1.1).
      // Legacy keys (canvas/surface/border/accent/ongc/textPrimary/textSecondary) are kept so
      // existing classes keep working; light/dark variants map to the same theme-aware variable.
      colors: {
        canvas: { DEFAULT: 'var(--canvas)', light: 'var(--canvas)', dark: 'var(--canvas)' },
        card: 'var(--card)',
        surface: {
          DEFAULT: 'var(--surface)',
          2: 'var(--surface-2)',
          light: 'var(--surface)',
          hoverLight: 'var(--surface-2)',
          dark: 'var(--surface)',
          hoverDark: 'var(--surface-2)',
        },
        border: { DEFAULT: 'var(--hairline)', light: 'var(--hairline)', dark: 'var(--hairline)' },
        hairline: 'var(--hairline)',
        ink: { DEFAULT: 'var(--ink)', 2: 'var(--ink-2)', 3: 'var(--ink-3)' },
        accent: {
          DEFAULT: 'rgb(var(--accentRgb) / <alpha-value>)',
          secondary: 'var(--accent-soft)',
          soft: 'var(--accent-soft)',
          dark: 'var(--accent-deep)',
          deep: 'var(--accent-deep)',
          subtle: 'var(--accent-pale)',
          pale: 'var(--accent-pale)',
          subtleDark: 'var(--accent-pale)',
        },
        intel: 'var(--intel)',
        positive: { DEFAULT: 'var(--positive)', fill: 'var(--positive-fill)', pale: 'var(--positive-pale)' },
        warning: { DEFAULT: 'var(--warning)', fill: 'var(--warning-fill)', pale: 'var(--warning-pale)' },
        critical: 'var(--critical)',
        ongc: {
          maroon: 'rgb(var(--maroonRgb) / <alpha-value>)',
          darkMaroon: 'var(--maroon-deep)',
          lightMaroon: 'var(--maroon-pale)',
          gold: 'var(--brand-amber)',
          saffron: 'var(--brand-saffron)',
          amber: 'var(--brand-amber)',
          petrol: 'var(--brand-petrol)',
          cyan: 'var(--brand-cyan)',
        },
        textPrimary: { light: 'var(--ink)', dark: 'var(--ink)' },
        textSecondary: { light: 'var(--ink-2)', dark: 'var(--ink-2)' },
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        display: ['var(--font-display)'],
        hindi: ['Noto Sans Devanagari', 'Inter', 'sans-serif'],
      },
      fontSize: {
        'kpi-giant': ['4.5rem', { lineHeight: '1.05', letterSpacing: '-0.03em' }],
        'kpi-large': ['3.25rem', { lineHeight: '1.1', letterSpacing: '-0.02em' }],
        'kpi-medium': ['2.25rem', { lineHeight: '1.15', letterSpacing: '-0.01em' }],
      },
      boxShadow: {
        'panel': '0 12px 40px -10px rgba(0, 0, 0, 0.12), 0 4px 16px -4px rgba(0, 0, 0, 0.08)',
        'panel-dark': '0 16px 48px -8px rgba(0, 0, 0, 0.6), 0 4px 16px rgba(0, 0, 0, 0.4)',
        'card': '0 2px 8px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.06)',
        'card-dark': '0 2px 10px rgba(0, 0, 0, 0.25)',
        'orb-glow': '0 0 45px rgb(var(--accentRgb) / 0.35)',
        'orb-glow-dark': '0 0 65px rgb(var(--accentRgb) / 0.45)',
      },
      borderRadius: {
        card: 'var(--radius-card)',
        pill: 'var(--radius-pill)',
      },
      transitionDuration: {
        fast: 'var(--dur-fast)',
        DEFAULT: 'var(--dur)',
        slow: 'var(--dur-slow)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 18s linear infinite',
      },
    },
  },
  plugins: [],
};
