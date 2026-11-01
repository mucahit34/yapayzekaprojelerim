export type RiskLevel = "critical" | "high" | "medium" | "low";

export interface ReportSection {
  id: string;
  title: string;
  kind: "cover" | "summary" | "findings" | "evidence" | "appendix" | "text";
  body: string;
}

export interface ReportTemplate {
  id: string;
  name: string;
  audience: string;
  description: string;
  sections: ReportSection[];
}

export const RISK_LABELS: Record<RiskLevel, string> = {
  critical: "Kritik",
  high: "Yüksek",
  medium: "Orta",
  low: "Düşük",
};

export const TEMPLATES: ReportTemplate[] = [
  {
    id: "executive-brief",
    name: "Yönetici Özeti",
    audience: "Karar vericiler",
    description: "Tek sayfada iş riskine odaklı özet; teknik detay yerine etki ve öncelik.",
    sections: [
      {
        id: "cover",
        title: "Kapak",
        kind: "cover",
        body: "Acme Lojistik — Dış Yüzey Değerlendirmesi\nKapsam: acme-portal.example, 3 harici IP\nTarih: 2026-10",
      },
      {
        id: "summary",
        title: "Genel Değerlendirme",
        kind: "summary",
        body: "Test kapsamında 2 kritik, 3 yüksek önem derecesinde bulgu doğrulandı. Kritik bulgular, kimlik doğrulama katmanını atlayarak müşteri verisine erişime izin veriyor. Önerilen aksiyonlar bu raporun sonunda önceliklendirildi.",
      },
      {
        id: "findings",
        title: "Öne Çıkan Bulgular",
        kind: "findings",
        body: "critical:Kimlik doğrulama atlatması (CVE eşleşmesi yok, dahili test ile doğrulandı)\nhigh:Yönetim panelinde parola sıfırlama jetonu tahmin edilebilir",
      },
    ],
  },
  {
    id: "technical-assessment",
    name: "Teknik Değerlendirme",
    audience: "Güvenlik / mühendislik ekibi",
    description: "Her bulgu için adım adım tekrar üretim, etkilenen bileşen ve düzeltme önerisi.",
    sections: [
      { id: "cover", title: "Kapak", kind: "cover", body: "Teknik Değerlendirme Raporu\nKapsam ID: PRJ-0142" },
      {
        id: "findings",
        title: "Bulgu Detayları",
        kind: "findings",
        body: "critical:SSRF — /api/v1/fetch, dahili metadata servisine erişim sağlıyor\nhigh:Oturum jetonu yenilemede yetersiz entropi\nmedium:Hata mesajlarında stack trace sızıntısı",
      },
      {
        id: "evidence",
        title: "Kanıt",
        kind: "evidence",
        body: "GET /api/v1/fetch?url=http://169.254.169.254/latest/meta-data/\nYanıt: 200 OK, iam/security-credentials/ listelendi",
      },
    ],
  },
  {
    id: "attack-surface-review",
    name: "Dış Yüzey İncelemesi",
    audience: "Varlık ve ağ sahipleri",
    description: "Keşfedilen varlıklar, açık portlar ve kapsam dışı/beklenmeyen tespitler.",
    sections: [
      { id: "cover", title: "Kapak", kind: "cover", body: "Dış Yüzey İncelemesi\nKeşif tarihi: 2026-10-28" },
      {
        id: "summary",
        title: "Varlık Envanteri",
        kind: "summary",
        body: "14 harici host tespit edildi, 2'si daha önce bilinmeyen alt alan adı. 3 host'ta kapsam dışı olarak işaretlendi.",
      },
      {
        id: "findings",
        title: "Dikkat Gerektiren Tespitler",
        kind: "findings",
        body: "medium:staging.acme.example üretim güvenlik duvarı kurallarına sahip değil\nlow:Eski TLS 1.0 desteği tespit edildi",
      },
    ],
  },
  {
    id: "incident-evidence",
    name: "Olay ve Kanıt",
    audience: "Hukuk / olay müdahale ekibi",
    description: "Zaman çizelgesi, kanıt zinciri ve doğrulama adımlarının eksiksiz kaydı.",
    sections: [
      { id: "cover", title: "Kapak", kind: "cover", body: "Olay Kaydı — INC-2026-014" },
      {
        id: "evidence",
        title: "Zaman Çizelgesi ve Kanıt Zinciri",
        kind: "evidence",
        body: "2026-10-30 14:02 — İlk erişim denemesi loglandı (kanıt: auth.log#4471)\n2026-10-30 14:09 — Doğrulama testiyle teyit edildi (validator: pentestpilot-agent)",
      },
      {
        id: "appendix",
        title: "Ekler",
        kind: "appendix",
        body: "Ham loglar, ekran görüntüleri ve hash değerleri ayrı kanıt deposunda saklanır; bu rapor yalnızca referans gösterir.",
      },
    ],
  },
];
