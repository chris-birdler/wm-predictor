export interface Team {
  id: number;
  name: string;
  fifa_code: string;
  confederation: string;
  group: string | null;
  elo: number;
  is_host: boolean;
}

export interface TeamRef {
  id: number;
  name: string;
  fifa_code: string;
}

export interface Match {
  id: number;
  kickoff: string;
  stage: string;
  group: string | null;
  home: TeamRef;
  away: TeamRef;
  home_score: number | null;
  away_score: number | null;
  is_finished: boolean;
}

export interface Prediction {
  match_id: number;
  p_home: number;
  p_draw: number;
  p_away: number;
  expected_home_goals: number;
  expected_away_goals: number;
  predicted_score: [number, number];
  has_odds: boolean;
}

export interface TeamProbs {
  team_id: number;
  name: string;
  fifa_code: string;
  p_advance_group: number;
  p_r16: number;
  p_qf: number;
  p_sf: number;
  p_final: number;
  p_winner: number;
}

export interface SimulationResponse {
  run_id: number;
  n_runs: number;
  teams: TeamProbs[];
}
