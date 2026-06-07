from __future__ import annotations

from pydantic import BaseModel


class UsageBySkill(BaseModel):
    """Consommation agrégée d'un skill sur la période — ventilation du metering `usage_events`."""

    skill: str
    cost_usd: float
    tokens_input: int
    tokens_output: int
    events: int


class UsageResponse(BaseModel):
    """Consommation agrégée du tenant courant sur la fenêtre `period_days` (E4-S5).

    Alimentée par `usage_events` (metering S166) sous le contexte tenant (RLS) : un tenant
    ne voit que sa propre consommation. `cost_usd` (colonne `NUMERIC`) est arrondi à 6 décimales
    côté API, cohérent avec `MetricsResponse`.
    """

    period_days: int
    total_cost_usd: float
    total_tokens_input: int
    total_tokens_output: int
    by_skill: list[UsageBySkill]
    # coût USD total par jour (clé YYYY-MM-DD), même forme que MetricsResponse.daily_cost
    daily_cost: dict[str, float]
