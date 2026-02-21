import os
import time
import requests
import streamlit as st
import db

DATA_DIR = os.environ.get("DATA_DIR", "/data")
CONFIG_DIR = os.environ.get("CONFIG_DIR", "config")
SCRAPER_URL = os.environ.get("SCRAPER_URL", "http://localhost:8000")


def read_text(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def write_text(path: str, value: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(value or "")


def fetch_status():
    try:
        r = requests.get(f"{SCRAPER_URL}/status", timeout=3)
        return r.json()
    except Exception:
        return {"message": "offline", "progress": 0, "running": False}


def trigger(api_key: str, lite_mode: bool):
    payload = {"api_key": api_key or "", "lite_mode": bool(lite_mode)}
    requests.post(f"{SCRAPER_URL}/run", json=payload, timeout=5)


def main():
    st.set_page_config(page_title="Job Scraper Tool by Firas Lamouchi", layout="wide")
    db.init()

    st.title("Job Scraper Tool by Firas Lamouchi")

    with st.sidebar:
        st.header("Run")
        api_key = st.text_input("Groq API Key", type="password")
        lite_mode = st.toggle("Lite Mode", value=False)
        if st.button("Start"):
            trigger(api_key, lite_mode or (not bool(api_key)))
        st.divider()
        st.header("Config")
        sites_path = os.path.join(CONFIG_DIR, "sites.txt")
        keywords_path = os.path.join(CONFIG_DIR, "keywords.txt")
        cv_path = os.path.join(CONFIG_DIR, "cv.txt")
        sites_val = st.text_area(
            "sites.txt",
            value=read_text(sites_path),
            height=150,
        )
        keywords_val = st.text_area(
            "keywords.txt",
            value=read_text(keywords_path),
            height=150,
        )
        cv_val = st.text_area("cv.txt", value=read_text(cv_path), height=200)
        if st.button("Save Config"):
            write_text(
                sites_path,
                sites_val.strip() + "\n" if sites_val.strip() else "",
            )
            write_text(
                keywords_path,
                keywords_val.strip() + "\n" if keywords_val.strip() else "",
            )
            write_text(cv_path, cv_val)

    col1, col2 = st.columns([1, 2])
    with col1:
        status = fetch_status()
        st.metric("Status", status.get("message", ""))
        st.progress(int(status.get("progress", 0)) / 100)
        st.metric("Running", bool(status.get("running", False)))
        st.metric("Added", int(status.get("added", 0) or 0))
        if st.button("Refresh"):
            st.rerun()

    with col2:
        jobs = db.list_jobs(limit=200)
        st.metric("Jobs", len(jobs))
        for j in jobs:
            with st.container(border=True):
                st.subheader(j.get("title") or "")
                st.caption(j.get("link") or "")
                st.write(j.get("snippet") or "")
                st.write({"score": j.get("score"), "reasoning": j.get("reasoning")})

    time.sleep(0.1)


if __name__ == "__main__":
    main()
