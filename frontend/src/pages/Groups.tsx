import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import { GroupCard } from "../components/GroupCard";
import type { Prediction } from "../types";

export default function Groups() {
  const teamsQ = useQuery({ queryKey: ["teams-by-group"], queryFn: api.teamsByGroup });
  const matchesQ = useQuery({
    queryKey: ["matches", "group"],
    queryFn: () => api.matches({ stage: "group" }),
  });
  const [busy, setBusy] = useState(false);
  const [predictions, setPredictions] = useState<Record<number, Prediction>>({});

  const mergePredictions = (preds: Prediction[]) =>
    setPredictions((prev) => {
      const next = { ...prev };
      for (const p of preds) next[p.match_id] = p;
      return next;
    });

  const handleAll = async () => {
    setBusy(true);
    try {
      const result = await api.predictAllGroups();
      mergePredictions(result);
    } finally {
      setBusy(false);
    }
  };

  if (teamsQ.isLoading || matchesQ.isLoading) {
    return <p className="py-10 text-center text-sm text-fifa-muted">Loading…</p>;
  }
  if (teamsQ.error || matchesQ.error) {
    return <p className="py-10 text-center text-sm text-fifa-red">Failed to load.</p>;
  }

  const teams = teamsQ.data!;
  const matchesByGroup: Record<string, typeof matchesQ.data> = {};
  for (const m of matchesQ.data ?? []) {
    if (!m.group) continue;
    (matchesByGroup[m.group] ??= []).push(m);
  }

  const predictedCount = Object.keys(predictions).length;
  const totalMatches = matchesQ.data?.length ?? 0;

  return (
    <div className="space-y-8">
      <section className="flex flex-wrap items-end justify-between gap-4 border-b border-fifa-line pb-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-fifa-pink">
            Group stage
          </p>
          <h1 className="mt-1 font-display text-4xl font-extrabold tracking-tight text-fifa-ink">
            Standings
          </h1>
          <p className="mt-2 max-w-xl text-sm text-fifa-dim">
            12 groups, 48 teams. Top two advance plus the eight best
            third-placed teams. Tables auto-update from predicted scorelines.
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="font-display text-2xl font-extrabold tabular-nums text-fifa-ink">
              {predictedCount}
              <span className="text-fifa-muted">/{totalMatches}</span>
            </div>
            <div className="text-[10px] font-semibold uppercase tracking-wide text-fifa-muted">
              matches predicted
            </div>
          </div>
          <button
            onClick={handleAll}
            disabled={busy}
            className="rounded-md bg-fifa-pink px-4 py-2.5 font-display text-sm font-bold uppercase tracking-wide text-white shadow-sm transition hover:bg-fifa-magenta disabled:opacity-50"
          >
            {busy ? "Predicting…" : "Predict all groups"}
          </button>
        </div>
      </section>
      <div className="flex flex-wrap gap-2 text-[11px] font-medium text-fifa-dim">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-full bg-fifa-green" />
          Top 2 — advances
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-full bg-fifa-gold" />
          Best-third candidate
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-full bg-fifa-line" />
          Eliminated
        </span>
      </div>
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        {Object.entries(teams).map(([letter, ts]) => (
          <GroupCard
            key={letter}
            group={letter}
            teams={ts}
            matches={matchesByGroup[letter] ?? []}
            predictions={predictions}
            onPredictions={mergePredictions}
          />
        ))}
      </div>
    </div>
  );
}
