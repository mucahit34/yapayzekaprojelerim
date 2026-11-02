const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8010/api";
const TOKEN_KEY = "sec_assistant_token";

export class ApiError extends Error {}

// Token tarayıcının localStorage'ında tutulur — bu tek kullanıcılı,
// yerel/geliştirme amaçlı araç için standart ve pragmatik bir seçim.
// Üretimde çok kullanıcılı bir dağıtım düşünülürse httpOnly cookie +
// CSRF koruması değerlendirilmelidir.
export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // localStorage engellenmiş olabilir (gizli pencere vb.); token bellekte
    // kalmaz ama uygulama en azından bu oturum boyunca çalışmaya devam eder.
  }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // yoksay
  }
}

let unauthorizedHandler: (() => void) | null = null;
export function setUnauthorizedHandler(handler: () => void): void {
  unauthorizedHandler = handler;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "content-type": "application/json",
        ...(token ? { authorization: `Bearer ${token}` } : {}),
      },
      ...init,
    });
  } catch {
    throw new ApiError(
      "Backend'e ulaşılamadı. Sunucunun çalıştığından ve adresin doğru olduğundan emin olun."
    );
  }
  if (response.status === 401) {
    clearToken();
    unauthorizedHandler?.();
    throw new ApiError("Oturum süresi doldu veya geçersiz. Lütfen tekrar giriş yapın.");
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

export interface AuthUser {
  id: string;
  email: string;
  display_name: string | null;
}

export async function register(input: {
  email: string;
  password: string;
  display_name?: string;
}): Promise<AuthUser> {
  return request<AuthUser>("/auth/register", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function login(email: string, password: string): Promise<void> {
  let response: Response;
  const body = new URLSearchParams({ username: email, password });
  try {
    response = await fetch(`${API_BASE_URL}/auth/login`, { method: "POST", body });
  } catch {
    throw new ApiError("Backend'e ulaşılamadı.");
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new ApiError(payload?.detail ?? "Giriş başarısız oldu.");
  }
  const data = (await response.json()) as { access_token: string };
  setToken(data.access_token);
}
