# Job Scraper by Firas V2 Improved version 23/04/2026

![CI](https://github.com/firaslamouchi21/Job-Scraper02/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)

A no-nonsense job search tool that finds listings across multiple sites and scores them against your CV using AI. Built it as a tool for myself because I was tired of checking ten different job boards every morning.now that i found a job i can focus on improving this tool.for community use. ill be able to release full version in few months.if you wanna help me you can mail me at firaslamou@gmail.com et merci!


 IT Runs entirely in Docker on a Linux VM. No local Python setup, no dependency hell, no "works on my machine".

## What you get

- Paste your CV and keywords into the web UI
- AI scores every job 0-100 for relevance
- Pause, resume, or restart runs from the dashboard
- Export results as JSON or CSV
- All data lives in a SQLite database you actually own

## How to run it

You need Docker. That's it.

### 1. Set your environment

```bash
cp .env.example .env
```

Edit `.env` and drop in any AI keys you have (Groq, Anthropic, or Gemini). If you don't have any, lite mode works fine with keyword matching.

### 2. Spin it up

```bash
docker compose up --build
```

This builds two containers:

- **scraper** at `http://localhost:8000` (the brain)
- **UI** at `http://localhost:8501` (your dashboard)

The optional n8n automation engine lives under a separate profile if you want it later:

```bash
docker compose --profile automation up
```

### 3. Open the UI

Go to `http://localhost:8501`, paste your CV, add some keywords like "senior python remote", pick your AI provider (or stay in lite mode), and hit Start. Watch the progress bar fill up. High-scoring jobs bubble to the top.

### 4. Export when done

```bash
curl http://localhost:8000/export/csv > jobs.csv
```

## Docker is the only way

This app is designed to run inside Docker containers on a Linux VM. Do not try to run it natively on Windows or macOS. The scraper uses Playwright, the UI needs Streamlit, and the database expects a Unix path structure. Docker handles all of that for you.

Requirements:

- Docker Engine 24+ or Docker Desktop
- A Linux VM (WSL2 on Windows, OrbStack or Docker Desktop on Mac, any Linux host)
- 2GB RAM minimum, 4GB recommended

## Environment variables

| Variable | What it does | Default |
| --- | --- | --- |
| `GROQ_API_KEY` | Groq AI scoring | empty |
| `ANTHROPIC_API_KEY` | Claude AI scoring | empty |
| `GEMINI_API_KEY` | Google AI scoring | empty |
| `DATA_DIR` | Where SQLite and logs live | `./data` |
| `REQUEST_DELAY_SECONDS` | Politeness between searches | `2.0` |
| `RETRY_MAX_ATTEMPTS` | How many times to retry a failed search | `5` |

## API for power users

The scraper exposes a FastAPI server. The UI talks to it, but you can too.

Start a run:

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"provider":"groq","lite_mode":true,"sites":["example.com"],"keywords":["python"],"cv_text":"developer"}'
```

Check status:

```bash
curl http://localhost:8000/status
```

Pause a running job:

```bash
curl -X POST http://localhost:8000/pause
```

Resume:

```bash
curl -X POST http://localhost:8000/resume
```

Kill it:

```bash
curl -X POST http://localhost:8000/stop
```

## Makefile shortcuts

```bash
make build
make up
make down
make logs
```

## Keeping your keys safe

Never commit `.env`. It is gitignored by default. If you accidentally pushed a key, rotate it immediately.
