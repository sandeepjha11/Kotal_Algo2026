/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          DEFAULT: '#000000',
          panel: '#121212',
          card: '#1e1e1e',
          border: '#2a2a2a',
        },
        primary: {
          DEFAULT: '#eab308', // yellow-500
          hover: '#ca8a04', // yellow-600
        }
      }
    },
  },
  plugins: [],
}
