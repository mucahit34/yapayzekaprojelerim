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

## PDF dışa aktarma

`GET /api/reports/{id}/pdf`, kayıtlı `data_snapshot`'ı Playwright/Chromium
ile gerçek bir PDF'e render eder. Bu geliştirme sandbox'ında Chromium
`/opt/pw-browsers/chromium`'da hazır geliyor; gerçek sunucuda
`playwright install chromium` çalıştırılmalı veya `PLAYWRIGHT_CHROMIUM_PATH`
ortam değişkeniyle kurulu bir Chromium'un yolu verilmelidir. Chromium
bulunamazsa uç nokta sahte bir "başarı" döndürmez — 503 ile açık bir hata
mesajı verir.

## Telegram botu

Web paneliyle aynı backend/veri modelini paylaşır (`app/telegram/service.py`
doğrudan aynı servis katmanını ve veritabanını kullanır — ayrı bir mantık
tekrar yazılmaz). FastAPI sürecinden bağımsız, ayrı bir süreç olarak
polling modunda çalışır:

```bash
cd backend
# .env içinde TELEGRAM_BOT_TOKEN ve TELEGRAM_ALLOWED_USER_IDS dolu olmalı
python -m app.telegram.bot
```

**Güvenlik modeli — JWT değil, whitelist:** Telegram tarafında web
paneliyle aynı kimlik doğrulama akışı yok. Tek koruma,
`TELEGRAM_ALLOWED_USER_IDS` ortam değişkenindeki (virgülle ayrılmış
sayısal) Telegram kullanıcı ID listesidir. Bu liste **boşsa veya
tanımsızsa, fail-closed tasarım gereği hiç kimse** bot'u kullanamaz —
"boş liste = herkese açık" değildir. Listede olmayan bir kullanıcıya
bot hiçbir yanıt vermez (komut seti dahi açık edilmez).

Desteklenen komutlar: `/projeler`, `/yeni_proje <ad>`,
`/gorevler <proje adı veya id>`, `/onayla <task_id>`. `/yeni_proje`
kasıtlı olarak kapsamı (scope_definition) boş bırakır — fail-closed
kapsam kontrolü gereği boş kapsam "hiçbir hedef izinli değil" demektir;
kapsam tanımlamak yapılandırılmış web formundan yapılmalıdır, serbest
Telegram metninden değil. Telegram üzerinden yapılan onaylar, web
tarafındaki JWT kullanıcısından değil `telegram:<user_id>` biçiminde
audit log'a yazılır.

## Durum

Bu iskelet, salt-okunur sunucu keşfinden sonra sıfırdan başlatılan ayrı bir
geliştirme hattıdır. Sunucudaki hiçbir mevcut servis bu depodan etkilenmez.
