# WC Predictor 2026

Predictor app for the FIFA World Cup 2026. Group-stage standings + bracket
projections from a 5-component ensemble (odds, Elo, form, head-to-head)
combined with a team-specific Poisson goal model, simulated via Monte Carlo.

## Stack

- **Backend**: FastAPI + SQLAlchemy + PostgreSQL
- **Frontend**: React + Vite + TypeScript + Tailwind
- **Auth**: JWT (multi-user)
- **Deploy**: docker-compose (Hetzner)
- **ML**: scikit-learn / XGBoost (Phase 2)

## Prediction strategy

**Ensemble (Phase 1)** — weighted soft-vote across 4 signals, output: `P(home),
P(draw), P(away)`. Each signal produces a 1X2 triple and they're averaged by
weight.

| Signal | Weight | Source |
|---|---|---|
| Bookmaker odds | 60% | The Odds API (free tier) + oddsportal.com scraping. Pinnacle ×2, Bet365 ×1.2, others ~1.0; overround removed per snapshot |
| Elo rating | 27% | Custom replay of all 32k+ international matches since 1990. K-factor: WC 60, Continental 50, WC Qualifier / Continental Qualifier / Nations League group 40, Nations League Finals 50, Friendly 20. Confederation multiplier on qualifiers / friendlies / continental tournaments (UEFA/CONMEBOL ×1.0, CAF ×0.85, CONCACAF ×0.80, AFC ×0.75, OFC ×0.55) — downweights inflation from weak co-confed opposition. Home advantage +100 Elo. See `app/prediction/elo.py` and `app/data/confederations.py` |
| Recent form | 10% | Elo-surprise EWMA: per match `(actual − expected)` against the opponent's Elo at the time. Last ~15 matches, 6-month decay |
| Head-to-head | 3% | Direct historical record between the two teams. Small weight on purpose — sample size |

Host advantage is *not* a separate component — it's already inside Elo as the
`+100` home bonus, gated by whether the home team is USA/CAN/MEX or otherwise
flagged as host.

**ML stacking (Phase 2 — planned)** — XGBoost trained on the same 32k+ matches.
Features: all of the above signals plus goal-difference trends, rest days,
tournament stage. Output: the same 1X2 probabilities but with learned
non-linear interactions. Replaces the fixed 60/27/10/3 weights.

## Goal model

Predicted scoreline uses a team-specific Poisson model (Dixon-Coles-flavoured):

```
λ_home = home.attack_rate × away.defense_rate × league_avg × home_factor
λ_away = away.attack_rate × home.defense_rate × league_avg
```

- `attack_rate`, `defense_rate` are per-team multipliers vs the league average
  (1.0 = average; computed in `app/data/compute_attack_defense.py`)
- Computed from historical goals scored/conceded with **4-year exponential
  time decay** and **Bayesian shrinkage** (k=4) toward 1.0
- `league_avg` ≈ 1.37 goals per team per match (recomputed from the dataset)
- `home_factor` = 1.15 for matches where the home team is a 2026 host, else 1.0

The predicted scoreline is **one deterministic Poisson sample** per match
(RNG seeded by `match_id`). Sampling rather than taking the mode/mean
captures the natural variance of football scorelines: many matches end 1:0
or 2:0, and rounding `λ_h≈1.5, λ_a≈1.0` to `2:1` would mask that diversity.

## Monte Carlo

- N = 10,000 runs per simulation
- Per match: goals drawn from Poisson(λ_h, λ_a)
- Knockout draws: extra time = half a regular match (Poisson(0.5λ)); penalty
  shootout decides remaining ties, slightly weighted to the 1X2 favourite
- Output: `P(R32), P(R16), P(QF), P(SF), P(Final), P(Champion)` per team

## Tournament format 2026

- 48 teams, 12 groups of 4
- Group stage: 3 matchdays, round-robin
- Top 2 + 8 best third-placed teams → Round of 32
- Knockout: R32 → R16 → QF → SF → Final + Third place playoff

## Setup

```bash
cp .env.example .env
# edit .env (DB password, JWT secret, optional ODDS_API_KEY)
docker compose up -d
# backend: http://localhost:8000/docs
# frontend: http://localhost:5173
```

Seed WC 2026 teams + group fixtures:
```bash
docker compose exec backend python -m app.data.seed
```

Replay historical Elo + compute team attack/defense rates (full rebuild):
```bash
docker compose exec backend python -m app.data.recompute_elo
```

## Roadmap

- [x] Project setup, Docker, DB schema
- [x] Elo engine + odds aggregation + Monte Carlo (with KO cache)
- [x] Auth (login/register + JWT)
- [x] Frontend: standings (per-group W/D/L/GF/GA/Pts auto-computed from
      predicted scores), match cards, knockout bracket
- [x] WC 2026 final draw seeded (groups A–L)
- [x] Historical data loaded (martj42 dataset since 1990, ~32k matches)
- [x] Live odds ingestion (The Odds API, ~26 bookmakers per match)
- [x] Team-specific Poisson goal model (attack / defense rates)
- [x] Per-match Poisson scoreline sampling (deterministic by match id)
- [ ] Periodic odds refresh (cron / scheduler — odds change daily)
- [ ] FIFA 2026 R32 seeding table → materialise knockout fixtures from group
      results
- [ ] XGBoost stacking model + training pipeline
- [ ] (Optional) Claude API for news-based adjustments

## Structure

```
wm-predictor/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI entry
│   │   ├── config.py            Settings (K-factors, ensemble weights)
│   │   ├── db.py                SQLAlchemy session
│   │   ├── models/              DB schemas
│   │   ├── api/                 REST endpoints
│   │   ├── prediction/          ensemble, elo, form, h2h, odds_aggregator
│   │   ├── simulation/          Monte Carlo
│   │   └── data/                ingestion + seed + recompute
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/               Standings, Playoffs, Simulation, Login
│   │   ├── components/          GroupCard, MatchCard, Bracket
│   │   ├── utils/               standings (W/D/L computation), flag emojis
│   │   └── api/                 backend client
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```
