/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        md: {
          surface: {
            DEFAULT: '#0f1118',
            1: '#14161f',
            2: '#1d202d',
            3: '#25293a',
            4: '#2d3246',
            5: '#363b52',
            variant: '#43475e',
          },
          primary: {
            DEFAULT: '#a8c7fa',
            container: '#0842a0',
            on: '#042b5c',
            'on-container': '#d3e3fd',
          },
          secondary: {
            DEFAULT: '#d0bcff',
            container: '#4f378b',
            on: '#381e72',
            'on-container': '#e8def8',
          },
          tertiary: {
            DEFAULT: '#7dd3fc',
            container: '#004d66',
            on: '#003447',
            'on-container': '#c2e7ff',
          },
          outline: {
            DEFAULT: '#8c9199',
            variant: '#43475e',
          },
          background: '#0a0c12',
          onBackground: '#e1e2ec',
        }
      },
      borderRadius: {
        '2xl': '20px',
        '3xl': '28px',
        '4xl': '36px',
      },
      boxShadow: {
        'elevation-1': '0px 1px 3px 1px rgba(0, 0, 0, 0.45), 0px 1px 2px 0px rgba(0, 0, 0, 0.3)',
        'elevation-2': '0px 2px 6px 2px rgba(0, 0, 0, 0.45), 0px 1px 2px 0px rgba(0, 0, 0, 0.3)',
        'elevation-3': '0px 4px 8px 3px rgba(0, 0, 0, 0.45), 0px 1px 3px 0px rgba(0, 0, 0, 0.3)',
        'elevation-4': '0px 6px 10px 4px rgba(0, 0, 0, 0.45), 0px 2px 3px 0px rgba(0, 0, 0, 0.3)',
        'elevation-5': '0px 8px 12px 6px rgba(0, 0, 0, 0.45), 0px 4px 4px 0px rgba(0, 0, 0, 0.3)',
        'book-ground': '0 25px 35px -10px rgba(0, 0, 0, 0.8), 0 10px 15px -5px rgba(0, 0, 0, 0.6)',
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'system-ui', 'sans-serif'],
        japanese: ['"Noto Sans JP"', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
