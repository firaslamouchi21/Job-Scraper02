from job_scraper import db, notifications


class TestMinScoreNotifyScale:

    def test_default_threshold_is_reachable_on_the_0_to_10_score_scale(self):
        assert 0 <= notifications.MIN_SCORE_NOTIFY <= 10

    def test_check_and_notify_fires_for_job_scoring_above_threshold(self, monkeypatch):
        db.init()
        sent = {}
        monkeypatch.setattr(
            notifications, "send_webhook", lambda jobs: sent.setdefault("webhook", jobs)
        )
        monkeypatch.setattr(
            notifications, "send_email", lambda jobs: sent.setdefault("email", jobs)
        )
        notifications.set_last_check("1970-01-01T00:00:00")
        db.upsert_job(
            title="Great match",
            company="a",
            link="https://example.com/a",
            site="a",
            snippet="",
            score=8,
            reasoning="",
        )
        db.upsert_job(
            title="Weak match",
            company="b",
            link="https://example.com/b",
            site="b",
            snippet="",
            score=2,
            reasoning="",
        )
        count = notifications.check_and_notify()
        assert count == 1
        assert [j["title"] for j in sent["webhook"]] == ["Great match"]
        assert [j["title"] for j in sent["email"]] == ["Great match"]

    def test_check_and_notify_does_not_fire_when_nothing_qualifies(self, monkeypatch):
        db.init()
        called = []
        monkeypatch.setattr(notifications, "send_webhook", lambda jobs: called.append(jobs))
        monkeypatch.setattr(notifications, "send_email", lambda jobs: called.append(jobs))
        notifications.set_last_check("1970-01-01T00:00:00")
        db.upsert_job(
            title="Weak match",
            company="a",
            link="https://example.com/a",
            site="a",
            snippet="",
            score=1,
            reasoning="",
        )
        count = notifications.check_and_notify()
        assert count == 0
        assert called == []
