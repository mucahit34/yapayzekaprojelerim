import type { ReportSection, RiskLevel } from "../data/templates";
import { RISK_LABELS } from "../data/templates";

export interface ParsedFindingLine {
  risk: RiskLevel | null;
  text: string;
}

const RISK_LEVELS = Object.keys(RISK_LABELS) as RiskLevel[];

export function parseFindingLine(line: string): ParsedFindingLine {
  const [level, ...rest] = line.split(":");
  const risk = (RISK_LEVELS as string[]).includes(level) ? (level as RiskLevel) : null;
  return { risk, text: risk ? rest.join(":").trim() : line };
}

/** Aktif şablondaki tüm "findings" bölümlerinden risk seviyesi sayımı çıkarır. */
export function countRisksBySections(sections: ReportSection[]): Record<RiskLevel, number> {
  const counts: Record<RiskLevel, number> = { critical: 0, high: 0, medium: 0, low: 0 };
  for (const section of sections) {
    if (section.kind !== "findings") continue;
    for (const line of section.body.split("\n").filter(Boolean)) {
      const { risk } = parseFindingLine(line);
      if (risk) counts[risk] += 1;
    }
  }
  return counts;
}
