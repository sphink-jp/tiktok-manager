/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        sidebar: {
          bg: '#1e2130',
          hover: '#2a2f45',
          active: '#3b4263',
          text: '#a0aec0',
          activeText: '#ffffff'
        }
      }
    }
  },
  plugins: []
}
