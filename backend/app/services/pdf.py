"""Rapor PDF üretimi: data_snapshot -> HTML -> Playwright/Chromium -> PDF.

Frontend'deki rapor tuvaliyle (ReportCanvas.tsx) aynı tasarım dilini
(kağıt/mürekkep paleti, serif/mono tipografi, risk renk noktaları)
kullanır ki PDF, ekranda görülenle tutarlı olsun."""
from __future__ import annotations

import asyncio
import html
import os
from typing import TYPE_CHECKING

from jinja2 import Template

if TYPE_CHECKING:
    from playwright.async_api import Browser, Playwright

RISK_LABELS = {"critical": "Kritik", "high": "Yüksek", "medium": "Orta", "low": "Düşük"}
# frontend/tailwind.config.ts ile birebir aynı — scripts/validate_palette.js
# ile CVD-güvenli olarak doğrulanmış değerler.
RISK_COLORS = {
    "critical": "#B3261E",
    "high": "#2457A8",
    "medium": "#B38600",
    "low": "#1F7A52",
}


class PdfRenderError(Exception):
    """Chromium başlatılamadığında veya render başarısız olduğunda."""


_TEMPLATE = Template(
    """
<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<style>
  @page { margin: 28mm 20mm; }
  body {
    font-family: "IBM Plex Sans", system-ui, sans-serif;
    color: #14181F;
    background: #F3F4F1;
    margin: 0;
  }
  h1 { font-family: Georgia, serif; font-size: 28pt; margin: 0 0 4mm 0; }
  h2 { font-family: Georgia, serif; font-size: 15pt; margin: 8mm 0 3mm 0; }
  .meta { font-family: "IBM Plex Mono", monospace; font-size: 9pt; color: #5E6975; }
  .section { margin-bottom: 8mm; }
  .finding { display: flex; gap: 3mm; padding: 2mm 0; border-bottom: 0.3mm solid #e3e4e0; }
  .dot { width: 2.5mm; height: 2.5mm; border-radius: 50%; margin-top: 1.5mm; flex-shrink: 0; }
  .risk-label { font-size: 8pt; color: #5E6975; margin: 0 0 1mm 0; }
  .finding-text { font-size: 11pt; line-height: 1.5; margin: 0; }
  .evidence { font-family: "IBM Plex Mono", monospace; font-size: 9pt; white-space: pre-wrap;
    background: rgba(20,24,31,0.04); border: 0.3mm solid #c7cbc6; padding: 4mm; border-radius: 1mm; }
  .body-text { font-size: 11pt; line-height: 1.6; white-space: pre-wrap; }
</style>
</head>
<body>
{% for section in sections %}
  <div class="section">
    {% if section.kind == 'cover' %}
      {% set lines = section.body.split('\n') %}
      <h1>{{ lines[0] }}</h1>
      <div class="meta">
        {% for line in lines[1:] %}<div>{{ line }}</div>{% endfor %}
      </div>
    {% else %}
      <h2>{{ section.title }}</h2>
      {% if section.kind == 'findings' %}
        {% for line in section.body.split('\n') if line %}
          {% set parts = line.split(':', 1) %}
          {% if parts[0] in risk_colors %}
            <div class="finding">
              <span class="dot" style="background:{{ risk_colors[parts[0]] }}"></span>
              <div>
                <p class="risk-label">{{ risk_labels[parts[0]] }}</p>
                <p class="finding-text">{{ parts[1].strip() }}</p>
              </div>
            </div>
          {% else %}
            <p class="finding-text">{{ line }}</p>
          {% endif %}
        {% endfor %}
      {% elif section.kind == 'evidence' %}
        <div class="evidence">{{ section.body }}</div>
      {% else %}
        <p class="body-text">{{ section.body }}</p>
      {% endif %}
    {% endif %}
  </div>
{% endfor %}
</body>
</html>
"""
)


def render_report_html(data_snapshot: dict) -> str:
    sections = data_snapshot.get("sections", [])
    # Jinja autoescape kapalı olduğundan (büyük metin bloklarında daha
    # okunur kalsın diye) her alanı burada elle escape ediyoruz.
    safe_sections = [
        {
            "title": html.escape(s.get("title", "")),
            "kind": s.get("kind", "text"),
            "body": html.escape(s.get("body", "")),
        }
        for s in sections
    ]
    return _TEMPLATE.render(
        sections=safe_sections, risk_labels=RISK_LABELS, risk_colors=RISK_COLORS
    )


# --- Paylaşılan Chromium instance'ı ----------------------------------
# Her PDF isteğinde yeni bir Chromium süreci başlatıp kapatmak pahalı ve
# yük altında kaynak tükenmesine yol açabilir; bunun yerine tek bir
# tarayıcı süreci tembel (lazy) başlatılır ve istekler arasında paylaşılır.
# Her istek kendi page()'ini açıp kapatır (ucuz, izole).
_playwright: "Playwright | None" = None
_browser: "Browser | None" = None
_lock = asyncio.Lock()


async def _get_browser() -> "Browser":
    global _playwright, _browser
    if _browser is not None and _browser.is_connected():
        return _browser

    async with _lock:
        if _browser is not None and _browser.is_connected():
            return _browser

        from playwright.async_api import async_playwright

        if _playwright is None:
            _playwright = await async_playwright().start()

        executable_path = (
            os.environ.get("PLAYWRIGHT_CHROMIUM_PATH") or "/opt/pw-browsers/chromium"
        )
        launch_kwargs: dict = {"headless": True, "args": ["--no-sandbox"]}
        if os.path.exists(executable_path):
            launch_kwargs["executable_path"] = executable_path

        _browser = await _playwright.chromium.launch(**launch_kwargs)
        return _browser


async def shutdown_pdf_renderer() -> None:
    """FastAPI shutdown event'inde çağrılır; süreç kapanırken Chromium'u
    ve Playwright sürücüsünü düzgün kapatır."""
    global _playwright, _browser
    if _browser is not None:
        await _browser.close()
        _browser = None
    if _playwright is not None:
        await _playwright.stop()
        _playwright = None


async def render_report_pdf(data_snapshot: dict) -> bytes:
    try:
        from playwright.async_api import Error as PlaywrightError
    except ImportError as exc:  # pragma: no cover
        raise PdfRenderError(
            "playwright paketi kurulu değil (backend/requirements.txt)."
        ) from exc

    html_content = render_report_html(data_snapshot)

    try:
        browser = await _get_browser()
        page = await browser.new_page()
        try:
            await page.set_content(html_content, wait_until="load")
            pdf_bytes = await page.pdf(format="A4", print_background=True)
        finally:
            await page.close()
    except PlaywrightError as exc:
        raise PdfRenderError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - Chromium başlatma hataları çeşitlidir
        raise PdfRenderError(str(exc)) from exc

    return pdf_bytes
