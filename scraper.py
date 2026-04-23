import os
import json
import time
import threading
import random
import sys
import io
import csv
from datetime import datetime, timezone
from urllib.parse import urlparse
from fastapi import FastAPI, Response
from pydantic import BaseModel
from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import db
from ai_service import AIService

USE_PLAYWRIGHT = os.environ.get("USE_PLAYWRIGHT", "true").lower() == "true"
REQUEST_DELAY_SECONDS = float(os.environ.get("REQUEST_DELAY_SECONDS", "2.0"))
RETRY_MAX_ATTEMPTS = int(os.environ.get("RETRY_MAX_ATTEMPTS", "5"))
RETRY_BASE_SECONDS = float(os.environ.get("RETRY_BASE_SECONDS", "2.0"))
RETRY_MAX_SECONDS = float(os.environ.get("RETRY_MAX_SECONDS", "16"))

_pause_requested = False
_stop_requested = False


def data_dir() -> str:
    return os.environ.get("DATA_DIR", "./data")


def config_dir() -> str:
    return os.environ.get("CONFIG_DIR", "./config")


def status_path() -> str:
    return os.path.join(data_dir(), "status.json")


def log_path() -> str:
    return os.path.join(data_dir(), "scraper.log")


def lock_path() -> str:
    return os.path.join(data_dir(), "run.lock")

api = FastAPI()


class RunRequest(BaseModel):
    provider: str | None = "groq"
    api_key: str | None = ""
    groq_api_key: str | None = ""
    anthropic_api_key: str | None = ""
    gemini_api_key: str | None = ""
    lite_mode: bool = False
    sites: list[str] | None = None
    keywords: list[str] | None = None
    cv_text: str | None = None


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


def normalize_site(site: str) -> str:
    s = (site or "").strip()
    if not s:
        return ""
    if "://" in s:
        try:
            p = urlparse(s)
            s = p.netloc or p.path or s
        except Exception:
            pass
    s = s.strip().strip("/")
    if "/" in s:
        s = s.split("/", 1)[0]
    return s


def write_status(message: str, progress: int, meta: dict | None = None):
    os.makedirs(data_dir(), exist_ok=True)
    payload = {
        "message": message,
        "progress": int(progress),
        "timestamp": time.time(),
    }
    if meta:
        payload.update(meta)
    try:
        with open(status_path(), "w", encoding="utf-8") as f:
            json.dump(payload, f)
    except Exception:
        pass


def append_log(line: str):
    os.makedirs(data_dir(), exist_ok=True)
    try:
        with open(log_path(), "a", encoding="utf-8") as f:
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
    return os.path.exists(lock_path())

def is_paused():
    return _pause_requested

def pause_requested():
    return _pause_requested

def stop_requested():
    return _stop_requested

def request_pause():
    global _pause_requested
    _pause_requested = True

def request_resume():
    global _pause_requested
    _pause_requested = False

def request_stop():
    global _stop_requested
    _stop_requested = True


def lock():
    os.makedirs(data_dir(), exist_ok=True)
    with open(lock_path(), "w", encoding="utf-8") as f:
        f.write(str(time.time()))


def unlock():
    try:
        if os.path.exists(lock_path()):
            os.remove(lock_path())
    except Exception:
        pass


def sleep_delay():
    if REQUEST_DELAY_SECONDS > 0:
        time.sleep(REQUEST_DELAY_SECONDS)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)


def make_ddgs():
    headers = {"User-Agent": get_random_user_agent()}
    try:
        return DDGS(headers=headers)
    except TypeError:
        return DDGS()


def ddg_text(query: str, max_results: int = 10):
    mock = (os.environ.get("MOCK_SEARCH") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if mock:
        return [
            {
                "title": "Mock Job",
                "href": "https://example.com/job",
                "body": f"mock snippet for {query}",
            }
        ]
    last = None
    for backend in ("lite", "html", None):
        try:
            with make_ddgs() as ddgs:
                if backend is None:
                    return list(ddgs.text(query, max_results=max_results))
                try:
                    return list(
                        ddgs.text(query, max_results=max_results, backend=backend)
                    )
                except TypeError:
                    return list(ddgs.text(query, max_results=max_results))
        except Exception as e:
            last = e
            continue
    if last:
        raise last
    return []


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
                headers={"User-Agent": get_random_user_agent()},
            )

        r = with_retry(fetch)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        return text[:8000]
    except Exception:
        log_event("fetch_requests_failed", url=url)
        return ""


