import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import type { TeamProbs } from "../types";
import { flagEmoji } from "../utils/flag";

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
    Champion: +(t.p_winner * 100).toFixed(1),
    Final: +(t.p_final * 100).toFixed(1),
    Semifinal: +(t.p_sf * 100).toFixed(1),
  }));

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-end justify-between gap-4 border-b border-fifa-line pb-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-fifa-pink">
            Monte Carlo
          </p>
          <h1 className="mt-1 font-display text-4xl font-extrabold tracking-tight text-fifa-ink">
            Simulation
          </h1>
          <p className="mt-2 max-w-xl text-sm text-fifa-dim">
            Each run samples 72 group matches and the full knockout from the
            ensemble model. Probabilities aggregate over {n.toLocaleString()} runs.
          </p>
        </div>
        <div className="flex items-end gap-3">
          <label className="text-xs">
            <div className="mb-1 font-semibold uppercase tracking-wider text-fifa-muted">
              Runs
            </div>
            <input
              type="number"
              value={n}
              onChange={(e) => setN(Number(e.target.value))}
              min={100}
              max={100000}
              step={500}
              className="w-32 rounded-md border border-fifa-line bg-fifa-surface px-3 py-1.5 text-sm tabular-nums focus:border-fifa-pink focus:outline-none"
            />
          </label>
          <button
            onClick={run}
            disabled={busy}
            className="rounded-md bg-fifa-pink px-5 py-2.5 font-display text-sm font-bold uppercase tracking-wide text-white shadow-sm transition hover:bg-fifa-magenta disabled:opacity-50"
          >
            {busy ? "Running…" : "Run simulation"}
          </button>
        </div>
      </section>
      {results.length > 0 && (
        <>
          <div className="h-96 rounded-2xl border border-fifa-line bg-fifa-surface p-4 shadow-sm">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={top} margin={{ top: 12, right: 16, left: 0, bottom: 8 }}>
                <CartesianGrid stroke="#E5E7EB" strokeDasharray="3 3" />
                <XAxis dataKey="name" stroke="#6B7280" />
                <YAxis stroke="#6B7280" unit="%" />
                <Tooltip
                  contentStyle={{
                    background: "#FFFFFF",
                    border: "1px solid #E5E7EB",
                    borderRadius: 8,
                    color: "#0A0A0F",
                  }}
                />
                <Bar dataKey="Semifinal" fill="#00BEC8" radius={[3, 3, 0, 0]} />
                <Bar dataKey="Final" fill="#00875A" radius={[3, 3, 0, 0]} />
                <Bar dataKey="Champion" fill="#E5007E" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="overflow-hidden rounded-2xl border border-fifa-line bg-fifa-surface shadow-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-fifa-line text-[10px] uppercase tracking-wider text-fifa-muted">
                  <th className="px-4 py-3 text-left font-semibold">Team</th>
                  <th className="px-3 py-3 text-center font-semibold">R32</th>
                  <th className="px-3 py-3 text-center font-semibold">R16</th>
                  <th className="px-3 py-3 text-center font-semibold">QF</th>
                  <th className="px-3 py-3 text-center font-semibold">SF</th>
                  <th className="px-3 py-3 text-center font-semibold">Final</th>
                  <th className="px-3 py-3 text-center font-semibold">Champion</th>
                </tr>
              </thead>
              <tbody>
                {results.map((t) => (
                  <tr key={t.team_id} className="border-b border-fifa-line/60 last:border-b-0 hover:bg-fifa-page/60">
                    <td className="px-4 py-2 font-medium">
                      <span className="flex items-center gap-2">
                        <span className="text-base leading-none">{flagEmoji(t.fifa_code)}</span>
                        <span className="text-fifa-ink">{t.name}</span>
                      </span>
                    </td>
                    <td className="px-3 py-2 text-center tabular-nums text-fifa-dim">
                      {(t.p_advance_group * 100).toFixed(1)}%
                    </td>
                    <td className="px-3 py-2 text-center tabular-nums text-fifa-dim">
                      {(t.p_r16 * 100).toFixed(1)}%
                    </td>
                    <td className="px-3 py-2 text-center tabular-nums text-fifa-dim">
                      {(t.p_qf * 100).toFixed(1)}%
                    </td>
                    <td className="px-3 py-2 text-center tabular-nums text-fifa-dim">
                      {(t.p_sf * 100).toFixed(1)}%
                    </td>
                    <td className="px-3 py-2 text-center tabular-nums text-fifa-ink">
                      {(t.p_final * 100).toFixed(1)}%
                    </td>
                    <td className="px-3 py-2 text-center font-display text-base font-bold tabular-nums text-fifa-pink">
                      {(t.p_winner * 100).toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
