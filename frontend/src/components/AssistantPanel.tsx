import { useEffect, useState } from "react";
import { ApiError, requestAiDraft } from "../api/client";
import type { ReportSection } from "../data/templates";

interface Draft {
  instruction: string;
  text: string;
  available: boolean;
}

interface AssistantPanelProps {
  open: boolean;
  onClose: () => void;
  activeSection: ReportSection | null;
  onApplyDraft: (body: string) => void;
}

export function AssistantPanel({ open, onClose, activeSection, onApplyDraft }: AssistantPanelProps) {
  const [instruction, setInstruction] = useState("");
  const [draft, setDraft] = useState<Draft | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function requestDraft() {
    if (!instruction.trim() || !activeSection) return;
    setLoading(true);
    setError("");
    try {
      const response = await requestAiDraft({
        instruction,
        section_text: activeSection.body,
      });
      setDraft({ instruction, text: response.draft, available: response.available });
      setInstruction("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Beklenmeyen bir hata oluştu.");
      // Talimat metni silinmiyor: istek başarısız olduğunda kullanıcı
      // yeniden yazmak zorunda kalmadan tekrar deneyebilsin.
    } finally {
      setLoading(false);
    }
  }

  function applyDraft() {
    if (!draft) return;
    onApplyDraft(draft.text);
    setDraft(null);
  }

  useEffect(() => {
    if (!open) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  return (
    <aside
      aria-label="AI asistan paneli"
      aria-hidden={!open}
      className={`fixed inset-y-0 right-0 z-20 w-full border-l border-slate-line/30 bg-paper-raised transition-transform sm:w-[22rem] print:hidden ${
        open ? "translate-x-0" : "translate-x-full"
      }`}
    >
      <div className="flex items-center justify-between border-b border-slate-line/20 px-5 py-4">
        <h2 className="font-sans text-sm font-medium text-ink">AI asistan</h2>
        <button
          type="button"
          onClick={onClose}
          className="text-sm text-slate-muted hover:text-ink"
        >
          Kapat
        </button>
      </div>

      <div className="flex h-[calc(100%-57px)] flex-col justify-between p-5">
        <div className="space-y-4 overflow-y-auto">
          {!activeSection && (
            <p className="font-sans text-sm text-slate-muted">
              Önce soldaki listeden bir bölüm seçin.
            </p>
          )}

          {error && <p className="font-sans text-sm text-signal-critical">{error}</p>}

          {draft ? (
            <div className="rounded-sm border border-dashed border-slate-line/50 p-4">
              <p className="mb-1 font-sans text-xs font-medium text-slate-muted">
                {draft.available ? "Taslak — onay bekliyor" : "AI şu an kullanılamıyor"}
              </p>
              <p className="mb-3 font-sans text-xs text-ink/60">“{draft.instruction}”</p>
              <p className="font-serif text-sm leading-relaxed text-ink">{draft.text}</p>
              {draft.available && (
                <div className="mt-4 flex gap-2">
                  <button
                    type="button"
                    onClick={applyDraft}
                    className="rounded-sm bg-ink px-3 py-1.5 font-sans text-xs text-paper hover:bg-ink-soft"
                  >
                    Rapora uygula
                  </button>
                  <button
                    type="button"
                    onClick={() => setDraft(null)}
                    className="rounded-sm border border-slate-line/40 px-3 py-1.5 font-sans text-xs text-ink/70 hover:bg-paper"
                  >
                    Reddet
                  </button>
                </div>
              )}
            </div>
          ) : (
            !error && (
              <p className="font-sans text-sm text-slate-muted">
                Seçili bölümü kısaltmasını, netleştirmesini veya yeniden yazmasını isteyin. Her
                öneri taslak olarak gelir, siz onaylamadan belgeye yazılmaz.
              </p>
            )
          )}
        </div>

        <div className="flex gap-2 border-t border-slate-line/20 pt-4">
          <input
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && requestDraft()}
            disabled={!activeSection || loading}
            placeholder="Örn: Bu bölümü kısalt"
            className="min-w-0 flex-1 rounded-sm border border-slate-line/30 bg-paper px-3 py-2 font-sans text-sm text-ink placeholder:text-slate-muted focus:border-slate-line disabled:opacity-50"
          />
          <button
            type="button"
            onClick={requestDraft}
            disabled={!activeSection || loading}
            className="rounded-sm bg-ink px-3 py-2 font-sans text-sm text-paper hover:bg-ink-soft disabled:opacity-50"
          >
            {loading ? "…" : "Sor"}
          </button>
        </div>
      </div>
    </aside>
  );
}
