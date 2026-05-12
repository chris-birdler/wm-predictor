import { useState } from "react";
import { api } from "../api/client";
import type { Match, Prediction } from "../types";
import { flagEmoji } from "../utils/flag";

interface Props {
  match: Match;
  prediction?: Prediction;
  onPredict?: (p: Prediction) => void;
}

function probBar(p_home: number, p_draw: number, p_away: number) {
  const h = Math.round(p_home * 100);
  const d = Math.round(p_draw * 100);
  const a = Math.round(p_away * 100);
  return (
    <div className="mt-2 space-y-1">
      <div className="flex h-1.5 overflow-hidden rounded-full bg-fifa-chip">
        <div className="bg-fifa-green" style={{ width: `${h}%` }} title={`Home ${h}%`} />
        <div className="bg-fifa-muted" style={{ width: `${d}%` }} title={`Draw ${d}%`} />
        <div className="bg-fifa-pink" style={{ width: `${a}%` }} title={`Away ${a}%`} />
      </div>
      <div className="flex justify-between text-[10px] font-semibold tabular-nums text-fifa-muted">
        <span>{h}%</span>
        <span>{d}%</span>
        <span>{a}%</span>
      </div>
    </div>
  );
}

export function MatchCard({ match, prediction, onPredict }: Props) {
  const [busy, setBusy] = useState(false);

  const handlePredict = async () => {
    setBusy(true);
    try {
      const p = await api.predictMatch(match.id);
      onPredict?.(p);
    } finally {
      setBusy(false);
    }
  };

  const hasActual = match.is_finished && match.home_score != null && match.away_score != null;
  const homeScore = hasActual
    ? match.home_score
    : prediction
      ? prediction.predicted_score[0]
      : null;
  const awayScore = hasActual
    ? match.away_score
    : prediction
      ? prediction.predicted_score[1]
      : null;

  const statusLabel = hasActual ? "Result" : prediction ? "Predicted" : "Scheduled";
  const statusColor = hasActual
    ? "text-fifa-green"
    : prediction
      ? "text-fifa-pink"
      : "text-fifa-muted";

  return (
    <div className="rounded-lg border border-fifa-line bg-fifa-surface px-3 py-2 transition hover:border-fifa-ink/20">
      <div className="flex items-center gap-3">
        <div className="flex flex-1 items-center justify-end gap-2 truncate">
          <span className="truncate text-sm font-semibold text-fifa-ink">
            {match.home.name}
          </span>
          <span className="text-base leading-none">{flagEmoji(match.home.fifa_code)}</span>
        </div>
        <div className="flex w-20 items-center justify-center gap-2 rounded-md bg-fifa-chip px-2 py-1.5 font-display text-base font-bold tabular-nums text-fifa-ink">
          <span className="min-w-[1ch] text-center">{homeScore ?? "–"}</span>
          <span className="text-fifa-muted">:</span>
          <span className="min-w-[1ch] text-center">{awayScore ?? "–"}</span>
        </div>
        <div className="flex flex-1 items-center gap-2 truncate">
          <span className="text-base leading-none">{flagEmoji(match.away.fifa_code)}</span>
          <span className="truncate text-sm font-semibold text-fifa-ink">
            {match.away.name}
          </span>
        </div>
      </div>
      {prediction && probBar(prediction.p_home, prediction.p_draw, prediction.p_away)}
      <div className="mt-2 flex items-center gap-2 text-xs">
        <button
          onClick={handlePredict}
          disabled={busy}
          className="rounded-md border border-fifa-line bg-fifa-page px-2.5 py-1 font-semibold text-fifa-ink hover:border-fifa-pink hover:text-fifa-pink disabled:opacity-50"
        >
          {busy ? "…" : prediction ? "Re-predict" : "Predict"}
        </button>
        <span className={`text-[10px] font-bold uppercase tracking-wide ${statusColor}`}>
          {statusLabel}
        </span>
        <span className="ml-auto text-fifa-muted">
          {new Date(match.kickoff).toLocaleString("en-US", {
            month: "short",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>
    </div>
  );
}
