import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Bracket } from "../components/Bracket";
import { usePredictions } from "../state/predictions";
import type { Match, Team } from "../types";

const STAGES = ["r32", "r16", "qf", "sf", "third", "final"] as const;
const NEXT_KO_STAGE: Record<string, string | undefined> = {
  r32: "r16",
  r16: "qf",
  qf: "sf",
  sf: "final",
};

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
  const queryClient = useQueryClient();
  const q = useQuery({ queryKey: ["matches", "all"], queryFn: () => api.matches({}) });
  const teamsQ = useQuery({ queryKey: ["teams-by-group"], queryFn: api.teamsByGroup });
  const [busy, setBusy] = useState<string | null>(null);
  const [autoBusy, setAutoBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { predictions, mergePredictions } = usePredictions();

  const matchesByStage: Record<string, Match[]> = {};
  const groupMatches: Match[] = [];
  for (const m of q.data ?? []) {
    if (STAGES.includes(m.stage as (typeof STAGES)[number])) {
      (matchesByStage[m.stage] ??= []).push(m);
    } else if (m.stage === "group") {
      groupMatches.push(m);
    }
  }
  const predictedGroupCount = groupMatches.filter((m) => predictions[m.id]).length;
  const totalGroupCount = groupMatches.length;
  const groupsComplete = totalGroupCount > 0 && predictedGroupCount === totalGroupCount;

  const teamById: Record<number, Team> = {};
  for (const list of Object.values(teamsQ.data ?? {})) {
    for (const t of list) teamById[t.id] = t;
  }

  const parseError = (err: unknown): string => {
    const raw = err instanceof Error ? err.message : String(err);
    // Surface backend's HTTPException detail when available
    const m = raw.match(/HTTP (\d+): (.+)$/);
    if (m) {
      try {
        const body = JSON.parse(m[2]);
        if (typeof body?.detail === "string") return body.detail;
      } catch {
        // not JSON
      }
      return m[2];
    }
    return raw;
  };

  const handleStage = async (stage: string) => {
    setBusy(stage);
    setError(null);
    try {
      const result = await api.predictStage(stage);
      mergePredictions(result);
      const next = NEXT_KO_STAGE[stage];
      if (next) {
        await api.seedNext(next);
        await queryClient.invalidateQueries({ queryKey: ["matches"] });
      }
    } catch (e) {
      setError(parseError(e));
    } finally {
      setBusy(null);
    }
  };

  const handleAutoFill = async () => {
    setAutoBusy(true);
    setError(null);
    try {
      const result = await api.autoFillBracket();
      mergePredictions(result.predictions);
      await queryClient.invalidateQueries({ queryKey: ["matches"] });
    } catch (e) {
      setError(parseError(e));
    } finally {
      setAutoBusy(false);
    }
  };

  const knockoutMatchesCount = STAGES.reduce(
    (acc, s) => acc + (matchesByStage[s]?.length ?? 0),
    0,
  );

  const stageButtons = STAGES;
  const finalMatch = groupsComplete ? matchesByStage["final"]?.[0] : undefined;
  const finalPred = finalMatch ? predictions[finalMatch.id] : undefined;
  let championId: number | null = null;
  if (finalMatch && finalPred) {
    const decisive = finalPred.extra_time_score ?? finalPred.predicted_score;
    const [h, a] = decisive;
    championId =
      h > a
        ? finalMatch.home.id
        : a > h
          ? finalMatch.away.id
          : finalPred.p_home >= finalPred.p_away
            ? finalMatch.home.id
            : finalMatch.away.id;
  }
  const champion = championId !== null ? teamById[championId] : null;

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
            32 teams enter, one lifts the trophy. Predict the groups to seed
            R32, then walk it stage by stage — or auto-fill the whole bracket.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleAutoFill}
            disabled={autoBusy || !groupsComplete}
            title={
              !groupsComplete
                ? `Predict all group matches first (${predictedGroupCount}/${totalGroupCount || "—"})`
                : ""
            }
            className="rounded-md bg-fifa-pink px-4 py-2 font-display text-xs font-bold uppercase tracking-wide text-white shadow-sm transition hover:bg-fifa-magenta disabled:cursor-not-allowed disabled:opacity-50"
          >
            {autoBusy ? "Filling…" : "Auto-fill bracket"}
          </button>
          {stageButtons.map((s) => {
            const noMatches = (matchesByStage[s]?.length ?? 0) === 0;
            const disabled =
              busy === s || autoBusy || noMatches || !groupsComplete;
            const title = !groupsComplete
              ? `Predict all group matches first (${predictedGroupCount}/${totalGroupCount || "—"})`
              : noMatches
                ? `Predict the previous round to seed ${STAGE_LABEL[s]}`
                : "";
            return (
              <button
                key={s}
                onClick={() => handleStage(s)}
                disabled={disabled}
                className="rounded-md border border-fifa-line bg-fifa-surface px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-fifa-ink transition hover:border-fifa-pink hover:text-fifa-pink disabled:cursor-not-allowed disabled:opacity-40"
                title={title}
              >
                {busy === s ? "…" : `Predict ${STAGE_LABEL[s]}`}
              </button>
            );
          })}
        </div>
      </section>
      {error && (
        <div className="flex items-center justify-between gap-3 rounded-md border border-fifa-pink/40 bg-fifa-pink/5 px-4 py-3 text-sm">
          <span className="text-fifa-ink">{error}</span>
          <Link
            to="/"
            className="rounded-md bg-fifa-pink px-3 py-1.5 text-xs font-bold uppercase tracking-wide text-white hover:bg-fifa-magenta"
          >
            ← Go to Standings
          </Link>
        </div>
      )}
      {champion && (
        <div className="flex items-center gap-3 rounded-2xl border border-fifa-pink/40 bg-fifa-gradient p-4 text-white shadow-sm">
          <span className="text-3xl">🏆</span>
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-widest opacity-80">
              Predicted Champion
            </div>
            <div className="font-display text-2xl font-extrabold tracking-tight">
              {champion.name}
            </div>
          </div>
        </div>
      )}
      {(!groupsComplete || knockoutMatchesCount === 0) && (
        <p className="rounded-md border border-fifa-line bg-fifa-surface p-4 text-sm text-fifa-dim">
          {!groupsComplete && totalGroupCount > 0 ? (
            <>
              Predict all group matches first (
              <span className="font-semibold text-fifa-ink">
                {predictedGroupCount}/{totalGroupCount}
              </span>
              {" "}done) on the Standings tab — knockout pairings stay blank
              until standings are complete.
            </>
          ) : (
            <>
              Knockout pairings haven't been seeded yet. Predict all group
              matches first (Standings tab) or hit Auto-fill above to walk the
              whole tournament in one go.
            </>
          )}
        </p>
      )}
      <Bracket
        matchesByStage={matchesByStage}
        predictions={predictions}
        onPredictions={mergePredictions}
        expectedSlots={EXPECTED_SLOTS}
        groupsComplete={groupsComplete}
      />
    </div>
  );
}
