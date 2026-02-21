from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from openai import OpenAI

# ----------------------------
# Config (env-driven)
# ----------------------------

DEFAULT_MODEL = os.getenv("SMARTNOTE_OPENAI_MODEL", "gpt-4o-mini")
MAX_OUTPUT_TOKENS = int(os.getenv("SMARTNOTE_MAX_OUTPUT_TOKENS", "300"))
MAX_ASKS_PER_SESSION_PER_DAY = int(os.getenv("SMARTNOTE_MAX_ASKS_PER_SESSION_PER_DAY", "30"))

# If you want to hard-disable hosted LLM in some environments
LLM_ENABLED = os.getenv("SMARTNOTE_LLM_ENABLED", "true").lower() in ("1", "true", "yes")


@dataclass
class Usage:
    day_key: str
    asks: int


# In-memory quota tracking (good enough for single instance).
# If you later scale backend replicas, move this to Redis.
_USAGE: Dict[str, Usage] = {}


def _today_key() -> str:
    # UTC day key for consistency across deployments
    return time.strftime("%Y-%m-%d", time.gmtime())


def _check_and_increment_quota(session_id: str) -> Tuple[bool, int]:
    """
    Returns (allowed, remaining).
    """
    sid = (session_id or "").strip()
    if not sid:
        return False, 0

    day = _today_key()
    u = _USAGE.get(sid)

    if u is None or u.day_key != day:
        u = Usage(day_key=day, asks=0)
        _USAGE[sid] = u

    if u.asks >= MAX_ASKS_PER_SESSION_PER_DAY:
        return False, 0

    u.asks += 1
    remaining = MAX_ASKS_PER_SESSION_PER_DAY - u.asks
    return True, remaining


def generate_text(prompt: str, session_id: str) -> Tuple[str, Dict[str, int]]:
    """
    Hosted LLM call (OpenAI Responses API).
    Returns (text, meta) where meta includes remaining quota.
    """
    if not LLM_ENABLED:
        return "LLM is disabled on this server.", {"remaining_asks_today": 0}

    allowed, remaining = _check_and_increment_quota(session_id)
    if not allowed:
        return (
            f"Daily limit reached for this session ({MAX_ASKS_PER_SESSION_PER_DAY} asks/day). Try again tomorrow.",
            {"remaining_asks_today": 0},
        )

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return "Server is missing OPENAI_API_KEY.", {"remaining_asks_today": remaining}

    client = OpenAI(api_key=api_key)

    # Responses API: cap output tokens to cap cost per request
    # max_output_tokens is the recommended knob for response length control
    # (see OpenAI docs). :contentReference[oaicite:3]{index=3}
    resp = client.responses.create(
        model=DEFAULT_MODEL,
        input=prompt,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )

    text = (resp.output_text or "").strip()
    if not text:
        text = "Model returned empty response."

    return text, {"remaining_asks_today": remaining}