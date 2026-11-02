# Kişisel AI Güvenlik Asistanı

Web paneli ve Telegram üzerinden erişilen, projelendirilmiş güvenlik testi
(pentest) asistanı. Tek bir koordinatör AI ve rol bazlı uzman ajanlar;
proje/kapsam/varlık/bulgu/kanıt/görev yönetimi; ortak proje hafızası;
AI destekli görsel rapor stüdyosu.

> **Önemli:** Bu proje, üzerinde çalıştığı sunucudaki mevcut servislere
> (PentestPilot AI, Sliver, Tor, Kali container, mevcut Telegram botları vb.)
> dokunmaz. Bağımsız bir uygulama olarak geliştirilir ve ayrı container'larda
> çalıştırılması planlanır. Sunucu değişiklikleri (kurulum, port, firewall,
> kullanıcı, SSH) her zaman açık onay gerektirir.

## Mimari (plan)

- **Backend:** FastAPI (Python), PostgreSQL, Redis + worker (uzun süren görevler).
- **Frontend:** React + TypeScript + Tailwind, dnd-kit tabanlı rapor editörü.
- **PDF üretimi:** Playwright/Chromium ile HTML/CSS render.
- **Telegram:** Aynı backend/koordinatör/proje hafızasını kullanan ayrı bir bot
  entegrasyonu (token yalnızca sunucu secret/env katmanında saklanır).
- **AI:** API tabanlı model çağrıları; anahtarlar yalnızca sunucu
  secret/env katmanında tutulur, koda veya loglara yazılmaz.

## Veri modeli

`Project`, `Asset`, `Finding`, `Evidence`, `Validation`, `Task`,
`Conversation`, `Report`, `ReportRevision`, `AuditEvent`.

Bulgu durumları: `suspected` (şüpheli) → `verifying` (doğrulanıyor) →
`confirmed` (doğrulandı) / `false_positive` (yanlış pozitif) /
`remediated_pending_retest` (düzeltildi, yeniden test bekliyor).

Kurallar:
- Raporlar belirli bir `project_id` ve sabitlenmiş veri snapshot'ı ile üretilir.
- Projeler arası veri birleştirme yalnızca açık kullanıcı seçimiyle yapılır.
- Teknik iddialar yapılandırılmış `Finding`/`Evidence` kayıtlarına bağlanmalı;
  serbest metin sohbet yalnızca bağlam sağlar, kanıt sayılmaz.
- Her yüksek etkili/aktif test işlemi kapsam kontrolünden geçmeli ve
  `AuditEvent` olarak kaydedilmelidir.

## Geliştirme ortamı

```bash
cp .env.example .env   # değerleri kendiniz doldurun, asla commit etmeyin
docker compose up -d --build
```

Backend `http://localhost:8000/health` üzerinden ayakta olduğunu bildirir.

## Kimlik doğrulama

Bu kişisel asistan tek kullanıcı için tasarlandı. `/health` ve
`/api/auth/*` dışındaki her uç nokta JWT bearer token gerektirir
(`app/services/auth.py`, `get_current_user`).

İlk kurulum:

```bash
curl -X POST localhost:8010/api/auth/register \
  -H 'content-type: application/json' \
  -d '{"email":"you@example.com","password":"en-az-10-karakter"}'
curl -X POST localhost:8010/api/auth/login \
  -d 'username=you@example.com&password=en-az-10-karakter'
# -> {"access_token": "...", "token_type": "bearer"}
```

`/register` yalnızca veritabanında hiç kullanıcı yokken çalışır; ikinci
bir hesap eklemek doğrudan veritabanı erişimi gerektirir — bu kasıtlı
bir kısıtlama, eksiklik değil.

Token'lar `access_token_expire_minutes` (varsayılan 12 saat) sonra
geçersiz olur. `/login` 5 başarısız denemeden sonra o e-posta için 60
saniyelik kilitlenme uygular (süreç-içi, bellekte; yeniden başlatmada
sıfırlanır). Yine de **backend genel ağa açılmamalıdır**; yalnızca
localhost/VPN/SSH tüneli üzerinden erişilmelidir — tek kullanıcılı bu
asistan için rate limiting, parola sıfırlama, çoklu oturum yönetimi gibi
üretim-seviyesi kontroller henüz yok.

## Durum

Bu iskelet, salt-okunur sunucu keşfinden sonra sıfırdan başlatılan ayrı bir
geliştirme hattıdır. Sunucudaki hiçbir mevcut servis bu depodan etkilenmez.
