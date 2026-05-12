import type { Match } from "../types";
import { MatchCard } from "./MatchCard";

interface Props {
  matchesByStage: Record<string, Match[]>;
}

const STAGES: { key: string; label: string }[] = [
  { key: "r32", label: "Round of 32" },
  { key: "r16", label: "Achtelfinale" },
  { key: "qf", label: "Viertelfinale" },
  { key: "sf", label: "Halbfinale" },
  { key: "final", label: "Finale" },
];

export function Bracket({ matchesByStage }: Props) {
  return (
    <div className="flex gap-6 overflow-x-auto pb-4">
      {STAGES.map(({ key, label }) => (
        <div key={key} className="min-w-[280px] flex-1">
          <h3 className="mb-2 text-center text-sm font-semibold uppercase tracking-wide text-slate-400">
            {label}
          </h3>
          <div className="space-y-3">
            {(matchesByStage[key] ?? []).map((m) => (
              <MatchCard key={m.id} match={m} />
            ))}
            {!matchesByStage[key]?.length && (
              <div className="rounded border border-dashed border-slate-700 p-4 text-center text-xs text-slate-500">
                noch keine Paarungen
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
