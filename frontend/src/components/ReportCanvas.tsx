import type { ReportSection, RiskLevel } from "../data/templates";
import { RISK_LABELS } from "../data/templates";

const RISK_DOT: Record<RiskLevel, string> = {
  critical: "bg-signal-critical",
  high: "bg-signal-high",
  medium: "bg-signal-medium",
  low: "bg-signal-low",
};

function parseFindingLine(line: string) {
  const [level, ...rest] = line.split(":");
  const risk = (level as RiskLevel) in RISK_LABELS ? (level as RiskLevel) : null;
  return { risk, text: risk ? rest.join(":").trim() : line };
}

function SectionBody({ section }: { section: ReportSection }) {
  if (section.kind === "cover") {
    const [titleLine, ...rest] = section.body.split("\n");
    return (
      <div className="flex min-h-[18rem] flex-col justify-end border-b border-slate-line/30 pb-10">
        <p className="font-serif text-4xl leading-tight text-ink">{titleLine}</p>
        <div className="mt-4 space-y-1 font-mono text-sm text-slate-muted">
          {rest.map((line, i) => (
            <p key={i}>{line}</p>
          ))}
        </div>
      </div>
    );
  }

  if (section.kind === "findings") {
    const lines = section.body.split("\n").filter(Boolean);
    return (
      <ul className="space-y-3">
        {lines.map((line, i) => {
          const { risk, text } = parseFindingLine(line);
          return (
            <li key={i} className="flex items-start gap-3 border-b border-slate-line/15 pb-3">
              {risk && (
                <span
                  className={`mt-1.5 inline-block h-2 w-2 flex-shrink-0 rounded-full ${RISK_DOT[risk]}`}
                  aria-hidden
                />
              )}
              <div>
                {risk && (
                  <p className="font-sans text-xs font-medium text-ink/60">{RISK_LABELS[risk]}</p>
                )}
                <p className="font-serif text-base leading-relaxed text-ink">{text}</p>
              </div>
            </li>
          );
        })}
      </ul>
    );
  }

  if (section.kind === "evidence") {
    return (
      <pre className="whitespace-pre-wrap break-words rounded-sm border border-slate-line/30 bg-ink/[0.03] p-4 font-mono text-sm leading-relaxed text-ink/90">
        {section.body}
      </pre>
    );
  }

  return (
    <p className="max-w-[60ch] font-serif text-base leading-relaxed text-ink/90">
      {section.body}
    </p>
  );
}

interface ReportCanvasProps {
  sections: ReportSection[];
  activeId: string;
}

export function ReportCanvas({ sections, activeId }: ReportCanvasProps) {
  return (
    <div className="flex justify-center px-10 py-10">
      <div className="w-full max-w-[42rem] bg-paper-raised shadow-[0_1px_2px_rgba(20,24,31,0.08),0_12px_32px_rgba(20,24,31,0.08)]">
        <div className="space-y-10 px-12 py-14">
          {sections.map((section) => (
            <section
              key={section.id}
              id={`section-${section.id}`}
              className={`scroll-mt-10 ${section.id === activeId ? "" : ""}`}
            >
              {section.kind !== "cover" && (
                <h2 className="mb-4 font-serif text-xl text-ink">{section.title}</h2>
              )}
              <SectionBody section={section} />
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
