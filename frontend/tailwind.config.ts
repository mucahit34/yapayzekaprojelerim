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
          // #6B7684 kağıt zeminde (#F3F4F1) 4.18:1 veriyordu — WCAG AA'nin
          // 4.5:1 eşiğinin altında. #5E6975, aynı aileyi koruyarak 5.07:1'e
          // çıkarır.
          muted: "#5E6975",
        },
        // Risk sinyali — sistemdeki TEK doygun renk ailesi.
        // CVD (renk körlüğü) güvenliği için scripts/validate_palette.js ile
        // doğrulandı; kritik/yüksek çifti klasik kırmızı-turuncu yerine
        // kırmızı-mavi kullanır çünkü kırmızı-turuncu-sarı-yeşil sırası
        // protanopi/döteranopi için ayırt edilemez çıkıyor. Bu yüzden anlam
        // HİÇBİR YERDE yalnızca renge değil, her zaman metin etiketine
        // bağlanmalıdır (bkz. RISK_LABELS kullanımları).
        signal: {
          critical: "#B3261E",
          high: "#2457A8",
          medium: "#B38600",
          low: "#1F7A52",
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
