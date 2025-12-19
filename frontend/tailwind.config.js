/** @type {import('tailwindcss').Config} */
const config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        sidebar: "#020617", // Very dark blue/black
        card: "#1e293b",    // Slate 800
        muted: "#64748b",   // Slate 500
        accent: "#38bdf8",  // Sky 400
      },
    },
  },
  plugins: [],
};
export default config;
