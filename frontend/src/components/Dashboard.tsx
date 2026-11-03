import { useEffect, useRef, useState } from "react";
import {
  ApiError,
  approveTask,
  listAuditEvents,
  listFindings,
  listReports,
  listTasks,
  type AuditEvent,
  type Finding,
  type FindingStatus,
  type Project,
  type Report,
  type RiskLevelValue,
  type Task,
} from "../api/client";
import { RISK_LABELS } from "../data/templates";
import { ProjectPicker } from "./ProjectPicker";

const TASK_STATUS_LABELS: Record<Task["status"], string> = {
  awaiting_approval: "Onay bekliyor",
  pending: "Beklemede",
  running: "Çalışıyor",
  completed: "Tamamlandı",
  failed: "Başarısız",
  rejected: "Reddedildi",
};

// Bulgu durumu gerçek bir olgunluk sırasıdır (şüpheli → doğrulanıyor →
// doğrulandı) — bu yüzden kategorik risk renkleri değil, tek bir rengin
// (mürekkep) artan opaklığı kullanılır. false_positive ve
// remediated_pending_retest bu sıranın dışında, kendi anlamlarıyla
// (sırasıyla "iptal" ve "dikkat gerektiriyor") ayrı gösterilir.
const FINDING_STATUS_ORDER: FindingStatus[] = ["suspected", "verifying", "confirmed"];
const FINDING_STATUS_LABELS: Record<FindingStatus, string> = {
  suspected: "Şüpheli",
  verifying: "Doğrulanıyor",
  confirmed: "Doğrulandı",
  false_positive: "Yanlış pozitif",
  remediated_pending_retest: "Yeniden test bekliyor",
};
const FINDING_STATUS_OPACITY: Record<string, string> = {
  suspected: "bg-ink/20",
  verifying: "bg-ink/50",
  confirmed: "bg-ink/85",
};

