const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8010/api";

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "content-type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiError(
      "Backend'e ulaşılamadı. Sunucunun çalıştığından ve adresin doğru olduğundan emin olun."
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(body?.detail ?? `İstek başarısız oldu (${response.status}).`);
  }
  return response.json() as Promise<T>;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  is_archived: boolean;
}

export function listProjects(): Promise<Project[]> {
  return request<Project[]>("/projects");
}

export function createProject(input: {
  name: string;
  description?: string;
  scope_definition?: Record<string, unknown>;
}): Promise<Project> {
  return request<Project>("/projects", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export interface AiDraftResponse {
  draft: string;
  available: boolean;
}

export function requestAiDraft(input: {
  instruction: string;
  section_text: string;
}): Promise<AiDraftResponse> {
  return request<AiDraftResponse>("/ai/draft", {
    method: "POST",
    body: JSON.stringify(input),
  });
}
