import os
import sqlite3
import hashlib
from datetime import datetime, timezone


def data_dir() -> str:
    return os.environ.get("DATA_DIR", "./data")


def db_path() -> str:
    return os.path.join(data_dir(), "jobs.sqlite")


def connect():
    os.makedirs(data_dir(), exist_ok=True)
    conn = sqlite3.connect(db_path(), check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def init():
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS jobs ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "job_hash TEXT UNIQUE, "
        "title TEXT, company TEXT, link TEXT, site TEXT, "
        "snippet TEXT, score INTEGER, reasoning TEXT, created_at TEXT"
        ")"
    )
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
        "INSERT OR IGNORE INTO jobs "
        "(job_hash, title, company, link, site, snippet, score, reasoning, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            h,
            title,
            company,
            link,
            site,
            snippet,
            score,
            reasoning,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    inserted = bool(cur.rowcount)
    conn.commit()
    cur.close()
    conn.close()
    return h if inserted else ""


def list_jobs(limit=200):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM jobs ORDER BY score DESC, created_at DESC LIMIT ?",
        (int(limit),),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def count_jobs() -> int:
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM jobs")
    n = cur.fetchone()["n"]
    cur.close()
    conn.close()
    return int(n)


def get_jobs_since(timestamp: str):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM jobs WHERE created_at > ? ORDER BY score DESC",
        (timestamp,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]
