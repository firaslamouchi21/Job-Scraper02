/// Job Scraper 02: Automated Intelligence Engine
Job Scraper 02 isn't just a script; it’s a full-throttle automation pipeline designed to take the "search" out of job searching. Built for developers who want to skip the manual scrolling and go straight to the high-value opportunities, this tool handles the heavy lifting of discovery, extraction, and ranking—all from your local machine.

///The Mission
In a market full of noise, this tool acts as your personal scout. It monitors the web, identifies relevant listings based on your specific tech stack and keywords, and uses Groq AI to tell you exactly which ones are worth your time. No cloud subscriptions, no data selling—just local, containerized power.

/// The Engine Under the Hood
Deep Discovery: Uses DuckDuckGo and Playwright to bypass basic limitations and fetch real-time data from across the web.

AI-Powered Ranking: Integrates Groq (Llama 3) to score jobs against your actual CV. It doesn't just find jobs; it finds your jobs.

Workflow Automation: Comes pre-integrated with n8n, allowing you to schedule runs, send alerts, or pipe data into your own CRM/Spreadsheets.

Local-First Architecture: Your data stays in your ./data folder. Built with FastAPI for speed and Streamlit for a clean, "street-smart" control center.

Job Scraper Tool by Firas Lamouchi
A local-first job scraping stack with Docker Compose by Firas Lamouchi.

Services
agent-ui: Streamlit UI at http://localhost:8501

scraper: FastAPI service at http://localhost:8000

automation-engine: n8n at http://localhost:5678

Quick Start
Configure

Edit files in ./config:

sites.txt: one site per line

keywords.txt: one keyword or job title per line

cv.txt: your CV text

.env.example: copy to .env and set GROQ_API_KEY (optional)

Run

Bash
docker compose up --build
Use

Open UI: http://localhost:8501

Open n8n: http://localhost:5678

Developer CLI
Run without the UI:

Bash
python cli.py run --lite
python cli.py run --api-key YOUR_GROQ_KEY
Export saved results from the local SQLite database:

Bash
python cli.py export --format json --limit 200
python cli.py export --format csv --out jobs.csv
You can override paths:

Bash
python cli.py --config ./config --data ./data run --lite
Makefile
Bash
make build
make up
make down
make logs
make ps
BYOK and Lite Mode
Provide a Groq API key in the UI to enable AI scoring.

Toggle Lite Mode to use keyword-only scoring without an API key.

Scraper can also be triggered from n8n via POST http://scraper:8000/run

Persistence
All state is stored in ./data:

SQLite database and logs

n8n workflows and database

Running docker compose down will not delete ./data.

Scraper API
Trigger a run:

POST http://localhost:8000/run

Read results:

GET http://localhost:8000/jobs

Export:

GET http://localhost:8000/export/json

GET http://localhost:8000/export/csv

Rate limiting and retries
The scraper supports basic delay and retry tuning via environment variables:

REQUEST_DELAY_SECONDS (default 0.6)

RETRY_MAX_ATTEMPTS (default 4)

RETRY_BASE_SECONDS (default 0.6)

RETRY_MAX_SECONDS (default 8)

n8n Trigger
Send a POST to http://scraper:8000/run with JSON:

JSON
{"api_key":"your_key","lite_mode":false}
