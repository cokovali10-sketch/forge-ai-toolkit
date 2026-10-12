"""Local inference providers. Honest availability: probe, never assume.

Ollama: http://localhost:11434 by default (OLLAMA_HOST override).
If no server answers, available() is False and chat() explains why
instead of faking a response.
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderInfo:
    name: str
    available: bool
    models: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    limits: list[str] = field(default_factory=list)
    how_to_connect: str = ""


class OllamaProvider:
    def __init__(self, host: str = "") -> None:
        self.host = (host or os.environ.get("OLLAMA_HOST",
                                            "http://localhost:11434")).rstrip("/")

    def _get(self, path: str, timeout: int = 5) -> Any:
        req = urllib.request.Request(self.host + path,
                                     headers={"User-Agent": "forge/0.1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)

    def available(self, timeout: int = 5) -> bool:
        try:
            self._get("/api/tags", timeout)
            return True
        except Exception:
            return False

    def models(self, timeout: int = 10) -> list[str]:
        try:
            data = self._get("/api/tags", timeout)
            return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
        except Exception:
            return []

    def info(self) -> ProviderInfo:
        if not self.available():
            return ProviderInfo(
                name="ollama", available=False,
                capabilities=["chat (when server runs)"],
                limits=["no server detected; start `ollama serve` first",
                        "no tool-calling assumed; plain chat only"],
                how_to_connect="run `ollama serve`, optionally set OLLAMA_HOST",
            )
        models = self.models()
        return ProviderInfo(
            name="ollama", available=True, models=models,
            capabilities=["chat", "local inference, no external API"],
            limits=["plain chat only; verify tool-calling per model"],
            how_to_connect=f"connected at {self.host}",
        )

    def chat(self, model: str, messages: list[dict], timeout: int = 120) -> dict:
        if not self.available():
            return {"ok": False,
                    "error": "ollama server not reachable; run `ollama serve`"}
        try:
            body = json.dumps({"model": model, "messages": messages,
                               "stream": False}).encode()
            req = urllib.request.Request(
                self.host + "/api/chat", data=body,
                headers={"Content-Type": "application/json",
                         "User-Agent": "forge/0.1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.load(r)
            return {"ok": True, "text": data.get("message", {}).get("content", "")}
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}
