/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          main: '#0B0F19',
          primary: '#121212',
          secondary: '#1A1A1A',
        },
        border: {
          DEFAULT: '#1F2937',
        },
        text: {
          primary: '#FFFFFF',
          secondary: '#9CA3AF',
        },
        state: {
          safe: '#34C759',
          warning: '#FF9500',
          danger: '#FF3B30',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}

