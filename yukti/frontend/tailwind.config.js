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
      colors: {
        canvas: {
          light: '#FFFFFF',
          dark: '#121316',
        },
        surface: {
          light: '#F8F9FA',
          hoverLight: '#F1F3F4',
          dark: '#1E2024',
          hoverDark: '#2A2D32',
        },
        border: {
          light: '#E0E3E7',
          dark: '#2D3139',
        },
        accent: {
          DEFAULT: '#3186FF',
          secondary: '#76BBFF',
          dark: '#1A73E8',
          subtle: '#E8F0FE',
          subtleDark: '#1E293B',
        },
        ongc: {
          maroon: '#8E000C',
          darkMaroon: '#6A1814',
          lightMaroon: '#FCE8E6',
          gold: '#D97706',
        },
        textPrimary: {
          light: '#1F1F1F',
          dark: '#F1F3F4',
        },
        textSecondary: {
          light: '#5F6368',
          dark: '#9AA0A6',
        },
      },
      fontFamily: {
        sans: ['Google Sans Text', 'Inter', 'Noto Sans Devanagari', 'system-ui', 'sans-serif'],
        display: ['Google Sans Flex', 'Google Sans', 'Inter', 'sans-serif'],
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
        'orb-glow': '0 0 45px rgba(49, 134, 255, 0.35)',
        'orb-glow-dark': '0 0 65px rgba(118, 187, 255, 0.45)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 18s linear infinite',
      },
    },
  },
  plugins: [],
};
