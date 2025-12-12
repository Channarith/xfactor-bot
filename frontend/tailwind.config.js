/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(222, 47%, 11%)",
        foreground: "hsl(210, 40%, 98%)",
        card: "hsl(222, 47%, 14%)",
        "card-foreground": "hsl(210, 40%, 98%)",
        primary: "hsl(142, 76%, 36%)",
        "primary-foreground": "hsl(0, 0%, 100%)",
        secondary: "hsl(217, 33%, 17%)",
        "secondary-foreground": "hsl(210, 40%, 98%)",
        muted: "hsl(217, 33%, 17%)",
        "muted-foreground": "hsl(215, 20%, 65%)",
        accent: "hsl(217, 33%, 17%)",
        "accent-foreground": "hsl(210, 40%, 98%)",
        destructive: "hsl(0, 84%, 60%)",
        "destructive-foreground": "hsl(0, 0%, 100%)",
        border: "hsl(217, 33%, 22%)",
        input: "hsl(217, 33%, 17%)",
        ring: "hsl(142, 76%, 36%)",
        profit: "hsl(142, 76%, 36%)",
        loss: "hsl(0, 84%, 60%)",
      },
      fontFamily: {
        sans: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
}

