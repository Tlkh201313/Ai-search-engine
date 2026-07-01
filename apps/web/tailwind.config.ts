import type { Config } from 'tailwindcss';

const withOpacity = (name: string) => `rgb(var(${name}) / <alpha-value>)`;

const config: Config = {
  darkMode: 'class',
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: withOpacity('--paper'),
        surface: withOpacity('--surface'),
        raised: withOpacity('--raised'),
        ink: withOpacity('--ink'),
        muted: withOpacity('--muted'),
        faint: withOpacity('--faint'),
        line: withOpacity('--line'),
        accent: withOpacity('--accent'),
        'accent-soft': withOpacity('--accent-soft'),
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        serif: ['var(--font-serif)'],
        mono: ['var(--font-mono)'],
      },
      maxWidth: {
        prose: '46rem',
        content: '52rem',
      },
      boxShadow: {
        subtle: '0 1px 2px rgb(0 0 0 / 0.04), 0 1px 3px rgb(0 0 0 / 0.06)',
        card: '0 1px 3px rgb(0 0 0 / 0.05), 0 6px 24px -12px rgb(0 0 0 / 0.12)',
        float: '0 8px 40px -12px rgb(0 0 0 / 0.18)',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in-fast': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
        'pulse-dot': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.35' },
        },
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.4s ease-out both',
        'fade-in-fast': 'fade-in-fast 0.25s ease-out both',
        shimmer: 'shimmer 1.6s infinite',
        'pulse-dot': 'pulse-dot 1.4s ease-in-out infinite',
        blink: 'blink 1.1s step-end infinite',
      },
    },
  },
  plugins: [],
};

export default config;
