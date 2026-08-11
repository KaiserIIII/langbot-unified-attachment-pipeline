from __future__ import annotations

import re
from collections.abc import Callable


VisionCallback = Callable[[bytes, str, str], str]

_REFUSALS = (
    "i cannot see the image",
    "i can't see the image",
    "no image was provided",
    "unable to analyze the image",
    "cannot access the image",
)
_UPLOAD_INSTRUCTIONS = (
    "upload the image",
    "attach the image",
    "provide the image",
    "send the image",
)


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


def sanitize_vision_text(text: str, prompt: str = "") -> str:
    normalized = " ".join(str(text or "").split()).strip()
    if not normalized:
        return ""
    lowered = normalized.casefold()
    if any(pattern in lowered for pattern in _REFUSALS + _UPLOAD_INSTRUCTIONS):
        return ""
    output_tokens = _tokens(normalized)
    prompt_tokens = _tokens(prompt)
    if prompt_tokens and output_tokens:
        overlap = len(output_tokens & prompt_tokens) / max(1, len(output_tokens))
        if overlap >= 0.9 and len(output_tokens) >= 6:
            return ""
    return normalized


def run_vision_with_fallback(
    image: bytes,
    mime_type: str,
    prompt: str,
    primary: VisionCallback,
    fallback: VisionCallback | None = None,
) -> str:
    for callback in (primary, fallback):
        if callback is None:
            continue
        candidate = sanitize_vision_text(callback(image, mime_type, prompt), prompt)
        if candidate:
            return candidate
    return ""
