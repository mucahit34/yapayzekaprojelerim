import type { ReportSection, RiskLevel } from "../data/templates";
import { RISK_LABELS } from "../data/templates";
import { countRisksBySections } from "../utils/findings";

const RISK_ORDER: RiskLevel[] = ["critical", "high", "medium", "low"];

const RISK_DOT: Record<RiskLevel, string> = {
  critical: "bg-signal-critical",
  high: "bg-signal-high",
  medium: "bg-signal-medium",
  low: "bg-signal-low",
};

interface RiskSummaryProps {
  sections: ReportSection[];
}

export function RiskSummary({ sections }: RiskSummaryProps) {
  const counts = countRisksBySections(sections);
  const total = RISK_ORDER.reduce((sum, level) => sum + counts[level], 0);

  if (total === 0) return null;

  return (
    <dl
      className="hidden items-center gap-4 border-l border-slate-line/20 pl-4 sm:flex"
      aria-label="Bulgu risk dağılımı"
    >
      {RISK_ORDER.map((level) => (
        <div key={level} className="flex items-center gap-1.5">
          <span className={`h-2 w-2 flex-shrink-0 rounded-full ${RISK_DOT[level]}`} aria-hidden />
          <dt className="font-sans text-xs text-slate-muted">{RISK_LABELS[level]}</dt>
          <dd className="font-sans text-xs font-medium text-ink">{counts[level]}</dd>
        </div>
      ))}
    </dl>
  );
}
