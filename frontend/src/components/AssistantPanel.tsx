import { useState } from "react";

interface Draft {
  id: string;
  instruction: string;
  preview: string;
}

interface AssistantPanelProps {
  open: boolean;
  onClose: () => void;
}

export function AssistantPanel({ open, onClose }: AssistantPanelProps) {
  const [instruction, setInstruction] = useState("");
  const [draft, setDraft] = useState<Draft | null>(null);

  function requestDraft() {
    if (!instruction.trim()) return;
    // Backend hazır olduğunda burası /api/reports/{id}/ai-draft çağırır.
    // Yanıt her zaman bir taslak olarak gelir; belgeye yazılmaz.
    setDraft({
      id: crypto.randomUUID(),
      instruction,
      preview:
        "Taslak önizleme burada görünecek. Hiçbir değişiklik, onaylamadan rapora yazılmaz.",
    });
    setInstruction("");
  }

  return (
    <aside
      aria-hidden={!open}
      className={`fixed inset-y-0 right-0 z-20 w-[22rem] border-l border-slate-line/30 bg-paper-raised transition-transform ${
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
          {draft ? (
            <div className="rounded-sm border border-dashed border-slate-line/50 p-4">
              <p className="mb-1 font-sans text-xs font-medium text-slate-muted">
                Taslak — onay bekliyor
              </p>
              <p className="mb-3 font-sans text-xs text-ink/60">“{draft.instruction}”</p>
              <p className="font-serif text-sm leading-relaxed text-ink">{draft.preview}</p>
              <div className="mt-4 flex gap-2">
                <button
                  type="button"
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
            </div>
          ) : (
            <p className="font-sans text-sm text-slate-muted">
              Bir bölümü kısaltmasını, netleştirmesini veya yeniden yazmasını isteyin. Her öneri
              taslak olarak gelir, siz onaylamadan belgeye yazılmaz.
            </p>
          )}
        </div>

        <div className="flex gap-2 border-t border-slate-line/20 pt-4">
          <input
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && requestDraft()}
            placeholder="Örn: Bulgular bölümünü kısalt"
            className="flex-1 rounded-sm border border-slate-line/30 bg-paper px-3 py-2 font-sans text-sm text-ink placeholder:text-slate-muted focus:border-slate-line"
          />
          <button
            type="button"
            onClick={requestDraft}
            className="rounded-sm bg-ink px-3 py-2 font-sans text-sm text-paper hover:bg-ink-soft"
          >
            Sor
          </button>
        </div>
      </div>
    </aside>
  );
}
