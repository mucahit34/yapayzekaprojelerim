"""AI destekli taslak üretimi. Her yanıt bir taslaktır; rapora otomatik
yazılmaz — onay akışı frontend tarafında uygulanır (bkz. CLAUDE.md:
'AI değişiklikleri önce taslak olmalı ve onayla uygulanmalı')."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(prefix="/ai", tags=["ai"])


class DraftRequest(BaseModel):
    instruction: str
    section_text: str = ""


class DraftResponse(BaseModel):
    draft: str
    available: bool


@router.post("/draft", response_model=DraftResponse)
async def generate_draft(payload: DraftRequest) -> DraftResponse:
    settings = get_settings()
    if not settings.anthropic_api_key:
        return DraftResponse(
            draft=(
                "AI asistanı yapılandırılmamış: sunucuda ANTHROPIC_API_KEY ortam "
                "değişkeni ayarlı değil. Bir anahtar eklendiğinde bu uç nokta "
                "gerçek taslaklar üretecek."
            ),
            available=False,
        )

    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt = (
        f"Aşağıdaki güvenlik raporu bölümü için şu talimatı uygula: "
        f"'{payload.instruction}'.\n\nMevcut metin:\n{payload.section_text}\n\n"
        "Yalnızca güncellenmiş metni döndür, açıklama ekleme."
    )
    try:
        response = await client.messages.create(
            model=settings.ai_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        return DraftResponse(draft=text or "(boş yanıt)", available=True)
    except Exception as exc:  # pragma: no cover - ağ/servis hatası
        return DraftResponse(
            draft=f"AI isteği başarısız oldu: {exc}",
            available=False,
        )
