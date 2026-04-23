import os
import time
import requests
import streamlit as st
import db

DATA_DIR = os.environ.get("DATA_DIR", "./data")
SCRAPER_URL = os.environ.get("SCRAPER_URL", "http://localhost:8000")


def fetch_status():
    try:
        r = requests.get(f"{SCRAPER_URL}/status", timeout=3)
        return r.json()
    except Exception:
        return {"message": "offline", "progress": 0, "running": False, "added": 0, "paused": False}


def parse_lines(raw: str):
    return [x.strip() for x in str(raw or "").splitlines() if x.strip()]


def trigger(
    provider: str,
    groq_api_key: str,
    anthropic_api_key: str,
    gemini_api_key: str,
    lite_mode: bool,
    sites: list[str],
    keywords: list[str],
    cv_text: str,
):
    payload = {
        "provider": provider,
        "api_key": groq_api_key or "",
        "groq_api_key": groq_api_key or "",
        "anthropic_api_key": anthropic_api_key or "",
        "gemini_api_key": gemini_api_key or "",
        "lite_mode": bool(lite_mode),
        "sites": sites,
        "keywords": keywords,
        "cv_text": cv_text,
    }
    try:
        r = requests.post(f"{SCRAPER_URL}/run", json=payload, timeout=5)
        r.raise_for_status()
        return True, ""
    except Exception as e:
        return False, str(e)


def control(action: str):
    try:
        r = requests.post(f"{SCRAPER_URL}/{action}", timeout=5)
        r.raise_for_status()
        return True, ""
    except Exception as e:
        return False, str(e)


def main():
    st.set_page_config(page_title="Job Scraper Tool by Firas Lamouchi", layout="wide")
    db.init()

    st.title("Job Scraper Tool by Firas Lamouchi")

    if "show_about" not in st.session_state:
        st.session_state.show_about = False

    with st.sidebar:
        st.header("Run")
        if st.button("About"):
            st.session_state.show_about = not bool(st.session_state.show_about)
        if st.session_state.show_about:
            st.markdown(
                "This app runs a job search and stores results in SQLite. "
                "You can run in Lite mode (keyword scoring) or use an AI provider key."
            )
        provider = st.selectbox(
            "AI Provider",
            options=["groq", "anthropic", "gemini"],
            index=0,
        )
        groq_api_key = st.text_input("Groq API Key", type="password")
        anthropic_api_key = st.text_input("Anthropic API Key", type="password")
        gemini_api_key = st.text_input("Gemini API Key", type="password")
        provider_to_key = {
            "groq": groq_api_key,
            "anthropic": anthropic_api_key,
            "gemini": gemini_api_key,
        }
        selected_key = provider_to_key.get(provider, "")
        lite_mode = st.toggle("Lite Mode", value=False)
        st.divider()
        st.header("Inputs")
        default_sites = st.session_state.get("sites_raw", "")
        default_keywords = st.session_state.get("keywords_raw", "")
        default_cv = st.session_state.get("cv_text", "")
        sites_raw = st.text_area("Sites (one per line, optional)", value=default_sites, height=120)
        keywords_raw = st.text_area("Keywords (one per line)", value=default_keywords, height=160)
        cv_text = st.text_area("CV / Profile text", value=default_cv, height=180)
        st.session_state.sites_raw = sites_raw
        st.session_state.keywords_raw = keywords_raw
        st.session_state.cv_text = cv_text
        sites = parse_lines(sites_raw)
        keywords = parse_lines(keywords_raw)
        if st.button("Start"):
            ok, err = trigger(
                provider=provider,
                groq_api_key=groq_api_key,
                anthropic_api_key=anthropic_api_key,
                gemini_api_key=gemini_api_key,
                lite_mode=lite_mode or (not bool(selected_key)),
                sites=sites,
                keywords=keywords,
                cv_text=cv_text,
            )
            if ok:
                st.success("Run started")
            else:
                st.error(f"Failed to start run: {err}")

        st.divider()
        st.header("Controls")
        cols = st.columns(3)
        if cols[0].button("Pause"):
            ok, err = control("pause")
            if not ok:
                st.error(err)
        if cols[1].button("Resume"):
            ok, err = control("resume")
            if not ok:
                st.error(err)
        if cols[2].button("Stop"):
            ok, err = control("stop")
            if not ok:
                st.error(err)

        if st.button("Restart Run"):
            control("stop")
            for _ in range(40):
                s = fetch_status()
                if not bool(s.get("running", False)):
                    break
                time.sleep(0.25)
            ok, err = trigger(
                provider=provider,
                groq_api_key=groq_api_key,
                anthropic_api_key=anthropic_api_key,
                gemini_api_key=gemini_api_key,
                lite_mode=lite_mode or (not bool(selected_key)),
                sites=sites,
                keywords=keywords,
                cv_text=cv_text,
            )
            if ok:
                st.success("Run restarted")
            else:
                st.error(f"Failed to restart run: {err}")

    col1, col2 = st.columns([1, 2])
    with col1:
        status = fetch_status()
        st.metric("Status", status.get("message", ""))
        st.progress(int(status.get("progress", 0)) / 100)
        st.metric("Running", bool(status.get("running", False)))
        st.metric("Paused", bool(status.get("paused", False)))
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
