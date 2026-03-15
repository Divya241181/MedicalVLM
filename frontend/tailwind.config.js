/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        teal: {
          50:  '#d1f2eb',
          100: '#a3e4d7',
          400: '#1abc9c',
          600: '#1D9E75',
          700: '#0F6E56',
          800: '#085041',
        }
      }
    },
  },
  plugins: [],
}