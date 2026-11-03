import { useEffect, useState } from "react";
import { ApiError, listRevisions, type ReportRevision } from "../api/client";

interface RevisionHistoryProps {
  open: boolean;
  onClose: () => void;
  reportId: string | null;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("tr-TR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function RevisionHistory({ open, onClose, reportId }: RevisionHistoryProps) {
  const [revisions, setRevisions] = useState<ReportRevision[]>([]);
  const [state, setState] = useState<"loading" | "error" | "empty" | "ready">("loading");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open || !reportId) return;
    // reportId panel açıkken değişebilir (ör. kullanıcı hızlıca başka bir
    // şablona geçerse); eski isteğin yanıtı geldiğinde state'i ezmesin.
    let cancelled = false;
    setState("loading");
    listRevisions(reportId)
      .then((data) => {
        if (cancelled) return;
        setRevisions(data);
        setState(data.length === 0 ? "empty" : "ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Geçmiş yüklenemedi.");
        setState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [open, reportId]);

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
      aria-label="Rapor sürüm geçmişi"
      aria-hidden={!open}
      className={`fixed inset-y-0 right-0 z-20 w-full border-l border-slate-line/30 bg-paper-raised transition-transform sm:w-[24rem] print:hidden ${
        open ? "translate-x-0" : "translate-x-full"
      }`}
    >
      <div className="flex items-center justify-between border-b border-slate-line/20 px-5 py-4">
        <h2 className="font-sans text-sm font-medium text-ink">Sürüm geçmişi</h2>
        <button
          type="button"
          onClick={onClose}
          className="text-sm text-slate-muted hover:text-ink"
        >
          Kapat
        </button>
      </div>

      <div className="h-[calc(100%-57px)] overflow-y-auto p-5">
        {!reportId && (
          <p className="font-sans text-sm text-slate-muted">
            Geçmişi görmek için önce raporu kaydedin.
          </p>
        )}

        {reportId && state === "loading" && (
          <p className="font-sans text-sm text-slate-muted">Yükleniyor…</p>
        )}

        {reportId && state === "error" && (
          <p className="font-sans text-sm text-signal-critical">{error}</p>
        )}

        {reportId && state === "empty" && (
          <p className="font-sans text-sm text-slate-muted">
            Bu rapor için henüz bir revizyon kaydı yok. AI taslağı uyguladığınızda burada
            görünecek.
          </p>
        )}

        {reportId && state === "ready" && (
          <ul className="space-y-3">
            {revisions.map((rev) => (
              <li key={rev.id} className="border-b border-slate-line/15 pb-3">
                <div className="mb-1 flex items-center gap-2">
                  <span
                    className={`rounded-sm px-1.5 py-0.5 font-sans text-[10px] font-medium ${
                      rev.is_ai_draft
                        ? "bg-ink/10 text-ink/70"
                        : "bg-signal-low/10 text-signal-low"
                    }`}
                  >
                    {rev.is_ai_draft ? "AI taslağı" : "Manuel"}
                  </span>
                  <span
                    className={`rounded-sm px-1.5 py-0.5 font-sans text-[10px] font-medium ${
                      rev.approved
                        ? "bg-signal-low/10 text-signal-low"
                        : "bg-signal-high/10 text-signal-high"
                    }`}
                  >
                    {rev.approved ? "Onaylı" : "Onay bekliyor"}
                  </span>
                </div>
                <p className="font-sans text-xs text-slate-muted">
                  {rev.created_by ?? "bilinmeyen"} — {formatDate(rev.created_at)}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
