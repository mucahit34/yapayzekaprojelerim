import type { ReportSection, ReportTemplate } from "../data/templates";
import { SectionList } from "./SectionList";

interface SidebarProps {
  templates: ReportTemplate[];
  activeTemplateId: string;
  onSelectTemplate: (id: string) => void;
  sections: ReportSection[];
  activeSectionId: string;
  onSelectSection: (id: string) => void;
  onReorderSections: (sections: ReportSection[]) => void;
}

export function Sidebar({
  templates,
  activeTemplateId,
  onSelectTemplate,
  sections,
  activeSectionId,
  onSelectSection,
  onReorderSections,
}: SidebarProps) {
  return (
    <aside className="flex h-full w-72 flex-shrink-0 flex-col border-r border-slate-line/20 bg-paper">
      <div className="border-b border-slate-line/20 px-5 py-4">
        <p className="font-sans text-xs text-slate-muted">Proje</p>
        <p className="font-serif text-lg text-ink">Acme Lojistik — PRJ-0142</p>
      </div>

      <div className="border-b border-slate-line/20 px-5 py-4">
        <p className="mb-2 font-sans text-xs text-slate-muted">Şablon</p>
        <div className="flex flex-col gap-1.5">
          {templates.map((template) => (
            <button
              key={template.id}
              type="button"
              onClick={() => onSelectTemplate(template.id)}
              className={`rounded-sm px-2.5 py-2 text-left font-sans text-sm transition-colors ${
                template.id === activeTemplateId
                  ? "bg-ink text-paper"
                  : "text-ink/80 hover:bg-paper-raised"
              }`}
            >
              <span className="block">{template.name}</span>
              <span
                className={`block text-xs ${
                  template.id === activeTemplateId ? "text-paper/70" : "text-slate-muted"
                }`}
              >
                {template.audience}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        <p className="mb-2 font-sans text-xs text-slate-muted">Bölümler</p>
        <SectionList
          sections={sections}
          activeId={activeSectionId}
          onSelect={onSelectSection}
          onReorder={onReorderSections}
        />
        <button
          type="button"
          className="mt-2 w-full rounded-sm border border-dashed border-slate-line/40 px-2.5 py-2 text-left font-sans text-sm text-slate-muted hover:border-slate-line hover:text-ink"
        >
          Bölüm ekle
        </button>
      </div>
    </aside>
  );
}
