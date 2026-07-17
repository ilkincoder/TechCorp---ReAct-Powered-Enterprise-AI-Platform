/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      borderRadius: {
        '2xl': '20px',
      },
      colors: {
        sidebar: 'hsl(var(--sidebar))',
        accent: {
          red: '#EF4444',
          blue: '#3B82F6',
          green: '#22C55E',
          purple: '#A855F7',
          orange: '#F59E0B',
        },
      },
      boxShadow: {
        'card': '0 1px 2px rgba(0,0,0,0.25), 0 10px 30px rgba(0,0,0,0.18)',
        'card-hover': '0 12px 35px rgba(0,0,0,0.25)',
        'card-sm': '0 1px 2px rgba(0,0,0,0.2), 0 4px 12px rgba(0,0,0,0.14)',
      },
    },
  },
  plugins: [],
}
