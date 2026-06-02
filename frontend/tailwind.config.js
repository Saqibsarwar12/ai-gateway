/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{js,ts,jsx,tsx,mdx}', './components/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Inter Tight', 'system-ui', 'sans-serif'],
        sans: ['Inter Tight', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      colors: {
        bg: {
          0: '#0e0e0e',
          1: '#161616',
          2: '#1c1c1c',
          3: '#242424',
          4: '#2e2e2e',
        },
        fg: {
          0: '#f2f2f2',
          1: '#c4c4c4',
          2: '#8c8c8c',
          3: '#5e5e5e',
          4: '#3a3a3a',
        },
        line: {
          DEFAULT: '#2a2a2a',
          strong: '#3a3a3a',
        },
      },
    },
  },
  plugins: [],
};
