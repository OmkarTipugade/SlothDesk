"""
SlothDesk Ollama HTTP client.

Communicates with a locally running Ollama instance via its REST API.
Never falls back to a cloud model.  Never starts Ollama automatically.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Base class for Ollama-related errors with user-safe messages."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


class OllamaNotRunning(OllamaError):
    """Ollama service is unreachable."""

    def __init__(self) -> None:
        super().__init__(
            "Ollama is not running. Start it with 'ollama serve' or open the Ollama app.",
            status_code=503,
        )


class OllamaModelNotFound(OllamaError):
    """The requested model is not downloaded."""

    def __init__(self, model: str) -> None:
        super().__init__(
            f"Model '{model}' is not available. Run 'ollama pull {model}' to download it.",
            status_code=503,
        )


class OllamaTimeout(OllamaError):
    """Request to Ollama timed out."""

    def __init__(self) -> None:
        super().__init__(
            "The Ollama request timed out. The model may be loading or the system is under heavy load. "
            "Try again or increase OLLAMA_TIMEOUT_SECONDS.",
            status_code=504,
        )


class OllamaBadResponse(OllamaError):
    """Ollama returned an unparseable or invalid response."""

    def __init__(self, detail: str = "") -> None:
        msg = "Ollama returned an invalid response."
        if detail:
            msg += f" {detail}"
        super().__init__(msg, status_code=502)


class OllamaClient:
    """Async HTTP client for the local Ollama API."""

    def __init__(self, base_url: str, model: str, timeout_seconds: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = httpx.Timeout(
            connect=10.0,
            read=float(timeout_seconds),
            write=10.0,
            pool=10.0,
        )
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ── Health Checks ───────────────────────────────────────────

    async def is_available(self) -> bool:
        """Return True if Ollama is reachable."""
        try:
            client = await self._get_client()
            resp = await client.get("/")
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.ConnectTimeout, OSError):
            return False

    async def is_model_available(self) -> bool:
        """Return True if the configured model is downloaded."""
        try:
            client = await self._get_client()
            resp = await client.get("/api/tags")
            if resp.status_code != 200:
                return False
            data = resp.json()
            models = data.get("models", [])
            # Ollama model names may or may not include the tag
            for m in models:
                name = m.get("name", "")
                if name == self.model or name.startswith(self.model + ":"):
                    return True
                # Also match without tag suffix
                base_name = name.split(":")[0]
                if base_name == self.model.split(":")[0]:
                    return True
            return False
        except (httpx.ConnectError, httpx.ConnectTimeout, OSError):
            return False
        except (json.JSONDecodeError, KeyError):
            return False

    # ── Chat ────────────────────────────────────────────────────

    async def chat(
        self,
        messages: List[Dict[str, str]],
        json_schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.2,
    ) -> str:
        """
        Send a chat request to Ollama and return the assistant's message content.

        Parameters
        ----------
        messages : list of dicts with 'role' and 'content'
        json_schema : optional JSON schema for structured output
        temperature : sampling temperature (lower = more deterministic)

        Returns
        -------
        The raw text content of the assistant's response.

        Raises
        ------
        OllamaNotRunning, OllamaModelNotFound, OllamaTimeout, OllamaBadResponse
        """
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 4096,
                "num_predict": 2048,
            },
        }

        if json_schema is not None:
            payload["format"] = json_schema

        try:
            client = await self._get_client()
            resp = await client.post("/api/chat", json=payload)
        except (httpx.ConnectError, httpx.ConnectTimeout, OSError):
            raise OllamaNotRunning()
        except httpx.ReadTimeout:
            raise OllamaTimeout()

        if resp.status_code == 404:
            raise OllamaModelNotFound(self.model)

        if resp.status_code != 200:
            logger.error("Ollama returned HTTP %d: %s", resp.status_code, resp.text[:500])
            raise OllamaBadResponse(f"HTTP {resp.status_code}")

        # Parse response
        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError):
            raise OllamaBadResponse("Response is not valid JSON.")

        # Extract message content
        message = data.get("message")
        if not isinstance(message, dict):
            raise OllamaBadResponse("Response missing 'message' field.")

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise OllamaBadResponse("Response message has no content.")

        return content.strip()
