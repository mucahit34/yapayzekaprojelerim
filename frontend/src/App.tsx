import { useEffect, useMemo, useState } from "react";
import {
  ApiError,
  approveRevision,
  clearToken,
  createRevision,
  fetchReportPdf,
  getToken,
  listReports,
  saveReport,
  setUnauthorizedHandler,
  type Project,
  type Report,
} from "./api/client";
import { AssistantPanel } from "./components/AssistantPanel";
import { Dashboard } from "./components/Dashboard";
import { LoginScreen } from "./components/LoginScreen";
import { ReportCanvas } from "./components/ReportCanvas";
import { RevisionHistory } from "./components/RevisionHistory";
import { RiskSummary } from "./components/RiskSummary";
import { Sidebar } from "./components/Sidebar";
import { TEMPLATES, type ReportSection } from "./data/templates";

let nextSectionSeq = 1;

export default function App() {
  const [authenticated, setAuthenticated] = useState(() => Boolean(getToken()));

  useEffect(() => {
    setUnauthorizedHandler(() => setAuthenticated(false));
  }, []);

  if (!authenticated) {
    return <LoginScreen onAuthenticated={() => setAuthenticated(true)} />;
  }

  return (
    <AppShell
      onLogout={() => {
        clearToken();
        setAuthenticated(false);
      }}
    />
  );
}

type SaveState = "idle" | "saving" | "saved" | "error";
type ExportState = "idle" | "exporting" | "error";
type View = "studio" | "dashboard";

// Proje seçimi iki görünüm (Stüdyo/Kontrol paneli) arasında paylaşılır —
// biri diğerinde seçileni unutmamalı.
function AppShell({ onLogout }: { onLogout: () => void }) {
  const [view, setView] = useState<View>("studio");
  const [activeProject, setActiveProject] = useState<Project | null>(null);

  if (view === "dashboard") {
    return (
      <Dashboard
        activeProject={activeProject}
        onSelectProject={setActiveProject}
        onLogout={onLogout}
        onSwitchView={() => setView("studio")}
      />
    );
  }

  return (
    <Studio
      activeProject={activeProject}
      onSelectProject={setActiveProject}
      onLogout={onLogout}
      onSwitchView={() => setView("dashboard")}
    />
  );
}

interface StudioProps {
  activeProject: Project | null;
  onSelectProject: (project: Project) => void;
  onLogout: () => void;
  onSwitchView: () => void;
}

