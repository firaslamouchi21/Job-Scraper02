import time

from job_scraper import db


class TestListJobsOrdering:

    def test_higher_score_ranks_first_regardless_of_recency(self):
        db.init()
        db.upsert_job(
            title="Old but great match",
            company="a",
            link="https://example.com/a",
            site="a",
            snippet="",
            score=9,
            reasoning="",
        )
        db.upsert_job(
            title="Newer but weak match",
            company="b",
            link="https://example.com/b",
            site="b",
            snippet="",
            score=2,
            reasoning="",
        )
        jobs = db.list_jobs(limit=10)
        assert [j["title"] for j in jobs] == [
            "Old but great match",
            "Newer but weak match",
        ]

    def test_ties_broken_by_recency(self):
        db.init()
        db.upsert_job(
            title="First",
            company="a",
            link="https://example.com/a",
            site="a",
            snippet="",
            score=5,
            reasoning="",
        )
        time.sleep(0.01)
        db.upsert_job(
            title="Second",
            company="b",
            link="https://example.com/b",
            site="b",
            snippet="",
            score=5,
            reasoning="",
        )
        jobs = db.list_jobs(limit=10)
        titles = [j["title"] for j in jobs]
        assert titles[0] == "Second"
        assert set(titles) == {"First", "Second"}
