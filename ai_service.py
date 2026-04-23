import json
import re
import requests
from openai import OpenAI


class AIService:
    def __init__(self, provider: str | None, api_keys: dict[str, str] | None = None):
        self.provider = (provider or "groq").strip().lower()
        self.api_keys = {
            "groq": "",
            "anthropic": "",
            "gemini": "",
        }
        for k, v in (api_keys or {}).items():
            self.api_keys[str(k).strip().lower()] = (v or "").strip()
        self.client = None
        if self.provider == "groq" and self.api_keys.get("groq"):
            self.client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=self.api_keys["groq"],
            )
        if self.provider == "gemini" and self.api_keys.get("gemini"):
            self.client = OpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=self.api_keys["gemini"],
            )

    def analyze(self, text: str, cv_text: str, keywords: list[str]):
        if not text:
            return 0, ""
        if self.provider == "anthropic" and self.api_keys.get("anthropic"):
            return self.analyze_anthropic(text, cv_text, keywords)
        if not self.client:
            return self.lite_score(text, keywords)
        model = "llama3-70b-8192"
        if self.provider == "gemini":
            model = "gemini-2.0-flash"
        payload = self.build_prompt(text, cv_text, keywords)
        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": payload}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            return self.parse_score_and_reasoning(completion.choices[0].message.content)
        except Exception:
            return self.lite_score(text, keywords)

    def analyze_anthropic(self, text: str, cv_text: str, keywords: list[str]):
        payload = self.build_prompt(text, cv_text, keywords)
        try:
            res = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_keys.get("anthropic", ""),
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-3-5-haiku-latest",
                    "max_tokens": 220,
                    "temperature": 0.1,
                    "messages": [{"role": "user", "content": payload}],
                },
                timeout=25,
            )
            res.raise_for_status()
            obj = res.json()
            content = obj.get("content") or []
            raw = ""
            if content and isinstance(content, list):
                raw = str((content[0] or {}).get("text") or "")
            return self.parse_score_and_reasoning(raw)
        except Exception:
            return self.lite_score(text, keywords)

    def parse_score_and_reasoning(self, raw: str | None):
        text = str(raw or "").strip()
        if not text:
            return 0, ""
        obj = None
        try:
            obj = json.loads(text)
        except Exception:
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                try:
                    obj = json.loads(m.group(0))
                except Exception:
                    obj = None
        if not isinstance(obj, dict):
            return self.lite_score(text, [])
        score = int(obj.get("score", 0))
        reasoning = str(obj.get("reasoning", ""))
        return max(0, min(10, score)), reasoning

    def build_prompt(self, text: str, cv_text: str, keywords: list[str]):
        k = ", ".join([x for x in keywords if x])
        return (
            f"CV: {cv_text[:4000]}\n"
            f"Keywords: {k}\n"
            f"Text: {text[:6000]}\n"
            "Return JSON with keys score (int 0-10) and reasoning (string)."
        )

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
