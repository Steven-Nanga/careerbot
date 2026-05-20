#!/usr/bin/env sh
set -eu

INTERVAL_SECONDS="${CAREERBOT_INTERVAL_SECONDS:-3600}"

echo "CareerBot container started. Running every ${INTERVAL_SECONDS} seconds."

while true; do
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Starting CareerBot scrape"
  python /app/scraper.py || echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] CareerBot scrape failed; will retry on next interval"
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Sleeping for ${INTERVAL_SECONDS} seconds"
  sleep "${INTERVAL_SECONDS}"
done
