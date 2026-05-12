# WM Predictor 2026

Vorhersage-App für die FIFA Weltmeisterschaft 2026. Tippspiel + Monte-Carlo-Simulation auf Basis aggregierter Buchmacher-Quoten, Elo, Form und Head-to-Head.

## Stack

- **Backend**: FastAPI + SQLAlchemy + PostgreSQL
- **Frontend**: React + Vite + TypeScript + Tailwind
- **Auth**: JWT (Multi-User)
- **Deploy**: docker-compose (Hetzner)
- **ML**: scikit-learn / XGBoost (Phase 2)

## Vorhersage-Strategie

**Ensemble (Phase 1)** — gewichteter Mix aus 5 Signalen, Output: `P(home), P(draw), P(away)` + erwartete Tore pro Team.

| Signal | Gewicht | Quelle |
|---|---|---|
| Buchmacher-Quoten | 60% | The Odds API (free tier) + oddsportal.com scraping; Mehrere Bookies, Pinnacle stärker gewichtet; Overround entfernt |
| Elo-Rating | 25% | Eigene Berechnung. K-Faktor: WM 60, Kontinental 50, Quali 40, Nations 35, Friendly 20 — bei Quali + Friendly zusätzlich Confed-Multiplikator (UEFA/CONMEBOL 1.0, CAF 0.85, CONCACAF 0.80, AFC 0.75, OFC 0.55). Mapping in `app/data/confederations.py` |
| Recent Form | 10% | Elo-Surprise EWMA: pro Spiel (actual − expected) gegen Elo des Gegners, ähnlich Glicko/UTR. Letzte 15 Spiele, 6-Monats-Decay |
| Head-to-Head | 3% | Direkte Duelle (klein wegen wenig Daten) |
| Heimvorteil | 2% | Bonus für USA/CAN/MEX |

**ML-Stacking (Phase 2)** — XGBoost trainiert auf Kaggle-Dataset `martj42/international-football-results-from-1872-to-2017` (regelmäßig aktualisiert, ~45k Spiele). Features: alle obigen Signale + Tordifferenz-Trends + Tournament-Stage. Output: dieselben Wahrscheinlichkeiten, aber mit gelernten nichtlinearen Interaktionen.

**Tor-Modell** — Bivariate Poisson (Dixon-Coles) für Monte-Carlo-Sampling. Wichtig für realistische KO-Verlängerungen.

## Monte Carlo

- N = 10.000 Läufe pro Simulation
- Pro Spiel: Tore aus Poisson(λ_home, λ_away) sampeln
- Bei KO + Unentschieden: Verlängerung (zusätzliche 30 Min Poisson), dann 50/50 Elfmeter (leicht Form-gewichtet)
- Output: P(Achtelfinale), P(Viertelfinale), ..., P(Weltmeister) pro Team

## Turnierformat 2026

- 48 Teams, 12 Gruppen á 4
- Pro Gruppe: 3 Spieltage, Jeder gegen Jeden
- Aus Gruppe weiter: Top 2 + 8 beste Gruppendritte → Round of 32
- KO: R32 → R16 → Viertelfinale → Halbfinale → Finale + Spiel um Platz 3

## Setup

```bash
cp .env.example .env
# .env editieren (DB-Passwort, JWT-Secret, optional ODDS_API_KEY)
docker compose up -d
# Backend: http://localhost:8000/docs
# Frontend: http://localhost:5173
```

Seed-Daten laden:
```bash
docker compose exec backend python -m app.data.seed
```

## Roadmap

- [x] Projekt-Setup, Docker, DB-Schema
- [x] Elo-Engine + Odds-Aggregation + Monte Carlo (Basis, mit KO-Cache)
- [x] Auth (Login/Register + JWT)
- [x] Frontend: Gruppen-Übersicht + Match-Cards
- [x] Frontend: Playoff-Bracket
- [x] Tipp-Modus: Single-Click / Runde / Alle Gruppen
- [x] Simulations-Dashboard mit Charts
- [x] WM-2026-Draw eingetragen (echte Gruppen A–L)
- [x] Historische Daten geladen (martj42 Dataset, seit 2010, ~15.7k Spiele)
- [x] Odds-Ingestion live (The Odds API, ~26 Bookies pro Spiel, 50/72 Gruppenspiele aktuell auf den Brettern)
- [ ] Periodischer Odds-Refresh (cron / scheduler — Quoten ändern sich täglich)
- [ ] XGBoost Stacking-Modell + Training-Pipeline
- [ ] Leaderboard zwischen Usern
- [ ] (Optional) Claude API für News-Faktoren

## Struktur

```
wm-predictor/
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI Entry
│   │   ├── config.py          Settings
│   │   ├── db.py              SQLAlchemy Session
│   │   ├── models/            DB-Schemas
│   │   ├── api/               REST-Endpoints
│   │   ├── prediction/        Ensemble, Elo, Odds-Aggregation
│   │   ├── simulation/        Monte Carlo
│   │   └── data/              Ingestion + Seed
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/             Groups, Playoffs, Simulation
│   │   ├── components/        GroupCard, MatchCard, Bracket
│   │   └── api/               Backend-Client
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```
