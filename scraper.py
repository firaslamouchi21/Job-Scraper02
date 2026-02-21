import os
import json
import time
import threading
import random
import sys
import io
import csv
from datetime import datetime, timezone
from fastapi import FastAPI, Response
from pydantic import BaseModel
from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import db
from ai_service import AIService

DATA_DIR = os.environ.get("DATA_DIR", "/data")
CONFIG_DIR = os.environ.get("CONFIG_DIR", "/config")
USE_PLAYWRIGHT = os.environ.get("USE_PLAYWRIGHT", "true").lower() == "true"
REQUEST_DELAY_SECONDS = float(os.environ.get("REQUEST_DELAY_SECONDS", "0.6"))
RETRY_MAX_ATTEMPTS = int(os.environ.get("RETRY_MAX_ATTEMPTS", "4"))
RETRY_BASE_SECONDS = float(os.environ.get("RETRY_BASE_SECONDS", "0.6"))
RETRY_MAX_SECONDS = float(os.environ.get("RETRY_MAX_SECONDS", "8"))
STATUS_PATH = os.path.join(DATA_DIR, "status.json")
LOG_PATH = os.path.join(DATA_DIR, "scraper.log")
LOCK_PATH = os.path.join(DATA_DIR, "run.lock")

api = FastAPI()


class RunRequest(BaseModel):
    api_key: str | None = ""
    lite_mode: bool = False


def read_lines(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [x.strip() for x in f.read().splitlines() if x.strip()]
    except Exception:
        return []


def read_text(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def write_status(message: str, progress: int, meta: dict | None = None):
    os.makedirs(DATA_DIR, exist_ok=True)
    payload = {
        "message": message,
        "progress": int(progress),
        "timestamp": time.time(),
    }
    if meta:
        payload.update(meta)
    try:
        with open(STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f)
    except Exception:
        pass


def append_log(line: str):
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} {line}\n")
    except Exception:
        pass


def log_event(event: str, **fields):
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    try:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    except Exception:
        pass


def is_running():
    return os.path.exists(LOCK_PATH)


def lock():
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LOCK_PATH, "w", encoding="utf-8") as f:
        f.write(str(time.time()))


def unlock():
    try:
        if os.path.exists(LOCK_PATH):
            os.remove(LOCK_PATH)
    except Exception:
        pass


def sleep_delay():
    if REQUEST_DELAY_SECONDS > 0:
        time.sleep(REQUEST_DELAY_SECONDS)


def backoff_sleep(attempt: int):
    base = RETRY_BASE_SECONDS * (2**max(0, attempt))
    delay = min(RETRY_MAX_SECONDS, base)
    jitter = random.random() * 0.25 * delay
    time.sleep(delay + jitter)


def with_retry(fn):
    last = None
    for attempt in range(RETRY_MAX_ATTEMPTS):
        try:
            return fn()
        except Exception as e:
            last = e
            if attempt < RETRY_MAX_ATTEMPTS - 1:
                log_event(
                    "retry",
                    attempt=attempt + 1,
                    max_attempts=RETRY_MAX_ATTEMPTS,
                    error=str(e),
                )
                backoff_sleep(attempt)
    if last:
        raise last


def html_extract(url: str):
    if USE_PLAYWRIGHT:
        try:
            content = ""
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    page.set_default_timeout(25000)
                    page.goto(url, wait_until="domcontentloaded")
                    content = page.content()
                finally:
                    browser.close()
            soup = BeautifulSoup(content, "html.parser")
            text = soup.get_text(" ", strip=True)
            if text:
                return text[:8000]
        except Exception:
            log_event("fetch_playwright_failed", url=url)
            pass
    try:
        def fetch():
            sleep_delay()
            return requests.get(
                url,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0"},
            )

        r = with_retry(fetch)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        return text[:8000]
    except Exception:
        log_event("fetch_requests_failed", url=url)
        return ""


def run_scrape(api_key: str, lite_mode: bool):
    if is_running():
        log_event("run_rejected", reason="already_running")
        return
    lock()
    try:
        db.init()
        sites = read_lines(os.path.join(CONFIG_DIR, "sites.txt"))
        keywords = read_lines(os.path.join(CONFIG_DIR, "keywords.txt"))
        cv_text = read_text(os.path.join(CONFIG_DIR, "cv.txt"))
        use_ai = bool(api_key) and not lite_mode
        ai = AIService(api_key if use_ai else "")
        log_event(
            "run_started",
            use_ai=use_ai,
            lite_mode=bool(lite_mode),
            sites=len(sites),
            keywords=len(keywords),
        )
        total = max(1, len(sites) * max(1, len(keywords)))
        done = 0
        added = 0
        write_status("starting", 0, {"running": True, "added": 0})
        for site in sites or [""]:
            for kw in keywords or [""]:
                query = " ".join([x for x in [f"site:{site}" if site else "", kw] if x])
                append_log(f"query={query}")
                log_event("query", query=query)
                try:
                    def search():
                        sleep_delay()
                        with DDGS() as ddgs:
                            return list(ddgs.text(query, max_results=10))

                    results = with_retry(search)
                except Exception:
                    log_event("search_failed", query=query)
                    results = []
                for r in results:
                    title = r.get("title") or ""
                    link = r.get("href") or ""
                    snippet = r.get("body") or ""
                    company = site
                    text = snippet
                    if use_ai and link:
                        fetched = html_extract(link)
                        if fetched:
                            text = fetched
                    score, reasoning = ai.analyze(text, cv_text, keywords)
                    h = db.upsert_job(
                        title=title,
                        company=company,
                        link=link,
                        site=site,
                        snippet=snippet,
                        score=score,
                        reasoning=reasoning,
                    )
                    if h:
                        added += 1
                done += 1
                pct = int((done / total) * 100)
                write_status("running", pct, {"running": True, "added": added})
        write_status("complete", 100, {"running": False, "added": added})
        log_event("run_complete", added=added)
    finally:
        unlock()


@api.get("/health")
def health():
    return {"ok": True}


@api.get("/status")
def status():
    try:
        with open(STATUS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"message": "idle", "progress": 0, "running": is_running()}


@api.get("/jobs")
def jobs(limit: int = 200):
    db.init()
    return {"jobs": db.list_jobs(limit=limit)}


@api.get("/export/json")
def export_json(limit: int = 200):
    db.init()
    return db.list_jobs(limit=limit)


@api.get("/export/csv")
def export_csv(limit: int = 200):
    db.init()
    rows = db.list_jobs(limit=limit)
    fieldnames = []
    for r in rows:
        for k in r.keys():
            if k not in fieldnames:
                fieldnames.append(k)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return Response(content=buf.getvalue(), media_type="text/csv")


@api.post("/run")
def run(req: RunRequest):
    t = threading.Thread(
        target=run_scrape,
        args=(req.api_key or "", bool(req.lite_mode)),
        daemon=True,
    )
    t.start()
    return {"started": True}
