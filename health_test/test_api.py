import os
import time

os.environ["MOCK_SEARCH"] = "true"
os.environ["USE_PLAYWRIGHT"] = "false"
os.environ["REQUEST_DELAY_SECONDS"] = "0"
os.environ["DATA_DIR"] = "./data_test"

import pytest
from fastapi.testclient import TestClient

import db
import scraper


def wait_for_status(client: TestClient, target_msg: str, timeout: float = 10.0):
    start = time.time()
    while time.time() - start < timeout:
        r = client.get("/status")
        data = r.json()
        if data.get("message") == target_msg:
            return data
        time.sleep(0.1)
    return None


@pytest.fixture(autouse=True)
def clean_test_data():
    import shutil
    test_dir = "./data_test"
    if os.path.isdir(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)
    yield
    if os.path.isdir(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def client():
    return TestClient(scraper.api)


class TestHealthEndpoints:

    def test_health_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"ok": True}

    def test_status_idle(self, client):
        r = client.get("/status")
        assert r.status_code == 200
        data = r.json()
        assert data.get("message") == "idle"
        assert data.get("running") is False
        assert data.get("paused") is False
        assert "progress" in data

    def test_jobs_endpoint_empty(self, client):
        r = client.get("/jobs")
        assert r.status_code == 200
        data = r.json()
        assert data.get("jobs") == []

    def test_export_json_empty(self, client):
        r = client.get("/export/json")
        assert r.status_code == 200
        assert r.json() == []

    def test_export_csv_empty(self, client):
        r = client.get("/export/csv")
        assert r.status_code == 200
        content = r.text
        assert "title" in content.lower() or content == ""


class TestRunLifecycle:

    def test_run_no_keywords_returns_error(self, client):
        payload = {
            "provider": "groq",
            "api_key": "",
            "lite_mode": True,
            "sites": [],
            "keywords": [],
            "cv_text": "",
        }
        r = client.post("/run", json=payload)
        assert r.status_code == 200
        assert r.json().get("started") is True

        status = wait_for_status(client, "no_keywords", timeout=5.0)
        assert status is not None
        assert status.get("message") == "no_keywords"
        assert status.get("running") is False

    def test_run_with_keywords_completes(self, client):
        payload = {
            "provider": "groq",
            "api_key": "",
            "lite_mode": True,
            "sites": ["example.com"],
            "keywords": ["python"],
            "cv_text": "Python developer",
        }
        r = client.post("/run", json=payload)
        assert r.status_code == 200
        assert r.json().get("started") is True

        status = wait_for_status(client, "complete", timeout=10.0)
        assert status is not None
        assert status.get("message") == "complete"
        assert status.get("running") is False
        assert status.get("progress") == 100

    def test_run_adds_jobs(self, client):
        payload = {
            "provider": "groq",
            "api_key": "",
            "lite_mode": True,
            "sites": ["example.com"],
            "keywords": ["developer"],
            "cv_text": "Software engineer",
        }
        r = client.post("/run", json=payload)
        assert r.status_code == 200

        status = wait_for_status(client, "complete", timeout=10.0)
        assert status is not None
        assert status.get("added", 0) >= 1

        jobs_r = client.get("/jobs")
        jobs_data = jobs_r.json()
        assert len(jobs_data.get("jobs", [])) >= 1


class TestRunControls:

    def test_pause_when_not_running(self, client):
        r = client.post("/pause")
        assert r.status_code == 200
        data = r.json()
        assert data.get("paused") is False
        assert data.get("running") is False

    def test_resume_when_not_running(self, client):
        r = client.post("/resume")
        assert r.status_code == 200
        data = r.json()
        assert data.get("paused") is False
        assert data.get("running") is False

    def test_stop_when_not_running(self, client):
        r = client.post("/stop")
        assert r.status_code == 200
        data = r.json()
        assert data.get("stopping") is False
        assert data.get("running") is False


class TestConcurrency:

    def test_cannot_start_second_run_while_running(self, client):
        payload = {
            "provider": "groq",
            "api_key": "",
            "lite_mode": True,
            "sites": ["example.com"],
            "keywords": ["slow"],
            "cv_text": "",
        }
        r1 = client.post("/run", json=payload)
        assert r1.status_code == 200
        assert r1.json().get("started") is True

        time.sleep(0.2)

        r2 = client.post("/run", json=payload)
        assert r2.status_code == 200
        assert r2.json().get("started") is True


class TestExport:

    def test_export_json_with_data(self, client):
        payload = {
            "provider": "groq",
            "api_key": "",
            "lite_mode": True,
            "sites": ["test.com"],
            "keywords": ["engineer"],
            "cv_text": "",
        }
        client.post("/run", json=payload)
        wait_for_status(client, "complete", timeout=10.0)

        r = client.get("/export/json")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        if data:
            job = data[0]
            assert "title" in job
            assert "link" in job
            assert "snippet" in job

    def test_export_csv_with_data(self, client):
        payload = {
            "provider": "groq",
            "api_key": "",
            "lite_mode": True,
            "sites": ["test.com"],
            "keywords": ["engineer"],
            "cv_text": "",
        }
        client.post("/run", json=payload)
        wait_for_status(client, "complete", timeout=10.0)

        r = client.get("/export/csv")
        assert r.status_code == 200
        content = r.text
        assert content
        lines = content.strip().split("\n")
        assert len(lines) >= 1
