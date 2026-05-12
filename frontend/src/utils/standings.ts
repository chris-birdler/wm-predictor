import type { Match, Prediction, Team } from "../types";

export interface Standing {
  team: Team;
  played: number;
  w: number;
  d: number;
  l: number;
  gf: number;
  ga: number;
  gd: number;
  pts: number;
}

export function computeStandings(
  teams: Team[],
  matches: Match[],
  predictions: Record<number, Prediction>,
): Standing[] {
  const byId = new Map<number, Standing>();
  for (const t of teams) {
    byId.set(t.id, { team: t, played: 0, w: 0, d: 0, l: 0, gf: 0, ga: 0, gd: 0, pts: 0 });
  }

  for (const m of matches) {
    let h: number | null = null;
    let a: number | null = null;
    if (m.is_finished && m.home_score != null && m.away_score != null) {
      h = m.home_score;
      a = m.away_score;
    } else if (predictions[m.id]) {
      [h, a] = predictions[m.id].predicted_score;
    }
    if (h == null || a == null) continue;

    const home = byId.get(m.home.id);
    const away = byId.get(m.away.id);
    if (!home || !away) continue;

    home.played++; away.played++;
    home.gf += h; home.ga += a;
    away.gf += a; away.ga += h;
    home.gd = home.gf - home.ga;
    away.gd = away.gf - away.ga;
    if (h > a) { home.w++; away.l++; home.pts += 3; }
    else if (h < a) { away.w++; home.l++; away.pts += 3; }
    else { home.d++; away.d++; home.pts++; away.pts++; }
  }

  return Array.from(byId.values()).sort(
    (x, y) =>
      y.pts - x.pts ||
      y.gd - x.gd ||
      y.gf - x.gf ||
      x.team.name.localeCompare(y.team.name),
  );
}
