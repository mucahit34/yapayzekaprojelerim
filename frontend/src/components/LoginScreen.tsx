import { useState } from "react";
import { ApiError, login, register } from "../api/client";

interface LoginScreenProps {
  onAuthenticated: () => void;
}

export function LoginScreen({ onAuthenticated }: LoginScreenProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (mode === "register") {
        await register({ email, password });
      }
      await login(email, password);
      onAuthenticated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Beklenmeyen bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-screen items-center justify-center bg-paper px-4">
      <div className="w-full max-w-sm rounded-sm border border-slate-line/20 bg-paper-raised p-8 shadow-[0_1px_2px_rgba(20,24,31,0.08),0_12px_32px_rgba(20,24,31,0.08)]">
        <p className="font-serif text-2xl text-ink">Rapor Stüdyosu</p>
        <p className="mb-6 font-sans text-sm text-slate-muted">
          {mode === "login"
            ? "Devam etmek için giriş yapın."
            : "İlk kurulum: bu kişisel asistan için tek hesabı oluşturun."}
        </p>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label htmlFor="email" className="mb-1 block font-sans text-xs text-slate-muted">
              E-posta
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-sm border border-slate-line/30 bg-paper px-3 py-2 font-sans text-sm text-ink focus:border-slate-line focus:outline-none"
            />
          </div>
          <div>
            <label htmlFor="password" className="mb-1 block font-sans text-xs text-slate-muted">
              Parola {mode === "register" && "(en az 10 karakter)"}
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={mode === "register" ? 10 : undefined}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-sm border border-slate-line/30 bg-paper px-3 py-2 font-sans text-sm text-ink focus:border-slate-line focus:outline-none"
            />
          </div>

          {error && <p className="font-sans text-sm text-signal-critical">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-sm bg-ink px-3 py-2 font-sans text-sm text-paper hover:bg-ink-soft disabled:opacity-50"
          >
            {loading ? "…" : mode === "login" ? "Giriş yap" : "Hesabı oluştur ve giriş yap"}
          </button>
        </form>

        <button
          type="button"
          onClick={() => {
            setMode(mode === "login" ? "register" : "login");
            setError("");
          }}
          className="mt-4 font-sans text-xs text-ink/70 underline underline-offset-2 hover:text-ink"
        >
          {mode === "login" ? "İlk kurulum: hesap oluştur" : "Zaten hesabım var, giriş yap"}
        </button>
      </div>
    </div>
  );
}
