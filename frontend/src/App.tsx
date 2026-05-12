import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import Groups from "./pages/Groups";
import Playoffs from "./pages/Playoffs";
import Simulation from "./pages/Simulation";
import Login from "./pages/Login";

function NavLink({ to, label }: { to: string; label: string }) {
  const { pathname } = useLocation();
  const active = pathname === to;
  return (
    <Link
      to={to}
      className={`relative inline-flex items-center px-3 py-3 text-sm font-semibold transition ${
        active ? "text-fifa-ink" : "text-fifa-dim hover:text-fifa-ink"
      }`}
    >
      {label}
      {active && (
        <span className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-fifa-pink" />
      )}
    </Link>
  );
}

export default function App() {
  const token = localStorage.getItem("token");
  const nav = useNavigate();
  const logout = () => {
    localStorage.removeItem("token");
    nav("/login");
  };

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-fifa-line bg-fifa-surface/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-8 px-6">
          <Link to="/" className="flex items-center gap-2 py-3">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-fifa-gradient font-display text-sm font-black text-white">
              26
            </span>
            <span className="font-display text-base font-extrabold tracking-tight text-fifa-ink">
              FIFA World Cup 26™ <span className="font-medium text-fifa-dim">Predictor</span>
            </span>
          </Link>
          <nav className="flex">
            <NavLink to="/" label="Standings" />
            <NavLink to="/playoffs" label="Knockout" />
            <NavLink to="/simulation" label="Simulation" />
          </nav>
          <div className="ml-auto py-3">
            {token ? (
              <button
                onClick={logout}
                className="rounded-md px-3 py-1.5 text-sm font-medium text-fifa-dim hover:text-fifa-ink"
              >
                Sign out
              </button>
            ) : (
              <Link
                to="/login"
                className="rounded-md border border-fifa-line bg-fifa-surface px-3 py-1.5 text-sm font-semibold text-fifa-ink hover:bg-fifa-chip"
              >
                Sign in
              </Link>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-8">
        <Routes>
          <Route path="/" element={<Groups />} />
          <Route path="/playoffs" element={<Playoffs />} />
          <Route path="/simulation" element={<Simulation />} />
          <Route path="/login" element={<Login />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
