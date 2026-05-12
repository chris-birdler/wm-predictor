import { useState } from "react";
import type { Match, Prediction, Team } from "../types";
import { MatchCard } from "./MatchCard";
import { api } from "../api/client";

interface Props {
  group: string;
  teams: Team[];
  matches: Match[];
}

export function GroupCard({ group, teams, matches }: Props) {
  const [preds, setPreds] = useState<Record<number, Prediction>>({});
  const [busy, setBusy] = useState(false);

  const handlePredictGroup = async () => {
    setBusy(true);
    try {
      const result = await api.predictGroup(group);
      const next: Record<number, Prediction> = {};
      for (const p of result) next[p.match_id] = p;
      setPreds(next);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-xl bg-slate-900/70 p-4 ring-1 ring-slate-800">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-xl font-bold">Gruppe {group}</h2>
        <button
          onClick={handlePredictGroup}
          disabled={busy}
          className="rounded bg-accent px-3 py-1 text-sm font-semibold text-slate-900 hover:bg-cyan-300 disabled:opacity-50"
        >
          Gruppe tippen
        </button>
      </div>
      <table className="mb-3 w-full text-sm">
        <thead className="text-xs text-slate-400">
          <tr>
            <th className="text-left">Team</th>
            <th>Elo</th>
          </tr>
        </thead>
        <tbody>
          {teams.map((t) => (
            <tr key={t.id} className="border-t border-slate-800">
              <td className="py-1">{t.name}</td>
              <td className="text-center text-slate-300">{Math.round(t.elo)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="space-y-2">
        {matches.map((m) => (
          <MatchCard
            key={m.id}
            match={m}
            prediction={preds[m.id]}
            onPredict={(p) => setPreds((s) => ({ ...s, [m.id]: p }))}
          />
        ))}
      </div>
    </div>
  );
}