def run_scrape(
    api_key: str,
    lite_mode: bool,
    provider: str | None = "groq",
    api_keys: dict[str, str] | None = None,
    sites: list[str] | None = None,
    keywords: list[str] | None = None,
    cv_text: str | None = None,
):
    global _pause_requested, _stop_requested
    _pause_requested = False
    _stop_requested = False
    
    if is_running():
        log_event("run_rejected", reason="already_running")
        return
    lock()
    try:
        db.init()
        if sites is None:
            sites = read_lines(os.path.join(config_dir(), "sites.txt"))
        if keywords is None:
            keywords = read_lines(os.path.join(config_dir(), "keywords.txt"))
        if cv_text is None:
            cv_text = read_text(os.path.join(config_dir(), "cv.txt"))

        if not keywords:
            write_status(
                "no_keywords",
                0,
                {"running": False, "added": 0, "paused": False},
            )
            log_event("run_invalid", reason="no_keywords")
            return
        
        selected_provider = (provider or "groq").strip().lower()
        keys = {
            "groq": (os.environ.get("GROQ_API_KEY") or "").strip(),
            "anthropic": (os.environ.get("ANTHROPIC_API_KEY") or "").strip(),
            "gemini": (os.environ.get("GEMINI_API_KEY") or "").strip(),
        }
        for k, v in (api_keys or {}).items():
            keys[str(k).strip().lower()] = (v or "").strip()
        if api_key and not keys.get("groq"):
            keys["groq"] = api_key.strip()
        use_ai = bool(keys.get(selected_provider, "")) and not lite_mode
        ai = AIService(selected_provider, keys)
        log_event(
            "run_started",
            provider=selected_provider,
            use_ai=use_ai,
            lite_mode=bool(lite_mode),
            sites=len(sites),
            keywords=len(keywords),
        )
        total = max(1, len(sites) * max(1, len(keywords)))
        done = 0
        added = 0
        write_status("starting", 0, {"running": True, "added": 0, "paused": False})
        
        for site in sites or [""]:
            site_norm = normalize_site(site)
            if stop_requested():
                log_event("run_stopped")
                break
            while pause_requested():
                write_status(
                    "paused",
                    int((done / total) * 100),
                    {"running": True, "added": added, "paused": True},
                )
                time.sleep(1)
                if stop_requested():
                    log_event("run_stopped")
                    break
            if stop_requested():
                break
                
            for kw in keywords or [""]:
                if stop_requested():
                    log_event("run_stopped")
                    break
                while pause_requested():
                    write_status(
                        "paused",
                        int((done / total) * 100),
                        {"running": True, "added": added, "paused": True},
                    )
                    time.sleep(1)
                    if stop_requested():
                        log_event("run_stopped")
                        break
                if stop_requested():
                    break
                    
                query_site = f"site:{site_norm}" if site_norm else ""
                query = " ".join([x for x in [query_site, kw] if x])
                append_log(f"query={query}")
                log_event("query", query=query)
                try:
                    def search():
                        sleep_delay()
                        return ddg_text(query, max_results=10)

                    results = with_retry(search)
                except Exception:
                    log_event("search_failed", query=query)
                    results = []
                for r in results:
                    title = r.get("title") or ""
                    link = r.get("href") or ""
                    snippet = r.get("body") or ""
                    company = site_norm or site
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
                        site=site_norm or site,
                        snippet=snippet,
                        score=score,
                        reasoning=reasoning,
                    )
                    if h:
                        added += 1
                done += 1
                pct = int((done / total) * 100)
                write_status(
                    "running",
                    pct,
                    {"running": True, "added": added, "paused": False},
                )
        if stop_requested():
            write_status(
                "stopped",
                int((done / total) * 100),
                {"running": False, "added": added, "paused": False},
            )
            log_event("run_stopped", added=added)
        else:
            write_status(
                "complete",
                100,
                {"running": False, "added": added, "paused": False},
            )
            log_event("run_complete", added=added)
            try:
                from notifications import check_and_notify

                n = check_and_notify()
                if n > 0:
                    log_event("notifications_sent", count=n)
            except Exception:
                pass
    finally:
        unlock()


@api.get("/health")
def health():
    return {"ok": True}


@api.get("/status")
def status():
    try:
        with open(status_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "message": "idle",
            "progress": 0,
            "running": is_running(),
            "added": 0,
            "paused": False,
        }


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
    keys = {
        "groq": (req.groq_api_key or "").strip(),
        "anthropic": (req.anthropic_api_key or "").strip(),
        "gemini": (req.gemini_api_key or "").strip(),
    }
    t = threading.Thread(
        target=run_scrape,
        args=(
            req.api_key or "",
            bool(req.lite_mode),
            req.provider or "groq",
            keys,
            req.sites,
            req.keywords,
            req.cv_text,
        ),
        daemon=True,
    )
    t.start()
    return {"started": True}


@api.post("/pause")
def pause():
    if not is_running():
        return {"paused": False, "running": False}
    request_pause()
    return {"paused": True, "running": True}


@api.post("/resume")
def resume():
    if not is_running():
        return {"paused": False, "running": False}
    request_resume()
    return {"paused": False, "running": True}


@api.post("/stop")
def stop():
    if not is_running():
        return {"stopping": False, "running": False}
    request_stop()
    request_resume()
    return {"stopping": True, "running": True}
