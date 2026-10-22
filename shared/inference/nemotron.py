"""Bounded NVIDIA Nemotron text inference transport for fabricated TB-CareOS data.

This is NOT Meterless World Model's event API. No provider is called until
complete() is invoked. Credentials must be in a local ignored environment
file or shell environment; never commit or log secrets.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

NVIDIA_CHAT_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"
ULTRA_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
LIGHTNING_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
_MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9_.-]{1,120}$")


class NemotronError(RuntimeError):
    """Model unavailable or non-conforming; never substitute invented model text."""


class NVIDIAChatClient:
    """Minimal OpenAI-compatible chat-completions client, no third-party deps.

    Intentionally pinned to the documented NVIDIA host, with no
    user-supplied URLs. The model ID is configurable; approval/credits are not
    implied by documented API availability.
    """

    def __init__(self, *, api_key: str | None = None,
                 model: str | None = None, timeout_seconds: int | None = None):
        self.api_key = api_key if api_key is not None else os.environ.get("NVIDIA_API_KEY", "")
        self.model = model or os.environ.get("NEMOTRON_MODEL", DEFAULT_MODEL)
        if not _MODEL_NAME.fullmatch(self.model):
            raise ValueError("NEMOTRON_MODEL must be a provider/model identifier")
        # Hosted Ultra may take longer to produce a complete non-streaming
        # answer. Keep ordinary Nemotron requests at the shorter 75s budget.
        if timeout_seconds is None:
            timeout_seconds = 180 if self.model == ULTRA_MODEL else 75
        if not isinstance(timeout_seconds, int) or not 10 <= timeout_seconds <= 180:
            raise ValueError("Nemotron timeout must be 10 to 180 seconds")
        self.timeout_seconds = timeout_seconds

    def complete(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise NemotronError(
                "NVIDIA_API_KEY not set; create a key in NVIDIA Build and load it privately"
            )
        if len(messages) != 2 or [x.get("role") for x in messages] != ["system", "user"]:
            raise ValueError("Expected exactly one bounded system and one evidence user message")
        if sum(len(x.get("content", "")) for x in messages) > 30_000:
            raise ValueError("Prompt exceeds synthetic evidence budget")
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1600,
            "temperature": 0.2,
            "stream": False,
        }
        # NVIDIA documents reasoning_effort=none for both Nemotron 3 Super and
        # Ultra. The latter otherwise defaults to high reasoning, which may
        # exhaust the bounded output budget before returning strict JSON.
        # Do not assume other model variants support the same field.
        if self.model in (DEFAULT_MODEL, ULTRA_MODEL):
            payload["reasoning_effort"] = "none"
        elif self.model == LIGHTNING_MODEL:
            # NVIDIA Lightning supports chat-template thinking control. Without
            # this, reasoning can consume the 1600-token bounded JSON budget.
            # For direct HTTPS requests, extra_body SDK fields live at top level.
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        req = urllib.request.Request(
            NVIDIA_CHAT_URL,
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read(256_001)
                if len(raw) > 256_000:
                    raise NemotronError("Provider response exceeds bounded size")
        except urllib.error.HTTPError as exc:
            # Avoid disclosing potentially sensitive response bodies and tokens.
            raise NemotronError(f"NVIDIA API HTTP {exc.code}; check key, model access and limits") from exc
        except TimeoutError as exc:
            raise NemotronError(
                f"NVIDIA request timed out (configured timeout {self.timeout_seconds}s)"
            ) from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise NemotronError(
                    f"NVIDIA request timed out (configured timeout {self.timeout_seconds}s)"
                ) from exc
            raise NemotronError("NVIDIA connection failed (network/DNS/TLS)") from exc
        except OSError as exc:
            raise NemotronError("NVIDIA connection failed (socket/network)") from exc

        try:
            obj = json.loads(raw)
            choice = obj["choices"][0]
            finish_reason = choice.get("finish_reason")
            if finish_reason in ("length", "content_filter", "tool_calls"):
                # Report only the documented termination category, never model
                # text or potentially identifying provider response content.
                raise NemotronError(
                    f"Provider did not return a complete text answer (finish_reason={finish_reason})"
                )
            text = choice["message"]["content"]
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Empty model answer")
            return text
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise NemotronError("Provider response is not a valid chat completion") from exc
