import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
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
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-fifa-line bg-fifa-surface/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-4 px-4 sm:gap-x-8 sm:px-6">
          <Link to="/" className="flex min-w-0 items-center gap-2 py-3">
            <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-fifa-gradient font-display text-sm font-black text-white">
              26
            </span>
            <span className="truncate font-display text-base font-extrabold tracking-tight text-fifa-ink">
              <span className="hidden sm:inline">
                FIFA World Cup 26™ <span className="font-medium text-fifa-dim">Predictor</span>
              </span>
              <span className="sm:hidden">WC 26 Predictor</span>
            </span>
          </Link>
          <nav className="order-3 -mx-4 ml-auto flex w-[calc(100%+2rem)] justify-around border-t border-fifa-line/60 sm:order-none sm:w-auto sm:flex-none sm:justify-start sm:border-0">
            <NavLink to="/" label="Standings" />
            <NavLink to="/playoffs" label="Knockout" />
            <NavLink to="/simulation" label="Simulation" />
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
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
