import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import { Bracket } from "../components/Bracket";
import type { Match } from "../types";

const STAGES = ["r32", "r16", "qf", "sf", "final"] as const;

export default function Playoffs() {
  const q = useQuery({
    queryKey: ["matches", "all"],
    queryFn: () => api.matches({}),
  });
  const [busy, setBusy] = useState<string | null>(null);

  const matchesByStage: Record<string, Match[]> = {};
  for (const m of q.data ?? []) {
    if (STAGES.includes(m.stage as typeof STAGES[number])) {
      (matchesByStage[m.stage] ??= []).push(m);
    }
  }

  const handleStage = async (stage: string) => {
    setBusy(stage);
    try {
      await api.predictStage(stage);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold">K.o.-Runde</h1>
      <div className="flex flex-wrap gap-2">
        {STAGES.map((s) => (
          <button
            key={s}
            onClick={() => handleStage(s)}
            disabled={busy === s}
            className="rounded bg-slate-800 px-3 py-1.5 text-sm hover:bg-slate-700 disabled:opacity-50"
          >
            {s.toUpperCase()} tippen
          </button>
        ))}
      </div>
      <Bracket matchesByStage={matchesByStage} />
    </div>
  );
}
