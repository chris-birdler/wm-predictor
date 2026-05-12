import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import type { TeamProbs } from "../types";

export default function Simulation() {
  const [results, setResults] = useState<TeamProbs[]>([]);
  const [busy, setBusy] = useState(false);
  const [n, setN] = useState(10000);

  const run = async () => {
    setBusy(true);
    try {
      const resp = await api.runSimulation(n);
      setResults(resp.teams);
    } finally {
      setBusy(false);
    }
  };

  const top = results.slice(0, 16).map((t) => ({
    name: t.fifa_code,
    Weltmeister: +(t.p_winner * 100).toFixed(1),
    Finale: +(t.p_final * 100).toFixed(1),
    Halbfinale: +(t.p_sf * 100).toFixed(1),
  }));

  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold">Monte-Carlo-Simulation</h1>
      <div className="flex items-end gap-3">
        <label className="text-sm">
          Anzahl Läufe
          <input
            type="number"
            value={n}
            onChange={(e) => setN(Number(e.target.value))}
            min={100}
            max={100000}
            step={500}
            className="ml-2 w-28 rounded bg-slate-900 px-2 py-1"
          />
        </label>
        <button
          onClick={run}
          disabled={busy}
          className="rounded bg-accent px-4 py-2 font-semibold text-slate-900 hover:bg-cyan-300 disabled:opacity-50"
        >
          {busy ? "läuft..." : "Simulation starten"}
        </button>
      </div>
      {results.length > 0 && (
        <>
          <div className="h-96 rounded-xl bg-slate-900/70 p-4 ring-1 ring-slate-800">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={top}>
                <CartesianGrid stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" unit="%" />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
                <Bar dataKey="Halbfinale" fill="#64748b" />
                <Bar dataKey="Finale" fill="#94a3b8" />
                <Bar dataKey="Weltmeister" fill="#22d3ee" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <table className="w-full text-sm">
            <thead className="text-xs text-slate-400">
              <tr>
                <th className="text-left">Team</th>
                <th>R32</th>
                <th>R16</th>
                <th>VF</th>
                <th>HF</th>
                <th>Finale</th>
                <th>Weltmeister</th>
              </tr>
            </thead>
            <tbody>
              {results.map((t) => (
                <tr key={t.team_id} className="border-t border-slate-800">
                  <td className="py-1">{t.name}</td>
                  <td className="text-center">{(t.p_advance_group * 100).toFixed(1)}%</td>
                  <td className="text-center">{(t.p_r16 * 100).toFixed(1)}%</td>
                  <td className="text-center">{(t.p_qf * 100).toFixed(1)}%</td>
                  <td className="text-center">{(t.p_sf * 100).toFixed(1)}%</td>
                  <td className="text-center">{(t.p_final * 100).toFixed(1)}%</td>
                  <td className="text-center font-bold text-accent">
                    {(t.p_winner * 100).toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
