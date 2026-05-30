from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_S = 60.0
_DEFAULT_MAX_RETRIES = 3


async def call_claude_with_retry(
    client: anthropic.AsyncAnthropic,
    *,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
    max_retries: int = _DEFAULT_MAX_RETRIES,
    **kwargs: Any,
) -> anthropic.types.Message:
    """
    Appelle client.messages.create() avec :
    - Timeout configurable (par défaut 60 s)
    - Retry exponentiel sur les erreurs 529 (Claude overloaded)
    - Jitter aléatoire pour éviter les requêtes synchronisées entre instances

    Les erreurs autres que 529 propagent immédiatement sans retry.
    Les erreurs de timeout ne sont pas retriées (budget temps épuisé).
    """
    # reproductibilité des analyses : température nulle par défaut, surchargeable par un skill
    kwargs.setdefault("temperature", 0)

    for attempt in range(max_retries + 1):
        try:
            return await client.messages.create(timeout=timeout_s, **kwargs)

        except anthropic.APITimeoutError:
            logger.error(
                "Timeout Claude après %.0f s (tentative %d/%d)",
                timeout_s,
                attempt + 1,
                max_retries + 1,
            )
            raise

        except anthropic.APIStatusError as exc:
            if exc.status_code != 529:
                raise

            if attempt >= max_retries:
                logger.error(
                    "Claude surchargé (529) — abandon après %d tentatives",
                    max_retries + 1,
                )
                raise

            delay = (2 ** attempt) + random.uniform(0.0, 1.0)
            logger.warning(
                "Claude surchargé (529) — retry %d/%d dans %.1f s",
                attempt + 1,
                max_retries,
                delay,
                extra={"attempt": attempt + 1, "delay_s": round(delay, 1)},
            )
            await asyncio.sleep(delay)

    raise RuntimeError("call_claude_with_retry : boucle épuisée sans résultat")
