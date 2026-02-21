import os
import sqlite3
import hashlib
from datetime import datetime

DATA_DIR = os.environ.get("DATA_DIR", "/data")
DB_PATH = os.path.join(DATA_DIR, "jobs.sqlite")


def connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    conn = connect()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, job_hash TEXT UNIQUE, title TEXT, company TEXT, link TEXT, site TEXT, snippet TEXT, score INTEGER, reasoning TEXT, created_at TEXT)")
    conn.commit()
    cur.close()
    conn.close()


def job_hash(title: str, site: str, link: str) -> str:
    raw = f"{title}|{site}|{link}".encode("utf-8")
    return hashlib.md5(raw).hexdigest()


def upsert_job(title, company, link, site, snippet, score, reasoning):
    h = job_hash(title or "", site or "", link or "")
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO jobs (job_hash, title, company, link, site, snippet, score, reasoning, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (h, title, company, link, site, snippet, score, reasoning, datetime.utcnow().isoformat()),
    )
    conn.commit()
    cur.close()
    conn.close()
    return h


def list_jobs(limit=200):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (int(limit),))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]
