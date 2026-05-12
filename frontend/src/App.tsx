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
      className={`rounded px-3 py-2 text-sm font-medium ${
        active ? "bg-accent text-slate-900" : "text-slate-300 hover:bg-slate-800"
      }`}
    >
      {label}
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
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3">
          <h1 className="text-lg font-bold text-accent">WM 2026</h1>
          <nav className="flex gap-1">
            <NavLink to="/" label="Gruppen" />
            <NavLink to="/playoffs" label="K.o." />
            <NavLink to="/simulation" label="Simulation" />
          </nav>
          <div className="ml-auto">
            {token ? (
              <button
                onClick={logout}
                className="rounded px-3 py-1.5 text-sm text-slate-400 hover:bg-slate-800"
              >
                Logout
              </button>
            ) : (
              <Link to="/login" className="rounded bg-slate-800 px-3 py-1.5 text-sm">
                Login
              </Link>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
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
