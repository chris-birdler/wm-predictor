#!/usr/bin/env bash
#
# Full data refresh for the WM Predictor, intended to be run by cron every 6h.
#
# Pulls fresh odds, refetches new international results (Elo + attack/defense),
# re-predicts all groups, rebuilds the knockout bracket and re-runs the Monte
# Carlo simulation -- all inside the running production backend container.
#
# Install (root crontab, every 6 hours, output appended to a log):
#   0 */6 * * * /root/wm-predictor/scripts/refresh.sh >> /root/wm-predictor/scripts/refresh.log 2>&1
#
set -euo pipefail

PROJECT_DIR="/root/wm-predictor"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"

cd "$PROJECT_DIR"

echo "----- refresh.sh $(date -u +%Y-%m-%dT%H:%M:%SZ) -----"

# -T disables TTY allocation (required under cron). Runs the one-shot
# orchestration module that chains odds -> results/Elo -> predictions ->
# bracket -> simulation in a single process.
docker compose -f "$COMPOSE_FILE" exec -T backend python -m app.data.refresh_all
