import { useEffect, useMemo, useState } from "react";
import { clearToken, getToken, setUnauthorizedHandler, type Project } from "./api/client";
import { AssistantPanel } from "./components/AssistantPanel";
import { LoginScreen } from "./components/LoginScreen";
import { ReportCanvas } from "./components/ReportCanvas";
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

  return <Studio onLogout={() => {
    clearToken();
    setAuthenticated(false);
  }} />;
}

function Studio({ onLogout }: { onLogout: () => void }) {
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [templateId, setTemplateId] = useState(TEMPLATES[0].id);
  const [sectionsByTemplate, setSectionsByTemplate] = useState<Record<string, ReportSection[]>>(
    () => Object.fromEntries(TEMPLATES.map((t) => [t.id, t.sections]))
  );
  const [activeSectionId, setActiveSectionId] = useState(TEMPLATES[0].sections[0].id);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const activeTemplate = useMemo(
    () => TEMPLATES.find((t) => t.id === templateId) ?? TEMPLATES[0],
    [templateId]
  );
  const sections = sectionsByTemplate[templateId] ?? [];
  const activeSection = sections.find((s) => s.id === activeSectionId) ?? null;

  function handleSelectTemplate(id: string) {
    setTemplateId(id);
    const firstSection = sectionsByTemplate[id]?.[0];
    if (firstSection) setActiveSectionId(firstSection.id);
    setSidebarOpen(false);
  }

  function handleReorder(next: ReportSection[]) {
    setSectionsByTemplate((prev) => ({ ...prev, [templateId]: next }));
  }

  function handleAddSection() {
    const id = `custom-${nextSectionSeq++}`;
    const newSection: ReportSection = {
      id,
      title: "Yeni bölüm",
      kind: "text",
      body: "",
    };
    setSectionsByTemplate((prev) => ({
      ...prev,
      [templateId]: [...(prev[templateId] ?? []), newSection],
    }));
    setActiveSectionId(id);
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
  }

  return (
    <div className="flex h-screen flex-col bg-paper text-ink">
      <header className="flex items-center justify-between gap-4 border-b border-slate-line/20 bg-paper-raised px-4 py-3 sm:px-6 print:hidden">
        <div className="flex min-w-0 items-center gap-3">
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
          <button
            type="button"
            onClick={() => window.print()}
            className="hidden rounded-sm border border-slate-line/40 px-3 py-1.5 font-sans text-sm text-ink/80 hover:bg-paper sm:inline-block"
          >
            PDF olarak dışa aktar
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
            onSelectProject={setActiveProject}
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
        onApplyDraft={(body) => activeSection && handleUpdateSectionBody(activeSection.id, body)}
      />
    </div>
  );
}
