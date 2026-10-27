import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        serif: ['Source Serif 4', 'Georgia', 'serif'],
      },
      colors: {
        sidebar: { bg: '#102A43', text: '#C4D3E2', active: '#1E8E73' },
        page: { bg: '#F4F6F8' },
        card: { bg: '#FFFFFF', border: '#E7ECF1' },
        heading: '#0B2A3B',
        body: '#1F2937',
        muted: '#667585',
        primary: '#102A43',
        success: { DEFAULT: '#1E8E73', text: '#0F5C4D' },
        rb: { bg: '#EAF0FC', text: '#2A4F9C' },
        pgrc: { bg: '#E8F6F1', text: '#0F5C4D' },
        alert: { bg: '#FFF4EC', border: '#F0D9A8', text: '#8A4A17', badge: '#E2572B' },
      },
      borderRadius: {
        card: '12px',
      },
    },
  },
  plugins: [],
} satisfies Config
