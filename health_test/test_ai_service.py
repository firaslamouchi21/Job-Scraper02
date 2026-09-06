from job_scraper.ai_service import AIService


class TestLiteScore:

    def setup_method(self):
        self.svc = AIService("groq", {})

    def test_single_keyword_match(self):
        score, reasoning = self.svc.lite_score(
            "We are hiring a Python Developer", ["python"]
        )
        assert score == 1
        assert reasoning == "matched_keywords=1"

    def test_multi_word_keyword_match(self):
        score, _ = self.svc.lite_score(
            "Looking for a Python Developer with Data Engineer experience",
            ["python developer", "data engineer"],
        )
        assert score == 2

    def test_no_match(self):
        score, reasoning = self.svc.lite_score(
            "We are hiring a plumber", ["python", "java"]
        )
        assert score == 0
        assert reasoning == "matched_keywords=0"

    def test_does_not_match_substring_of_a_longer_word(self):
        score, _ = self.svc.lite_score("Senior JavaScript Engineer", ["java"])
        assert score == 0

    def test_score_capped_at_ten(self):
        keywords = [f"kw{i}" for i in range(15)]
        text = " ".join(keywords)
        score, _ = self.svc.lite_score(text, keywords)
        assert score == 10

    def test_empty_and_blank_keywords_ignored(self):
        score, _ = self.svc.lite_score("python developer", ["", "  ", "python"])
        assert score == 1
