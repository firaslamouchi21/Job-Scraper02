#!/usr/bin/env sh
set -e

export SCRAPER_URL="${SCRAPER_URL:-http://localhost:8000}"

python -m uvicorn job_scraper.scraper:api --host 0.0.0.0 --port 8000 &
SCRAPER_PID=$!

cleanup() {
    kill "$SCRAPER_PID" 2>/dev/null || true
}
trap cleanup TERM INT EXIT

exec python -m streamlit run job_scraper/app.py --server.port="${PORT:-8501}" --server.address=0.0.0.0
