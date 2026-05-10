from __future__ import annotations

import anthropic

PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {
        "input":          3.00 / 1_000_000,
        "output":         15.00 / 1_000_000,
        "cache_read":     0.30 / 1_000_000,
        "cache_creation": 3.75 / 1_000_000,
    },
    "claude-opus-4-7": {
        "input":          15.00 / 1_000_000,
        "output":         75.00 / 1_000_000,
        "cache_read":     1.50 / 1_000_000,
        "cache_creation": 18.75 / 1_000_000,
    },
    "claude-haiku-4-5-20251001": {
        "input":          0.80 / 1_000_000,
        "output":         4.00 / 1_000_000,
        "cache_read":     0.08 / 1_000_000,
        "cache_creation": 1.00 / 1_000_000,
    },
}


def calculate_cost(usage: anthropic.types.Usage, model: str) -> float:
    """Calcule le coût en USD depuis l'objet usage de l'API Anthropic."""
    pricing = PRICING.get(model, PRICING["claude-sonnet-4-6"])
    return (
        usage.input_tokens * pricing["input"]
        + usage.output_tokens * pricing["output"]
        + getattr(usage, "cache_read_input_tokens", 0) * pricing["cache_read"]
        + getattr(usage, "cache_creation_input_tokens", 0) * pricing["cache_creation"]
    )
