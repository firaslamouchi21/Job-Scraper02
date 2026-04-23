import os
import smtplib
import requests
from email.mime.text import MIMEText
from datetime import datetime, timezone

NOTIFICATION_WEBHOOK = os.environ.get("NOTIFICATION_WEBHOOK", "")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USER = os.environ.get("EMAIL_USER", "")
EMAIL_PASS = os.environ.get("EMAIL_PASS", "")
EMAIL_TO = os.environ.get("EMAIL_TO", "")
MIN_SCORE_NOTIFY = int(os.environ.get("MIN_SCORE_NOTIFY", "70"))

_last_check_file = os.path.join(os.environ.get("DATA_DIR", "./data"), "last_check.txt")


def get_last_check():
    try:
        with open(_last_check_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "1970-01-01T00:00:00"


def set_last_check(ts: str):
    os.makedirs(os.path.dirname(_last_check_file) or ".", exist_ok=True)
    with open(_last_check_file, "w", encoding="utf-8") as f:
        f.write(ts)


def send_webhook(jobs: list):
    if not NOTIFICATION_WEBHOOK:
        return False
    payload = {
        "text": f"Found {len(jobs)} new matching jobs!",
        "jobs": [
            {"title": j["title"], "score": j["score"], "link": j["link"]}
            for j in jobs[:5]
        ],
    }
    try:
        requests.post(
            NOTIFICATION_WEBHOOK,
            json=payload,
            timeout=15,
            headers={"Content-Type": "application/json"},
        )
        return True
    except Exception:
        return False


def send_email(jobs: list):
    if not all([EMAIL_HOST, EMAIL_USER, EMAIL_PASS, EMAIL_TO]):
        return False
    subject = f"Job Alert: {len(jobs)} new matches found"
    body = "New job matches:\n\n"
    for j in jobs[:10]:
        body += f"• {j['title']} (Score: {j['score']})\n  {j['link']}\n\n"
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as s:
            s.starttls()
            s.login(EMAIL_USER, EMAIL_PASS)
            s.send_message(msg)
        return True
    except Exception:
        return False


def check_and_notify():
    import db

    last = get_last_check()
    jobs = db.get_jobs_since(last)
    high_score = [j for j in jobs if j.get("score", 0) >= MIN_SCORE_NOTIFY]
    if high_score:
        send_webhook(high_score)
        send_email(high_score)
    set_last_check(datetime.now(timezone.utc).isoformat())
    return len(high_score)