const RISK_ORDER: RiskLevelValue[] = ["critical", "high", "medium", "low"];
const RISK_DOT: Record<RiskLevelValue, string> = {
  critical: "bg-signal-critical",
  high: "bg-signal-high",
  medium: "bg-signal-medium",
  low: "bg-signal-low",
};

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("tr-TR", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

const ACTION_LABELS: Record<string, string> = {
  "project.created": "proje oluşturdu",
  "project.updated": "projeyi güncelledi",
  "task.created_awaiting_approval": "görev oluşturdu",
  "task.approved": "görevi onayladı",
  "task.rejected_out_of_scope": "görev kapsam dışı reddedildi",
  "finding.created": "bulgu ekledi",
  "finding.updated": "bulguyu güncelledi",
  "report.created": "rapor oluşturdu",
  "report.updated": "raporu güncelledi",
  "report_revision.created": "AI taslağı oluşturdu",
  "report_revision.approved": "revizyonu onayladı",
  "auth.login_succeeded": "giriş yaptı",
};

interface DashboardProps {
  activeProject: Project | null;
  onSelectProject: (project: Project) => void;
  onLogout: () => void;
  onSwitchView: () => void;
}

export function Dashboard({
  activeProject,
  onSelectProject,
  onLogout,
  onSwitchView,
}: DashboardProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [state, setState] = useState<"loading" | "error" | "ready">("loading");
  const [error, setError] = useState("");
  const [approvingId, setApprovingId] = useState<string | null>(null);

  // Kullanıcı proje değiştirdiğinde önceki, henüz tamamlanmamış bir
  // yükleme isteğinin yanıtı gelirse state'i ezmesin — her çağrı kendi
  // sıra numarasını taşır, yalnızca EN SON başlatılan istek state'i yazar.
  const requestIdRef = useRef(0);

  async function load(projectId: string) {
    const requestId = ++requestIdRef.current;
    setState("loading");
    try {
      const [t, f, r, a] = await Promise.all([
        listTasks(projectId),
        listFindings(projectId),
        listReports(projectId),
        listAuditEvents(projectId, 12),
      ]);
      if (requestId !== requestIdRef.current) return;
      setTasks(t);
      setFindings(f);
      setReports(r);
      setEvents(a);
      setState("ready");
    } catch (err) {
      if (requestId !== requestIdRef.current) return;
      setError(err instanceof ApiError ? err.message : "Veriler yüklenemedi.");
      setState("error");
    }
  }

  useEffect(() => {
    if (activeProject) load(activeProject.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeProject?.id]);

  async function handleApprove(taskId: string) {
    setApprovingId(taskId);
    try {
      const updated = await approveTask(taskId);
      setTasks((prev) => prev.map((t) => (t.id === taskId ? updated : t)));
      if (activeProject) {
        const requestId = requestIdRef.current;
        listAuditEvents(activeProject.id, 12)
          .then((a) => {
            if (requestId === requestIdRef.current) setEvents(a);
          })
          .catch(() => {});
      }
    } catch {
      // Hata olsa bile liste değişmez; kullanıcı tekrar deneyebilir.
    } finally {
      setApprovingId(null);
    }
  }

  const awaitingApproval = tasks.filter((t) => t.status === "awaiting_approval");
  const findingStatusCounts = findings.reduce(
    (acc, f) => ({ ...acc, [f.status]: (acc[f.status] ?? 0) + 1 }),
    {} as Record<string, number>
  );
  const confirmedRiskCounts = findings
    .filter((f) => f.status === "confirmed" && f.risk_level)
    .reduce(
      (acc, f) => ({ ...acc, [f.risk_level as string]: (acc[f.risk_level as string] ?? 0) + 1 }),
      {} as Record<string, number>
    );
  const maxStatusCount = Math.max(1, ...FINDING_STATUS_ORDER.map((s) => findingStatusCounts[s] ?? 0));

  return (
    <div className="flex h-screen flex-col bg-paper text-ink">
      <header className="flex items-center justify-between gap-4 border-b border-slate-line/20 bg-paper-raised px-4 py-3 sm:px-6">
        <div className="flex items-center gap-1 rounded-sm border border-slate-line/30 p-0.5">
          <button
            type="button"
            onClick={onSwitchView}
            className="rounded-sm px-3 py-1 font-sans text-sm text-ink/70 hover:bg-paper"
          >
            Stüdyo
          </button>
          <button
            type="button"
            className="rounded-sm bg-ink px-3 py-1 font-sans text-sm text-paper"
          >
            Kontrol paneli
          </button>
        </div>
        <button
          type="button"
          onClick={onLogout}
          className="hidden font-sans text-sm text-slate-muted hover:text-ink sm:inline-block"
        >
          Çıkış yap
        </button>
      </header>

      <div className="border-b border-slate-line/20 bg-paper-raised px-4 py-4 sm:px-6">
        <div className="max-w-xs">
          <ProjectPicker activeProject={activeProject} onSelect={onSelectProject} />
        </div>
      </div>

      <main className="flex-1 overflow-y-auto">
        {!activeProject && (
          <div className="p-6">
            <p className="font-sans text-sm text-slate-muted">
              Kontrol panelini görmek için bir proje seçin veya oluşturun.
            </p>
          </div>
        )}

        {activeProject && state === "loading" && (
          <div className="p-6">
            <p className="animate-pulse font-sans text-sm text-slate-muted">Yükleniyor…</p>
          </div>
        )}

        {activeProject && state === "error" && (
          <div className="p-6">
            <p className="font-sans text-sm text-signal-critical">{error}</p>
            <button
              type="button"
              onClick={() => load(activeProject.id)}
              className="mt-2 font-sans text-xs text-ink underline underline-offset-2"
            >
              Tekrar dene
            </button>
          </div>
        )}

        {activeProject && state === "ready" && (
          <div className="grid gap-6 p-4 sm:p-6 lg:grid-cols-[1.4fr_1fr]">
            {/* Onay bekleyen görevler — en çok ağırlık taşıyan bölge: aksiyon gerektirir */}
            <section className="border-l-2 border-signal-high/60 bg-paper-raised p-5">
              <h2 className="mb-1 font-serif text-lg text-ink">Onay bekleyen görevler</h2>
              <p className="mb-4 font-sans text-xs text-slate-muted">
                Aktif test gerektiren her görev, çalışmadan önce burada onay bekler.
              </p>
              {awaitingApproval.length === 0 ? (
                <p className="font-sans text-sm text-slate-muted">
                  Onay bekleyen görev yok. Yeni bir görev oluşturduğunuzda burada görünecek.
                </p>
              ) : (
                <ul className="space-y-2">
                  {awaitingApproval.map((task) => (
                    <li
                      key={task.id}
                      className="flex items-center justify-between gap-3 border-b border-slate-line/15 py-2.5"
                    >
                      <div className="min-w-0">
                        <p className="truncate font-sans text-sm text-ink">{task.title}</p>
                        <p className="font-mono text-xs text-slate-muted">{task.agent_role}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleApprove(task.id)}
                        disabled={approvingId === task.id}
                        className="flex-shrink-0 rounded-sm bg-ink px-3 py-1.5 font-sans text-xs text-paper hover:bg-ink-soft disabled:opacity-50"
                      >
                        {approvingId === task.id ? "…" : "Onayla"}
                      </button>
                    </li>
                  ))}
                </ul>
              )}

              {tasks.length > awaitingApproval.length && (
                <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1 border-t border-slate-line/15 pt-3">
                  {(
                    ["pending", "running", "completed", "failed", "rejected"] as const
                  ).map((s) => {
                    const count = tasks.filter((t) => t.status === s).length;
                    if (count === 0) return null;
                    return (
                      <p key={s} className="font-sans text-xs text-slate-muted">
                        {TASK_STATUS_LABELS[s]}: <span className="text-ink">{count}</span>
                      </p>
                    );
                  })}
                </div>
              )}
            </section>

            <div className="space-y-6">
              {/* Bulgu durumu — olgunluk sırası, tek renk açıklık kademesi */}
              <section className="bg-paper-raised p-5">
                <h2 className="mb-3 font-serif text-base text-ink">Bulgu durumu</h2>
                {findings.length === 0 ? (
                  <p className="font-sans text-sm text-slate-muted">Henüz bulgu kaydı yok.</p>
                ) : (
                  <div className="space-y-2">
                    {FINDING_STATUS_ORDER.map((s) => {
                      const count = findingStatusCounts[s] ?? 0;
                      return (
                        <div key={s} className="flex items-center gap-2">
                          <span className="w-24 flex-shrink-0 font-sans text-xs text-slate-muted">
                            {FINDING_STATUS_LABELS[s]}
                          </span>
                          <div className="h-2 flex-1 overflow-hidden rounded-sm bg-ink/[0.06]">
                            <div
                              className={`h-full ${FINDING_STATUS_OPACITY[s]}`}
                              style={{ width: `${(count / maxStatusCount) * 100}%` }}
                            />
                          </div>
                          <span className="w-5 flex-shrink-0 text-right font-mono text-xs text-ink">
                            {count}
                          </span>
                        </div>
                      );
                    })}
                    {(findingStatusCounts.false_positive || findingStatusCounts.remediated_pending_retest) && (
                      <p className="pt-1 font-sans text-xs text-slate-muted">
                        {findingStatusCounts.false_positive ? (
                          <>Yanlış pozitif: {findingStatusCounts.false_positive}</>
                        ) : null}
                        {findingStatusCounts.false_positive &&
                        findingStatusCounts.remediated_pending_retest
                          ? " · "
                          : ""}
                        {findingStatusCounts.remediated_pending_retest ? (
                          <>Yeniden test bekliyor: {findingStatusCounts.remediated_pending_retest}</>
                        ) : null}
                      </p>
                    )}
                  </div>
                )}

                {Object.keys(confirmedRiskCounts).length > 0 && (
                  <dl className="mt-4 flex flex-wrap items-center gap-4 border-t border-slate-line/15 pt-3">
                    {RISK_ORDER.filter((r) => confirmedRiskCounts[r]).map((r) => (
                      <div key={r} className="flex items-center gap-1.5">
                        <span className={`h-2 w-2 rounded-full ${RISK_DOT[r]}`} aria-hidden />
                        <dt className="font-sans text-xs text-slate-muted">{RISK_LABELS[r]}</dt>
                        <dd className="font-sans text-xs font-medium text-ink">
                          {confirmedRiskCounts[r]}
                        </dd>
                      </div>
                    ))}
                  </dl>
                )}
              </section>

              {/* Son raporlar */}
              <section className="bg-paper-raised p-5">
                <h2 className="mb-3 font-serif text-base text-ink">Raporlar</h2>
                {reports.length === 0 ? (
                  <p className="font-sans text-sm text-slate-muted">
                    Henüz kaydedilmiş rapor yok. Stüdyo'da bir şablonu kaydedin.
                  </p>
                ) : (
                  <ul className="space-y-1.5">
                    {reports.map((r) => (
                      <li key={r.id} className="font-sans text-sm text-ink">
                        {r.template}
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              {/* Son etkinlik */}
              <section className="bg-paper-raised p-5">
                <h2 className="mb-3 font-serif text-base text-ink">Son etkinlik</h2>
                {events.length === 0 ? (
                  <p className="font-sans text-sm text-slate-muted">Henüz etkinlik yok.</p>
                ) : (
                  <ul className="space-y-2.5">
                    {events.map((e) => (
                      <li key={e.id} className="font-sans text-xs">
                        <span className="text-ink">{e.actor}</span>{" "}
                        <span className="text-slate-muted">
                          {ACTION_LABELS[e.action] ?? e.action}
                        </span>
                        <span className="ml-2 font-mono text-slate-muted">
                          {formatDate(e.created_at)}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
