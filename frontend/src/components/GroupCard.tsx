import { useState } from "react";
import { api } from "../api/client";
import type { Match, Prediction, Team } from "../types";
import { flagEmoji } from "../utils/flag";
import { computeStandings } from "../utils/standings";
import { MatchCard } from "./MatchCard";

interface Props {
  group: string;
  teams: Team[];
  matches: Match[];
  predictions: Record<number, Prediction>;
  onPredictions: (preds: Prediction[]) => void;
}

const POS_TAG = [
  { bg: "bg-fifa-green", title: "Advances (top 2)" },
  { bg: "bg-fifa-green", title: "Advances (top 2)" },
  { bg: "bg-fifa-gold", title: "Best-third candidate" },
  { bg: "bg-fifa-line", title: "Eliminated" },
];

export function GroupCard({ group, teams, matches, predictions, onPredictions }: Props) {
  const [busy, setBusy] = useState(false);
  const standings = computeStandings(teams, matches, predictions);

  const handlePredictGroup = async () => {
    setBusy(true);
    try {
      const result = await api.predictGroup(group);
      onPredictions(result);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="overflow-hidden rounded-2xl border border-fifa-line bg-fifa-surface shadow-sm">
      <div className="flex items-center justify-between border-b border-fifa-line px-5 py-4">
        <div className="flex items-baseline gap-3">
          <span className="font-display text-3xl font-black tracking-tight text-fifa-ink">
            {group}
          </span>
          <span className="text-xs font-semibold uppercase tracking-wider text-fifa-dim">
            Group {group}
          </span>
        </div>
        <button
          onClick={handlePredictGroup}
          disabled={busy}
          className="rounded-md bg-fifa-pink px-3 py-1.5 text-xs font-bold uppercase tracking-wide text-white shadow-sm transition hover:bg-fifa-magenta disabled:opacity-50"
        >
          {busy ? "Predicting…" : "Predict group"}
        </button>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-fifa-line text-[10px] uppercase tracking-wider text-fifa-muted">
            <th className="w-6 py-2 pl-5 text-left font-semibold">#</th>
            <th className="py-2 text-left font-semibold">Team</th>
            <th className="w-9 py-2 text-center font-semibold">MP</th>
            <th className="w-9 py-2 text-center font-semibold">W</th>
            <th className="w-9 py-2 text-center font-semibold">D</th>
            <th className="w-9 py-2 text-center font-semibold">L</th>
            <th className="w-10 py-2 text-center font-semibold">GF</th>
            <th className="w-10 py-2 text-center font-semibold">GA</th>
            <th className="w-10 py-2 text-center font-semibold">GD</th>
            <th className="w-10 py-2 pr-5 text-center font-semibold">Pts</th>
          </tr>
        </thead>
        <tbody>
          {standings.map((s, i) => {
            const tag = POS_TAG[i] ?? POS_TAG[3];
            return (
              <tr
                key={s.team.id}
                className="border-b border-fifa-line/60 last:border-b-0 hover:bg-fifa-page/60"
              >
                <td className="py-2 pl-5">
                  <span className="flex items-center gap-2">
                    <span
                      className={`inline-block h-3 w-1 rounded-full ${tag.bg}`}
                      title={tag.title}
                    />
                    <span className="text-xs font-semibold text-fifa-dim">{i + 1}</span>
                  </span>
                </td>
                <td className="py-2">
                  <span className="flex items-center gap-2">
                    <span className="text-base leading-none">
                      {flagEmoji(s.team.fifa_code)}
                    </span>
                    <span className="font-semibold text-fifa-ink">{s.team.name}</span>
                    <span className="rounded bg-fifa-chip px-1.5 py-0.5 font-mono text-[10px] font-bold tracking-wide text-fifa-dim">
                      {s.team.fifa_code}
                    </span>
                  </span>
                </td>
                <td className="py-2 text-center tabular-nums text-fifa-dim">{s.played}</td>
                <td className="py-2 text-center tabular-nums text-fifa-dim">{s.w}</td>
                <td className="py-2 text-center tabular-nums text-fifa-dim">{s.d}</td>
                <td className="py-2 text-center tabular-nums text-fifa-dim">{s.l}</td>
                <td className="py-2 text-center tabular-nums text-fifa-dim">{s.gf}</td>
                <td className="py-2 text-center tabular-nums text-fifa-dim">{s.ga}</td>
                <td className="py-2 text-center tabular-nums text-fifa-dim">
                  {s.gd > 0 ? `+${s.gd}` : s.gd}
                </td>
                <td className="py-2 pr-5 text-center font-display text-base font-bold text-fifa-ink">
                  {s.pts}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="space-y-2 border-t border-fifa-line bg-fifa-page/40 px-3 py-3">
        {matches.map((m) => (
          <MatchCard
            key={m.id}
            match={m}
            prediction={predictions[m.id]}
            onPredict={(p) => onPredictions([p])}
          />
        ))}
      </div>
    </div>
  );
}
