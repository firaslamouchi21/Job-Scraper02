# Job Scraper Tool by Firas Lamouchi

![CI](https://github.com/REPLACE_OWNER/REPLACE_REPO/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Docker](https://img.shields.io/badge/docker-compose-blue)

A local-first job scraping stack with Docker Compose by Firas Lamouchi.

## Services

- agent-ui: Streamlit UI at <http://localhost:8501>
- scraper: FastAPI service at <http://localhost:8000>
- automation-engine: n8n at <http://localhost:5678>

## Quick Start

1. Configure

Edit files in ./config:

- sites.txt: one site per line
- keywords.txt: one keyword or job title per line
- cv.txt: your CV text
- .env.example: copy to .env and set GROQ_API_KEY (optional)

1. Run

```bash
docker compose up --build
```

1. Use

- Open UI: <http://localhost:8501>
- Open n8n: <http://localhost:5678>

## Developer CLI

Run without the UI:

```bash
python cli.py run --lite
python cli.py run --api-key YOUR_GROQ_KEY
```

Export saved results from the local SQLite database:

```bash
python cli.py export --format json --limit 200
python cli.py export --format csv --out jobs.csv
```

You can override paths:

```bash
python cli.py --config ./config --data ./data run --lite
```

## Makefile

```bash
make build
make up
make down
make logs
make ps
```

## BYOK and Lite Mode

- Provide a Groq API key in the UI to enable AI scoring.
- Toggle Lite Mode to use keyword-only scoring without an API key.
- Scraper can also be triggered from n8n via POST <http://scraper:8000/run>

## Persistence

All state is stored in ./data:

- SQLite database and logs
- n8n workflows and database

Running docker compose down will not delete ./data.

## Scraper API

Trigger a run:

- POST <http://localhost:8000/run>

Read results:

- GET <http://localhost:8000/jobs>

Export:

- GET <http://localhost:8000/export/json>
- GET <http://localhost:8000/export/csv>

## Rate limiting and retries

The scraper supports basic delay and retry tuning via environment variables:

- REQUEST_DELAY_SECONDS (default 0.6)
- RETRY_MAX_ATTEMPTS (default 4)
- RETRY_BASE_SECONDS (default 0.6)
- RETRY_MAX_SECONDS (default 8)

## n8n Trigger

Send a POST to <http://scraper:8000/run> with JSON:

```json
{"api_key":"your_key","lite_mode":false}
```
