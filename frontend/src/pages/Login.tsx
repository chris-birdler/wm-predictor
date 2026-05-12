import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";

export default function Login() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const nav = useNavigate();

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setErr(null);
    try {
      const r =
        mode === "login"
          ? await api.login(username, password)
          : await api.register(username, email, password);
      localStorage.setItem("token", r.access_token);
      nav("/");
    } catch (e: any) {
      setErr(e.message);
    }
  };

  return (
    <form
      onSubmit={submit}
      className="mx-auto max-w-sm space-y-4 rounded-2xl border border-fifa-line bg-fifa-surface p-6 shadow-sm"
    >
      <div className="text-center">
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-fifa-gradient font-display text-base font-black text-white">
          26
        </span>
        <h1 className="mt-3 font-display text-2xl font-extrabold tracking-tight text-fifa-ink">
          {mode === "login" ? "Sign in" : "Create account"}
        </h1>
        <p className="mt-1 text-xs text-fifa-dim">
          {mode === "login"
            ? "Welcome back to the predictor."
            : "Save your predictions across sessions."}
        </p>
      </div>
      <input
        className="w-full rounded-md border border-fifa-line bg-fifa-surface px-3 py-2 text-fifa-ink focus:border-fifa-pink focus:outline-none"
        placeholder="Username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        required
      />
      {mode === "register" && (
        <input
          className="w-full rounded-md border border-fifa-line bg-fifa-surface px-3 py-2 text-fifa-ink focus:border-fifa-pink focus:outline-none"
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      )}
      <input
        className="w-full rounded-md border border-fifa-line bg-fifa-surface px-3 py-2 text-fifa-ink focus:border-fifa-pink focus:outline-none"
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      {err && <p className="text-sm text-fifa-red">{err}</p>}
      <button className="w-full rounded-md bg-fifa-pink px-4 py-2 font-display font-bold uppercase tracking-wide text-white shadow-sm transition hover:bg-fifa-magenta">
        {mode === "login" ? "Sign in" : "Register"}
      </button>
      <button
        type="button"
        onClick={() => setMode(mode === "login" ? "register" : "login")}
        className="block w-full text-center text-sm text-fifa-dim hover:text-fifa-ink"
      >
        {mode === "login"
          ? "No account yet? Register"
          : "Already have an account? Sign in"}
      </button>
    </form>
  );
}
