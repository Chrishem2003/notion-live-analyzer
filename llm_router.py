"""
llm_router.py
Hybrid LLM Router  the "Local Hybrid Fallback Wrapper".

Strategy:
  1. Light text processing / embeddings  -> local Ollama (fast, private, free).
  2. Heavy cross-sector synthesis         -> Google Gemini API (google-genai).
  3. Deterministic template fallback      -> works fully offline (no API key).

Env vars:
  GEMINI_API_KEY       -> enables Gemini heavy synthesis.
  OLLAMA_BASE_URL      -> default http://localhost:11434
  OLLAMA_MODEL         -> e.g. llama3.1, mistral, gemma2 (default llama3)
"""
from __future__ import annotations

import os
import json
import re
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Optional SDKs
# ---------------------------------------------------------------------------
try:
    from google import genai
    from google.genai import types

    HAS_GOOGLE_GENAI = True
except Exception:  # pragma: no cover
    HAS_GOOGLE_GENAI = False

try:
    import requests

    HAS_REQUESTS = True
except Exception:
    HAS_REQUESTS = False


class LLMRouter:
    """Routes prompts to the best available model with graceful fallback."""

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
        ollama_model: Optional[str] = None,
    ):
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        self.ollama_base_url = ollama_base_url or os.environ.get(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self.ollama_model = ollama_model or os.environ.get("OLLAMA_MODEL", "llama3")
        self._gemini_client = None

        if HAS_GOOGLE_GENAI and self.gemini_api_key:
            try:
                self._gemini_client = genai.Client(api_key=self.gemini_api_key)
            except Exception:
                self._gemini_client = None

    # ------------------------------------------------------------------
    # Health / availability
    # ------------------------------------------------------------------
    def available_backends(self) -> Dict[str, bool]:
        return {
            "gemini": self._gemini_client is not None,
            "ollama": self._ollama_available(),
            "deterministic": True,  # always available
        }

    def _ollama_available(self) -> bool:
        if not HAS_REQUESTS:
            return False
        try:
            r = requests.get(f"{self.ollama_base_url}/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------
    def generate(self, prompt: str, *, task: str = "general", temperature: float = 0.4) -> str:
        """Generate text using the appropriate backend for the task weight."""
        if task in ("embedding", "light", "extractive", "summarize_short"):
            # Light task -> prefer Ollama (fast / local / free)
            out = self._ollama_generate(prompt, temperature=min(temperature, 0.3))
            if out:
                return out
        else:
            # Heavy synthesis -> prefer Gemini
            out = self._gemini_generate(prompt, temperature=temperature)
            if out:
                return out
            out = self._ollama_generate(prompt, temperature=temperature)
            if out:
                return out

        # Deterministic fallback (always works)
        return self._deterministic(prompt, task)

    def synthesize(self, prompt: str, *, task: str = "cross_sector_synthesis") -> str:
        """Alias for heavy cross-sector synthesis."""
        return self.generate(prompt, task=task, temperature=0.5)

    # ------------------------------------------------------------------
    # Backends
    # ------------------------------------------------------------------
    def _gemini_generate(self, prompt: str, temperature: float = 0.4) -> Optional[str]:
        if not self._gemini_client:
            return None
        try:
            model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
            response = self._gemini_client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=2048,
                ),
            )
            text = response.text or ""
            return text.strip() or None
        except Exception:
            return None

    def _ollama_generate(self, prompt: str, temperature: float = 0.4) -> Optional[str]:
        if not HAS_REQUESTS:
            return None
        try:
            r = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": temperature},
                },
                timeout=60,
            )
            if r.status_code == 200:
                data = r.json()
                return (data.get("response") or "").strip() or None
        except Exception:
            return None
        return None

    def _deterministic(self, prompt: str, task: str) -> str:
        """Offline template-based synthesis (no model required)."""
        topic_match = re.search(r"['\"]?([^'\"]{10,120})['\"]?", prompt)
        topic = topic_match.group(1) if topic_match else "the identified challenge"

        if task == "cross_sector_synthesis":
            return (
                f"# Evidence-Based Action Plan\n\n"
                f"**Objective:** {topic}\n\n"
                f"1. **Establish baseline telemetry** on all relevant sector indicators.\n"
                f"2. **Ingest & audit** structured and unstructured data sources.\n"
                f"3. **Deploy targeted interventions** validated by peer-reviewed literature.\n"
                f"4. **Monitor, evaluate, and iterate** with automated feedback loops.\n\n"
                f"*[Deterministic mode: enable Gemini/Ollama for richer synthesis.]*"
            )
        if task == "summarize_short":
            words = prompt.split()[:60]
            return " ".join(words) + ("…" if len(prompt.split()) > 60 else "")
        return f"Routed response ({task}): {topic} — see enterprise guidelines."

    # ------------------------------------------------------------------
    # Embeddings (Graph-RAG support)
    # ------------------------------------------------------------------
    def embed_text(self, text: str) -> List[float]:
        """Return a deterministic embedding vector (SHA-256 bag-of-characters)."""
        # Lightweight, dependency-free embedding fallback. In production,
        # swap for Ollama `nomic-embed-text` (vector dim 768) or Gemini embeddings.
        try:
            out = self._ollama_embed(text)
            if out:
                return out
        except Exception:
            pass
        return self._hash_embedding(text, dim=64)

    def _ollama_embed(self, text: str) -> Optional[List[float]]:
        if not HAS_REQUESTS:
            return None
        try:
            r = requests.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text[:2000]},
                timeout=30,
            )
            if r.status_code == 200:
                emb = r.json().get("embedding")
                if emb:
                    return emb
        except Exception:
            pass
        return None

    @staticmethod
    def _hash_embedding(text: str, dim: int = 64) -> List[float]:
        import hashlib

        vec = [0.0] * dim
        for i, ch in enumerate(text):
            h = int(hashlib.sha256(text[i : i + 1].encode("utf-8")).hexdigest(), 16)
            vec[i % dim] += (h % 1000) / 1000.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [round(v / norm, 6) for v in vec]


# Singleton for app-wide use
_router_instance: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter()
    return _router_instance

