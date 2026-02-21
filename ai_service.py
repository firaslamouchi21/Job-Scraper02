import json
import re
from openai import OpenAI


class AIService:
    def __init__(self, api_key: str | None):
        self.api_key = api_key or ""
        self.client = None
        if self.api_key:
            self.client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=self.api_key)

    def analyze(self, text: str, cv_text: str, keywords: list[str]):
        if not text:
            return 0, ""
        if not self.client:
            return self.lite_score(text, keywords)
        payload = self.build_prompt(text, cv_text, keywords)
        try:
            completion = self.client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": payload}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw = completion.choices[0].message.content
            obj = json.loads(raw)
            score = int(obj.get("score", 0))
            reasoning = str(obj.get("reasoning", ""))
            return max(0, min(10, score)), reasoning
        except Exception:
            return self.lite_score(text, keywords)

    def build_prompt(self, text: str, cv_text: str, keywords: list[str]):
        k = ", ".join([x for x in keywords if x])
        return f"CV: {cv_text[:4000]}\nKeywords: {k}\nText: {text[:6000]}\nReturn JSON with keys score (int 0-10) and reasoning (string)."

    def lite_score(self, text: str, keywords: list[str]):
        t = text.lower()
        hits = 0
        for kw in keywords:
            w = (kw or "").strip().lower()
            if not w:
                continue
            if re.search(r"\\b" + re.escape(w) + r"\\b", t):
                hits += 1
        score = min(10, max(0, hits))
        return score, f"matched_keywords={hits}"
