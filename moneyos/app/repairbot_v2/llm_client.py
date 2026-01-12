from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    content: str
    model: str
    mode: str


class OllamaClient:
    def __init__(self, host: str | None = None) -> None:
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.environ.get("OLLAMA_MODEL", "llama3.1")

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate(self, prompt: str) -> LLMResponse:
        payload = json.dumps({"model": self.model, "prompt": prompt, "stream": False}).encode()
        request = urllib.request.Request(f"{self.host}/api/generate", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        return LLMResponse(content=data.get("response", ""), model=self.model, mode="ollama")


class TransformersClient:
    def __init__(self) -> None:
        self.model_name = os.environ.get("TRANSFORMERS_MODEL", "")

    def available(self) -> bool:
        return bool(self.model_name)

    def generate(self, prompt: str) -> LLMResponse:
        from transformers import pipeline

        pipe = pipeline("text-generation", model=self.model_name)
        result = pipe(prompt, max_new_tokens=256)
        text = result[0]["generated_text"]
        return LLMResponse(content=text, model=self.model_name, mode="transformers")


class OpenAIClient:
    def __init__(self) -> None:
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def available(self) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY"))

    def generate(self, prompt: str) -> LLMResponse:
        import openai

        client = openai.OpenAI()
        response = client.responses.create(model=self.model, input=prompt)
        text = response.output_text
        return LLMResponse(content=text, model=self.model, mode="openai")


class HeuristicClient:
    def generate(self, prompt: str) -> LLMResponse:
        _ = prompt
        return LLMResponse(content=json.dumps({"note": "heuristics-only"}), model="heuristics", mode="heuristics")


class LLMRouter:
    def __init__(self) -> None:
        self.ollama = OllamaClient()
        self.transformers = TransformersClient()
        self.openai = OpenAIClient()
        self.heuristic = HeuristicClient()

    def generate(self, prompt: str) -> LLMResponse:
        if self.ollama.available():
            return self.ollama.generate(prompt)
        if self.transformers.available():
            return self.transformers.generate(prompt)
        if self.openai.available():
            return self.openai.generate(prompt)
        return self.heuristic.generate(prompt)