function Studio({ activeProject, onSelectProject, onLogout, onSwitchView }: StudioProps) {
  const [templateId, setTemplateId] = useState(TEMPLATES[0].id);
  const [sectionsByTemplate, setSectionsByTemplate] = useState<Record<string, ReportSection[]>>(
    () => Object.fromEntries(TEMPLATES.map((t) => [t.id, t.sections]))
  );
  const [activeSectionId, setActiveSectionId] = useState(TEMPLATES[0].sections[0].id);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Proje+şablon başına kaydedilmiş rapor. null = henüz kaydedilmemiş
  // (yalnızca yerel taslak) — PDF ve AI revizyon geçmişi bir kayıtlı
  // rapor gerektirir.
  const [currentReport, setCurrentReport] = useState<Report | null>(null);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [saveError, setSaveError] = useState("");
  const [exportState, setExportState] = useState<ExportState>("idle");
  const [exportError, setExportError] = useState("");

  const activeTemplate = useMemo(
    () => TEMPLATES.find((t) => t.id === templateId) ?? TEMPLATES[0],
    [templateId]
  );
  const sections = sectionsByTemplate[templateId] ?? [];
  const activeSection = sections.find((s) => s.id === activeSectionId) ?? null;

  // Proje veya şablon değiştiğinde, o ikili için kaydedilmiş bir rapor
  // var mı diye backend'e bakılır; varsa kaydedilmiş hali yerel state'in
  // üzerine yazılır (rapor her zaman tek bir "geçerli" durumu temsil eder).
  useEffect(() => {
    if (!activeProject) {
      setCurrentReport(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const reports = await listReports(activeProject.id);
        if (cancelled) return;
        const match = reports.find((r) => r.template === templateId) ?? null;
        setCurrentReport(match);
        if (match) {
          setSectionsByTemplate((prev) => ({
            ...prev,
            [templateId]: match.data_snapshot.sections as ReportSection[],
          }));
        }
      } catch {
        // Sessizce yerel taslakta kal — kullanıcı yine de düzenlemeye
        // devam edebilsin; Kaydet denendiğinde hata zaten gösterilecek.
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeProject?.id, templateId]);

  function handleSelectTemplate(id: string) {
    setTemplateId(id);
    const firstSection = sectionsByTemplate[id]?.[0];
    if (firstSection) setActiveSectionId(firstSection.id);
    setSidebarOpen(false);
    setSaveState("idle");
  }

  function handleReorder(next: ReportSection[]) {
    setSectionsByTemplate((prev) => ({ ...prev, [templateId]: next }));
    setSaveState("idle");
  }

  function handleAddSection() {
    const id = `custom-${nextSectionSeq++}`;
    const newSection: ReportSection = { id, title: "Yeni bölüm", kind: "text", body: "" };
    setSectionsByTemplate((prev) => ({
      ...prev,
      [templateId]: [...(prev[templateId] ?? []), newSection],
    }));
    setActiveSectionId(id);
    setSaveState("idle");
  }

  useEffect(() => {
    if (!sidebarOpen) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setSidebarOpen(false);
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [sidebarOpen]);

  function handleUpdateSectionBody(sectionId: string, body: string) {
    setSectionsByTemplate((prev) => ({
      ...prev,
      [templateId]: prev[templateId].map((s) => (s.id === sectionId ? { ...s, body } : s)),
    }));
    setSaveState("idle");
  }

  async function handleSave(): Promise<Report | null> {
    if (!activeProject) {
      setSaveState("error");
      setSaveError("Önce bir proje seçin veya oluşturun.");
      return null;
    }
    setSaveState("saving");
    try {
      const report = await saveReport({
        project_id: activeProject.id,
        template: templateId,
        data_snapshot: { template: templateId, sections },
      });
      setCurrentReport(report);
      setSaveState("saved");
      return report;
    } catch (err) {
      setSaveState("error");
      setSaveError(err instanceof ApiError ? err.message : "Kaydedilemedi.");
      return null;
    }
  }

  // AI taslağı uygulandığında: kayıtlı bir rapor varsa, değişikliği
  // denetlenebilir bir ReportRevision olarak kaydet ve hemen onayla
  // (buton zaten 'Rapora uygula' = onay anlamına geliyor). Kayıtlı rapor
  // yoksa yalnızca yerel state güncellenir — ilk kayıt yapılana kadar
  // AI geçmişi tutulamaz.
  async function handleApplyDraft(body: string) {
    if (!activeSection) return;
    const updatedSections = sections.map((s) =>
      s.id === activeSection.id ? { ...s, body } : s
    );
    setSectionsByTemplate((prev) => ({ ...prev, [templateId]: updatedSections }));
    setSaveState("idle");

    if (!currentReport) return;
    try {
      const revision = await createRevision(currentReport.id, {
        content: { template: templateId, sections: updatedSections },
        is_ai_draft: true,
      });
      const updatedReport = await approveRevision(currentReport.id, revision.id);
      setCurrentReport(updatedReport);
      setSaveState("saved");
    } catch {
      // Yerel değişiklik zaten uygulandı; yalnızca denetim kaydı
      // başarısız oldu. Kullanıcıyı Kaydet'e yönlendirmek için state'i
      // 'idle' bırakıyoruz (zaten öyle).
    }
  }

  async function handleExportPdf() {
    setExportState("exporting");
    setExportError("");
    // PDF her zaman kaydedilmiş data_snapshot'tan üretilir; bu yüzden
    // currentReport zaten varsa bile her export öncesi tekrar kaydedilir —
    // aksi halde ekrandaki son (henüz kaydedilmemiş) düzenlemeler PDF'e
    // yansımaz ve indirilen dosya sessizce bayat kalır.
    const report = await handleSave();
    if (!report) {
      setExportState("error");
      setExportError("PDF için önce rapor kaydedilmeli; kayıt başarısız oldu.");
      return;
    }
    try {
      const blob = await fetchReportPdf(report.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `rapor-${report.id.slice(0, 8)}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setExportState("idle");
    } catch (err) {
      setExportState("error");
      setExportError(err instanceof ApiError ? err.message : "PDF indirilemedi.");
    }
  }

  const saveLabel =
    saveState === "saving"
      ? "Kaydediliyor…"
      : saveState === "saved"
        ? "Kaydedildi"
        : saveState === "error"
          ? "Tekrar dene"
          : "Kaydet";

  return (
    <div className="flex h-screen flex-col bg-paper text-ink">
      <header className="flex items-center justify-between gap-4 border-b border-slate-line/20 bg-paper-raised px-4 py-3 sm:px-6 print:hidden">
        <div className="flex min-w-0 items-center gap-3">
          <div className="hidden flex-shrink-0 items-center gap-1 rounded-sm border border-slate-line/30 p-0.5 sm:flex">
            <button
              type="button"
              className="rounded-sm bg-ink px-3 py-1 font-sans text-sm text-paper"
            >
              Stüdyo
            </button>
            <button
              type="button"
              onClick={onSwitchView}
              className="rounded-sm px-3 py-1 font-sans text-sm text-ink/70 hover:bg-paper"
            >
              Kontrol paneli
            </button>
          </div>
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            aria-label="Paneli aç"
            className="flex min-h-11 min-w-11 flex-shrink-0 items-center justify-center rounded-sm border border-slate-line/30 text-ink/70 hover:bg-paper md:hidden"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden>
              <path d="M2 4.5h14M2 9h14M2 13.5h14" stroke="currentColor" strokeWidth="1.5" />
            </svg>
          </button>
          <div className="min-w-0">
            <p className="truncate font-serif text-base text-ink">{activeTemplate.name}</p>
            <p className="hidden truncate font-sans text-xs text-slate-muted sm:block">
              {activeTemplate.description}
            </p>
          </div>
        </div>

        <RiskSummary sections={sections} />

        <div className="flex flex-shrink-0 items-center gap-2 sm:gap-3">
          {saveState === "error" && (
            <span className="hidden font-sans text-xs text-signal-critical sm:inline">
              {saveError}
            </span>
          )}
          <button
            type="button"
            onClick={handleSave}
            disabled={saveState === "saving"}
            className="hidden rounded-sm border border-slate-line/40 px-3 py-1.5 font-sans text-sm text-ink/80 hover:bg-paper disabled:opacity-50 sm:inline-block"
          >
            {saveLabel}
          </button>
          <button
            type="button"
            onClick={handleExportPdf}
            disabled={exportState === "exporting"}
            title={exportState === "error" ? exportError : undefined}
            className="hidden rounded-sm border border-slate-line/40 px-3 py-1.5 font-sans text-sm text-ink/80 hover:bg-paper disabled:opacity-50 sm:inline-block"
          >
            {exportState === "exporting" ? "PDF hazırlanıyor…" : "PDF olarak dışa aktar"}
          </button>
          <button
            type="button"
            onClick={() => setHistoryOpen(true)}
            className="hidden rounded-sm border border-slate-line/40 px-3 py-1.5 font-sans text-sm text-ink/80 hover:bg-paper sm:inline-block"
          >
            Geçmiş
          </button>
          <button
            type="button"
            onClick={onSwitchView}
            aria-label="Kontrol paneline geç"
            className="flex min-h-11 min-w-11 flex-shrink-0 items-center justify-center rounded-sm border border-slate-line/30 text-ink/70 hover:bg-paper sm:hidden"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
              <rect x="1.5" y="1.5" width="6" height="6" rx="0.5" stroke="currentColor" strokeWidth="1.3" />
              <rect x="8.5" y="1.5" width="6" height="4" rx="0.5" stroke="currentColor" strokeWidth="1.3" />
              <rect x="8.5" y="7.5" width="6" height="7" rx="0.5" stroke="currentColor" strokeWidth="1.3" />
              <rect x="1.5" y="9.5" width="6" height="5" rx="0.5" stroke="currentColor" strokeWidth="1.3" />
            </svg>
          </button>
          <button
            type="button"
            onClick={() => setAssistantOpen(true)}
            className="rounded-sm bg-ink px-3 py-1.5 font-sans text-sm text-paper hover:bg-ink-soft"
          >
            AI asistan
          </button>
          <button
            type="button"
            onClick={onLogout}
            className="hidden font-sans text-sm text-slate-muted hover:text-ink sm:inline-block"
          >
            Çıkış yap
          </button>
        </div>
      </header>

      {exportState === "error" && (
        <p className="border-b border-slate-line/20 bg-paper-raised px-6 py-2 font-sans text-sm text-signal-critical print:hidden">
          {exportError}
        </p>
      )}

      <div className="relative flex flex-1 overflow-hidden">
        {sidebarOpen && (
          <button
            type="button"
            aria-label="Paneli kapat"
            onClick={() => setSidebarOpen(false)}
            className="fixed inset-0 z-10 bg-ink/30 md:hidden"
          />
        )}
        <div
          className={`fixed inset-y-0 left-0 z-20 transition-transform duration-200 md:static md:translate-x-0 ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <Sidebar
            activeProject={activeProject}
            onSelectProject={(p) => {
              onSelectProject(p);
              setSaveState("idle");
            }}
            templates={TEMPLATES}
            activeTemplateId={templateId}
            onSelectTemplate={handleSelectTemplate}
            sections={sections}
            activeSectionId={activeSectionId}
            onSelectSection={(id) => {
              setActiveSectionId(id);
              setSidebarOpen(false);
            }}
            onReorderSections={handleReorder}
            onAddSection={handleAddSection}
          />
        </div>
        <main className="flex-1 overflow-y-auto print:overflow-visible">
          <ReportCanvas sections={sections} onEditSectionBody={handleUpdateSectionBody} />
        </main>
      </div>

      <AssistantPanel
        open={assistantOpen}
        onClose={() => setAssistantOpen(false)}
        activeSection={activeSection}
        onApplyDraft={handleApplyDraft}
      />

      <RevisionHistory
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        reportId={currentReport?.id ?? null}
      />
    </div>
  );
}
