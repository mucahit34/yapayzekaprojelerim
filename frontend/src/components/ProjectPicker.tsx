import { useEffect, useRef, useState } from "react";
import { ApiError, createProject, listProjects, type Project } from "../api/client";

interface ProjectPickerProps {
  activeProject: Project | null;
  onSelect: (project: Project) => void;
}

type LoadState = "loading" | "error" | "empty" | "ready";

export function ProjectPicker({ activeProject, onSelect }: ProjectPickerProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [state, setState] = useState<LoadState>("loading");
  const [errorMessage, setErrorMessage] = useState("");
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");

  // load() yalnızca mount'ta çağrılır ama bir sonraki render'da ebeveynin
  // activeProject'i değişmiş olabilir; closure'daki eski değeri değil,
  // her zaman güncel değeri okumak için ref kullanıyoruz.
  const activeProjectRef = useRef(activeProject);
  activeProjectRef.current = activeProject;

  async function load() {
    setState("loading");
    try {
      const data = await listProjects();
      setProjects(data);
      if (data.length === 0) {
        setState("empty");
      } else {
        setState("ready");
        if (!activeProjectRef.current) onSelect(data[0]);
      }
    } catch (err) {
      setErrorMessage(err instanceof ApiError ? err.message : "Beklenmeyen bir hata oluştu.");
      setState("error");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate() {
    if (!newName.trim()) return;
    try {
      const project = await createProject({ name: newName.trim() });
      setNewName("");
      setCreating(false);
      setProjects((prev) => [...prev, project]);
      setState("ready");
      onSelect(project);
    } catch (err) {
      setErrorMessage(err instanceof ApiError ? err.message : "Proje oluşturulamadı.");
      setState("error");
    }
  }

  if (state === "loading") {
    return (
      <div className="px-5 py-4">
        <p className="font-sans text-xs text-slate-muted">Proje</p>
        <p className="mt-1 animate-pulse font-sans text-sm text-slate-muted">Yükleniyor…</p>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="px-5 py-4">
        <p className="font-sans text-xs text-slate-muted">Proje</p>
        <p className="mt-1 font-sans text-sm text-signal-critical">{errorMessage}</p>
        <button
          type="button"
          onClick={load}
          className="mt-2 font-sans text-xs text-ink underline underline-offset-2 hover:text-ink/70"
        >
          Tekrar dene
        </button>
      </div>
    );
  }

  return (
    <div className="px-5 py-4">
      <p className="mb-1 font-sans text-xs text-slate-muted">Proje</p>

      {state === "empty" && !creating && (
        <p className="mb-2 font-sans text-sm text-slate-muted">Henüz proje yok.</p>
      )}

      {state === "ready" && activeProject && (
        <select
          value={activeProject.id}
          onChange={(e) => {
            const project = projects.find((p) => p.id === e.target.value);
            if (project) onSelect(project);
          }}
          className="w-full rounded-sm border border-slate-line/30 bg-paper px-2 py-1.5 font-serif text-base text-ink"
        >
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      )}

      {creating ? (
        <div className="mt-2 flex gap-1.5">
          <input
            autoFocus
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            placeholder="Proje adı"
            className="min-w-0 flex-1 rounded-sm border border-slate-line/30 bg-paper px-2 py-1.5 font-sans text-sm"
          />
          <button
            type="button"
            onClick={handleCreate}
            className="rounded-sm bg-ink px-2.5 py-1.5 font-sans text-xs text-paper"
          >
            Ekle
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setCreating(true)}
          className="mt-2 font-sans text-xs text-ink/70 underline underline-offset-2 hover:text-ink"
        >
          + Yeni proje
        </button>
      )}
    </div>
  );
}
