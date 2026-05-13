import type { Match, Prediction } from "../types";
import { MatchCard } from "./MatchCard";

interface Props {
  matchesByStage: Record<string, Match[]>;
  predictions: Record<number, Prediction>;
  onPredictions: (preds: Prediction[]) => void;
  expectedSlots: Record<string, number>;
  // When false, render every slot as a placeholder regardless of seeded matches.
  // Used to keep the knockout bracket blank until group standings are complete.
  groupsComplete: boolean;
}

const STAGES: { key: string; label: string; sub: string }[] = [
  { key: "r32", label: "Round of 32", sub: "16 matches" },
  { key: "r16", label: "Round of 16", sub: "8 matches" },
  { key: "qf", label: "Quarter-finals", sub: "4 matches" },
  { key: "sf", label: "Semi-finals", sub: "2 matches" },
  { key: "third", label: "Third place", sub: "1 match" },
  { key: "final", label: "Final", sub: "1 match" },
];

function PlaceholderSlot({ index }: { index: number }) {
  return (
    <div className="rounded-lg border border-dashed border-fifa-line bg-fifa-surface px-3 py-3 text-xs text-fifa-muted">
      <div className="flex items-center justify-between">
        <span className="font-semibold uppercase tracking-wide">Match {index + 1}</span>
        <span className="rounded-full bg-fifa-chip px-2 py-0.5 text-[10px] uppercase tracking-wide">
          TBD
        </span>
      </div>
      <div className="mt-2 flex items-center justify-between">
        <span>—</span>
        <span className="font-display text-base font-bold text-fifa-muted">–:–</span>
        <span>—</span>
      </div>
    </div>
  );
}

export function Bracket({
  matchesByStage,
  predictions,
  onPredictions,
  expectedSlots,
  groupsComplete,
}: Props) {
  return (
    <div className="overflow-x-auto pb-6">
      <div className="flex min-w-max gap-5">
        {STAGES.map(({ key, label, sub }) => {
          const matches = groupsComplete ? matchesByStage[key] ?? [] : [];
          const expected = expectedSlots[key] ?? matches.length;
          const placeholders = Math.max(0, expected - matches.length);
          return (
            <div key={key} className="w-72 flex-shrink-0">
              <div className="mb-3 border-b border-fifa-line pb-2">
                <h3 className="font-display text-sm font-bold uppercase tracking-wider text-fifa-ink">
                  {label}
                </h3>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-fifa-muted">
                  {sub}
                </p>
              </div>
              <div className="space-y-3">
                {matches.map((m) => (
                  <MatchCard
                    key={m.id}
                    match={m}
                    prediction={predictions[m.id]}
                    onPredict={(p) => onPredictions([p])}
                  />
                ))}
                {Array.from({ length: placeholders }).map((_, i) => (
                  <PlaceholderSlot key={`ph-${i}`} index={matches.length + i} />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
