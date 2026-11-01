import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Mürekkep / grafit — birincil metin ve koyu yüzeyler
        ink: {
          DEFAULT: "#14181F",
          soft: "#2B313B",
        },
        // Serin kağıt — rapor tuvali (klişe krem değil)
        paper: {
          DEFAULT: "#F3F4F1",
          raised: "#FBFBFA",
        },
        // Yapı/chrome rengi — kenarlık, çizgi, pasif arayüz öğeleri
        slate: {
          line: "#3B4A5A",
          muted: "#6B7684",
        },
        // Risk sinyali — sistemdeki TEK doygun renk ailesi
        signal: {
          critical: "#B3261E",
          high: "#C9792B",
          medium: "#8A7B22",
          low: "#3F6B4C",
        },
      },
      fontFamily: {
        // Rapor sesi: resmi belge ağırlığı
        serif: ["\"Source Serif 4\"", "Georgia", "serif"],
        // Araç sesi: arayüz, etiketler, gövde metni
        sans: ["\"IBM Plex Sans\"", "system-ui", "sans-serif"],
        // Kanıt/veri sesi: IP, hash, port, kod
        mono: ["\"IBM Plex Mono\"", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
