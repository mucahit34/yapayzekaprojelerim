import { useMemo, useState } from "react";
import { AssistantPanel } from "./components/AssistantPanel";
import { ReportCanvas } from "./components/ReportCanvas";
import { Sidebar } from "./components/Sidebar";
import { TEMPLATES, type ReportSection } from "./data/templates";

export default function App() {
  const [templateId, setTemplateId] = useState(TEMPLATES[0].id);
  const [sectionsByTemplate, setSectionsByTemplate] = useState<Record<string, ReportSection[]>>(
    () => Object.fromEntries(TEMPLATES.map((t) => [t.id, t.sections]))
  );
  const [activeSectionId, setActiveSectionId] = useState(TEMPLATES[0].sections[0].id);
  const [assistantOpen, setAssistantOpen] = useState(false);

  const activeTemplate = useMemo(
    () => TEMPLATES.find((t) => t.id === templateId) ?? TEMPLATES[0],
    [templateId]
  );
  const sections = sectionsByTemplate[templateId];

  function handleSelectTemplate(id: string) {
    setTemplateId(id);
    setActiveSectionId(sectionsByTemplate[id][0].id);
  }

  function handleReorder(next: ReportSection[]) {
    setSectionsByTemplate((prev) => ({ ...prev, [templateId]: next }));
  }

  return (
    <div className="flex h-screen flex-col bg-paper text-ink">
      <header className="flex items-center justify-between border-b border-slate-line/20 bg-paper-raised px-6 py-3">
        <div>
          <p className="font-serif text-base text-ink">{activeTemplate.name}</p>
          <p className="font-sans text-xs text-slate-muted">{activeTemplate.description}</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="rounded-sm border border-slate-line/40 px-3 py-1.5 font-sans text-sm text-ink/80 hover:bg-paper"
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
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          templates={TEMPLATES}
          activeTemplateId={templateId}
          onSelectTemplate={handleSelectTemplate}
          sections={sections}
          activeSectionId={activeSectionId}
          onSelectSection={setActiveSectionId}
          onReorderSections={handleReorder}
        />
        <main className="flex-1 overflow-y-auto">
          <ReportCanvas sections={sections} activeId={activeSectionId} />
        </main>
      </div>

      <AssistantPanel open={assistantOpen} onClose={() => setAssistantOpen(false)} />
    </div>
  );
}
