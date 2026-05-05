"""
Shared OpenRouter LLM client
=============================
A thin wrapper around the OpenRouter API (OpenAI-compatible endpoint).
All pipeline stages import from here — one place to change model or config.

Setup:
    Add to your .env file:
        OPENROUTER_API_KEY=sk-or-...
        OPENROUTER_MODEL=any model on openrouter.ai/models
"""

import os
import logging
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

OPENROUTER_BASE_URL = os.getenv("OPENAI_API_BASE")
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")


class OpenRouterClient:
    """
    Minimal synchronous client for the OpenRouter chat completions API.
 
    Usage:
        client = OpenRouterClient()
        reply = client.chat("Summarise this in 3 sentences: ...")
    """
 
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        site_url: str = "https://github.com/yt-comment-pipeline",
        site_name: str = "YT Comment Analysis Pipeline",
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise EnvironmentError(
                "OpenRouter API key not found. "
                "Set OPENROUTER_API_KEY in your .env file or pass api_key=."
            )
        self.model = model or DEFAULT_MODEL
        self.site_url = site_url
        self.site_name = site_name
        log.info("OpenRouterClient initialised — model: %s", self.model)
 
    def chat(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.3,
    ) -> str:
        """
        Send a single-turn chat prompt and return the assistant reply as a string.
 
        Args:
            prompt:      User message content.
            system:      Optional system prompt to set tone / role.
            max_tokens:  Maximum tokens in the response.
            temperature: Sampling temperature (lower = more deterministic).
 
        Returns:
            Assistant reply text.
 
        Raises:
            requests.HTTPError: On non-2xx API responses.
            KeyError:           If the response structure is unexpected.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
 
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
 
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.site_name,
            "Content-Type": "application/json",
        }
 
        log.debug("OpenRouter request — model=%s, prompt_chars=%d", self.model, len(prompt))
 
        response = requests.post(
            OPENROUTER_BASE_URL,
            json=payload,
            headers=headers,
            timeout=60,
        )
 
        # Decode body first so we can show useful error messages
        raw_body = response.text.strip()
 
        if not response.ok:
            # Try to pull a human-readable message out of the error body
            try:
                err_data = response.json()
                err_msg = (
                    err_data.get("error", {}).get("message")
                    or err_data.get("error")
                    or raw_body
                )
            except Exception:
                err_msg = raw_body or f"HTTP {response.status_code}"
            raise RuntimeError(
                f"OpenRouter API error {response.status_code}: {err_msg}"
            )
 
        if not raw_body:
            raise RuntimeError("OpenRouter returned an empty response body.")
 
        try:
            data = response.json()
        except Exception as exc:
            raise RuntimeError(
                f"OpenRouter response is not valid JSON. "
                f"Status: {response.status_code}. Body: {raw_body[:200]!r}"
            ) from exc
 
        # Surface any API-level error messages cleanly
        if "error" in data:
            raise RuntimeError(f"OpenRouter error: {data['error']}")
 
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(
                f"OpenRouter returned no choices. Full response: {data}"
            )
 
        content = choices[0].get("message", {}).get("content") or ""
        if not content.strip():
            finish_reason = choices[0].get("finish_reason", "unknown")
            raise RuntimeError(
                f"OpenRouter returned an empty message content "
                f"(finish_reason={finish_reason!r}). "
                f"This usually means the model hit a content filter or token limit."
            )
 
        reply = content.strip()
        log.debug("OpenRouter reply — %d chars", len(reply))
        return reply
 
    def chat_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.1,
    ) -> dict:
        """
        Like `chat()` but instructs the model to respond with JSON and
        parses the response automatically.
 
        Useful for structured outputs (e.g. sentiment labels, topic lists).
 
        Returns:
            Parsed dict / list from the model's JSON response.
 
        Raises:
            ValueError: If the response is not valid JSON.
        """
        import json
        import re
 
        json_system = (system or "") + (
            "\n\nRespond ONLY with valid JSON. "
            "No markdown fences, no explanations, no extra text."
        )
 
        raw = self.chat(
            prompt=prompt,
            system=json_system.strip(),
            max_tokens=max_tokens,
            temperature=temperature,
        )
 
        # Strip markdown code fences if the model ignores instructions
        clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
 
        try:
            return json.loads(clean)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Model did not return valid JSON.\nRaw response:\n{raw}"
            ) from exc
 
 
# ---------------------------------------------------------------------------
# Module-level convenience — lazily instantiated singleton
# ---------------------------------------------------------------------------
 
_default_client: Optional[OpenRouterClient] = None
 
 
def get_client(model: Optional[str] = None) -> OpenRouterClient:
    """
    Return a shared OpenRouterClient instance (or create one if not yet initialised).
    Pass `model` to override the default from the env var.
    """
    global _default_client
    if _default_client is None or model:
        _default_client = OpenRouterClient(model=model)
    return _default_client