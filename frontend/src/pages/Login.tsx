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
    <form onSubmit={submit} className="mx-auto max-w-sm space-y-3 rounded-xl bg-slate-900/70 p-6 ring-1 ring-slate-800">
      <h1 className="text-2xl font-bold">{mode === "login" ? "Anmelden" : "Registrieren"}</h1>
      <input
        className="w-full rounded bg-slate-800 px-3 py-2"
        placeholder="Benutzername"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        required
      />
      {mode === "register" && (
        <input
          className="w-full rounded bg-slate-800 px-3 py-2"
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      )}
      <input
        className="w-full rounded bg-slate-800 px-3 py-2"
        type="password"
        placeholder="Passwort"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      {err && <p className="text-sm text-rose-400">{err}</p>}
      <button className="w-full rounded bg-accent px-4 py-2 font-semibold text-slate-900 hover:bg-cyan-300">
        {mode === "login" ? "Login" : "Registrieren"}
      </button>
      <button
        type="button"
        onClick={() => setMode(mode === "login" ? "register" : "login")}
        className="block w-full text-center text-sm text-slate-400 hover:text-slate-200"
      >
        {mode === "login" ? "Noch kein Account? Registrieren" : "Schon registriert? Login"}
      </button>
    </form>
  );
}
