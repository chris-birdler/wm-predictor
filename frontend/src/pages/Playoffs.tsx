import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import { Bracket } from "../components/Bracket";
import type { Match, Prediction } from "../types";

const STAGES = ["r32", "r16", "qf", "sf", "third", "final"] as const;

const STAGE_LABEL: Record<string, string> = {
  r32: "R32",
  r16: "R16",
  qf: "QF",
  sf: "SF",
  third: "3rd",
  final: "Final",
};

const EXPECTED_SLOTS: Record<string, number> = {
  r32: 16,
  r16: 8,
  qf: 4,
  sf: 2,
  third: 1,
  final: 1,
};

export default function Playoffs() {
  const q = useQuery({ queryKey: ["matches", "all"], queryFn: () => api.matches({}) });
  const [busy, setBusy] = useState<string | null>(null);
  const [predictions, setPredictions] = useState<Record<number, Prediction>>({});

  const mergePredictions = (preds: Prediction[]) =>
    setPredictions((prev) => {
      const next = { ...prev };
      for (const p of preds) next[p.match_id] = p;
      return next;
    });

  const matchesByStage: Record<string, Match[]> = {};
  for (const m of q.data ?? []) {
    if (STAGES.includes(m.stage as (typeof STAGES)[number])) {
      (matchesByStage[m.stage] ??= []).push(m);
    }
  }

  const handleStage = async (stage: string) => {
    setBusy(stage);
    try {
      const result = await api.predictStage(stage);
      mergePredictions(result);
    } finally {
      setBusy(null);
    }
  };

  const knockoutMatchesCount = STAGES.reduce(
    (acc, s) => acc + (matchesByStage[s]?.length ?? 0),
    0,
  );

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-end justify-between gap-4 border-b border-fifa-line pb-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-fifa-pink">
            Knockout
          </p>
          <h1 className="mt-1 font-display text-4xl font-extrabold tracking-tight text-fifa-ink">
            Bracket
          </h1>
          <p className="mt-2 max-w-xl text-sm text-fifa-dim">
            32 teams enter, one lifts the trophy. Pairings populate from the
            FIFA seeding table once group results are in.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {STAGES.map((s) => (
            <button
              key={s}
              onClick={() => handleStage(s)}
              disabled={busy === s || (matchesByStage[s]?.length ?? 0) === 0}
              className="rounded-md border border-fifa-line bg-fifa-surface px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-fifa-ink transition hover:border-fifa-pink hover:text-fifa-pink disabled:cursor-not-allowed disabled:opacity-40"
              title={
                (matchesByStage[s]?.length ?? 0) === 0 ? "Stage not seeded yet" : ""
              }
            >
              {busy === s ? "…" : `Predict ${STAGE_LABEL[s]}`}
            </button>
          ))}
        </div>
      </section>
      {knockoutMatchesCount === 0 && (
        <p className="rounded-md border border-fifa-line bg-fifa-surface p-4 text-sm text-fifa-dim">
          Knockout pairings haven't been seeded yet. The Monte Carlo simulation
          generates virtual brackets on the fly; once group results are in, the
          Round of 32 populates from the official FIFA slotting table.
        </p>
      )}
      <Bracket
        matchesByStage={matchesByStage}
        predictions={predictions}
        onPredictions={mergePredictions}
        expectedSlots={EXPECTED_SLOTS}
      />
    </div>
  );
}
