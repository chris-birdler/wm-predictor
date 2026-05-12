import type { Match, Prediction } from "../types";
import { useState } from "react";
import { api } from "../api/client";

interface Props {
  match: Match;
  prediction?: Prediction;
  onPredict?: (p: Prediction) => void;
}

export function MatchCard({ match, prediction, onPredict }: Props) {
  const [busy, setBusy] = useState(false);
  const [tipHome, setTipHome] = useState<number>(prediction?.most_likely_score?.[0] ?? 0);
  const [tipAway, setTipAway] = useState<number>(prediction?.most_likely_score?.[1] ?? 0);

  const handlePredict = async () => {
    setBusy(true);
    try {
      const p = await api.predictMatch(match.id);
      setTipHome(p.most_likely_score[0]);
      setTipAway(p.most_likely_score[1]);
      onPredict?.(p);
    } finally {
      setBusy(false);
    }
  };

  const handleSaveTip = async () => {
    setBusy(true);
    try {
      await api.submitTip(match.id, tipHome, tipAway);
    } finally {
      setBusy(false);
    }
  };

  const probs = prediction
    ? [prediction.p_home, prediction.p_draw, prediction.p_away].map((v) =>
        (v * 100).toFixed(0),
      )
    : null;

  return (
    <div className="rounded-lg bg-slate-800/60 p-3 ring-1 ring-slate-700">
      <div className="flex items-center gap-2">
        <span className="flex-1 truncate text-right text-sm">{match.home.name}</span>
        <input
          type="number"
          className="w-12 rounded bg-slate-900 px-2 py-1 text-center"
          value={tipHome}
          min={0}
          onChange={(e) => setTipHome(Number(e.target.value))}
        />
        <span className="text-xs opacity-60">:</span>
        <input
          type="number"
          className="w-12 rounded bg-slate-900 px-2 py-1 text-center"
          value={tipAway}
          min={0}
          onChange={(e) => setTipAway(Number(e.target.value))}
        />
        <span className="flex-1 truncate text-sm">{match.away.name}</span>
      </div>
      {probs && (
        <div className="mt-2 flex h-1.5 overflow-hidden rounded">
          <div className="bg-emerald-500" style={{ width: `${probs[0]}%` }} title={`Home ${probs[0]}%`} />
          <div className="bg-slate-500" style={{ width: `${probs[1]}%` }} title={`Draw ${probs[1]}%`} />
          <div className="bg-rose-500" style={{ width: `${probs[2]}%` }} title={`Away ${probs[2]}%`} />
        </div>
      )}
      <div className="mt-2 flex gap-2 text-xs">
        <button
          onClick={handlePredict}
          disabled={busy}
          className="rounded bg-accent/20 px-2 py-1 text-accent hover:bg-accent/30 disabled:opacity-50"
        >
          Vorhersage
        </button>
        <button
          onClick={handleSaveTip}
          disabled={busy}
          className="rounded bg-slate-700 px-2 py-1 hover:bg-slate-600 disabled:opacity-50"
        >
          Tipp speichern
        </button>
        <span className="ml-auto self-center text-slate-400">
          {new Date(match.kickoff).toLocaleString("de-DE", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
        </span>
      </div>
    </div>
  );
}
