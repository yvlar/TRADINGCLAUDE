from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from app.services.ratios_recon import reconstruct_ratios_traces

if TYPE_CHECKING:
    from app.orchestrator.core import AnalyzeResponse

logger = logging.getLogger(__name__)


# Mapping clé du JSONB result → (champ AnalyzeResponse, classe Pydantic du skill).
# Source unique des 16 skills tier2 (esg inclus) partagée par /report et /ticker-report.
def _result_skill_map() -> list[tuple[str, str, type]]:
    from app.skills.tier2.buffett_quality.schemas import BuffettQualityOutput
    from app.skills.tier2.canadian_tax.schemas import CanadianTaxOutput
    from app.skills.tier2.damodaran_narrative.schemas import DamodararOutput
    from app.skills.tier2.dorsey_moat.schemas import DorseyMoatOutput
    from app.skills.tier2.earnings_quality.schemas import EarningsQualityOutput
    from app.skills.tier2.esg_simplified.schemas import EsgOutput
    from app.skills.tier2.fisher_scuttlebutt.schemas import FisherOutput
    from app.skills.tier2.graham_analysis.schemas import GrahamAnalysisOutput
    from app.skills.tier2.greenblatt.schemas import GreenblattOutput
    from app.skills.tier2.klarman_margin.schemas import KlarmanOutput
    from app.skills.tier2.lynch_categories.schemas import LynchOutput
    from app.skills.tier2.marks_cycles.schemas import MarksOutput
    from app.skills.tier2.munger_mental.schemas import MungerOutput
    from app.skills.tier2.pabrai_dhandho.schemas import PabraiOutput
    from app.skills.tier2.stock_valuation.schemas import StockValuationOutput
    from app.skills.tier2.thesis_builder.schemas import ThesisBuilderOutput

    return [
        ("graham", "graham", GrahamAnalysisOutput),
        ("earnings_quality", "earnings_quality", EarningsQualityOutput),
        ("dorsey_moat", "dorsey", DorseyMoatOutput),
        ("buffett_quality", "buffett", BuffettQualityOutput),
        ("stock_valuation", "valuation", StockValuationOutput),
        ("investment_thesis_builder", "thesis", ThesisBuilderOutput),
        ("munger_mental_models", "munger", MungerOutput),
        ("canadian_tax_considerations", "canadian_tax", CanadianTaxOutput),
        ("lynch_categories", "lynch", LynchOutput),
        ("fisher_scuttlebutt", "fisher", FisherOutput),
        ("klarman_margin", "klarman", KlarmanOutput),
        ("greenblatt_magic_formula", "greenblatt", GreenblattOutput),
        ("damodaran_narrative", "damodaran", DamodararOutput),
        ("marks_cycles_risk", "marks", MarksOutput),
        ("pabrai_dhandho", "pabrai", PabraiOutput),
        ("esg_simplified", "esg", EsgOutput),
    ]


def reconstruct(row, *, require_graham: bool) -> "AnalyzeResponse | None":
    """Reconstruit une AnalyzeResponse depuis une ligne analysis_history (cœur partagé).

    Deux contrats divergents préservés via `require_graham` :
    - `True` (/report) : `result` illisible laisse propager ; `graham` absent lève
      `ValueError` ; ne retourne jamais None.
    - `False` (/ticker-report) : `result` illisible → None + warning ; `graham` toléré.
    Un skill optionnel dont le JSON ne valide pas est ignoré (warning, pas d'échec global).
    """
    from app.orchestrator.core import AnalyzeResponse

    result_str = row["result"]
    try:
        result: dict = (
            json.loads(result_str) if isinstance(result_str, str) else dict(result_str)
        )
    except (ValueError, TypeError):
        # /report (require_graham) laisse propager l'erreur ; /ticker-report tolère (None + warning).
        if require_graham:
            raise
        logger.warning("result illisible dans analysis_history — PDF sans skills")
        return None

    skills_used_raw = row["skills_used"]
    skills_used: list[str] = (
        json.loads(skills_used_raw)
        if isinstance(skills_used_raw, str)
        else list(skills_used_raw)
    )

    parsed_fields: dict = {}
    for result_key, field_name, model_cls in _result_skill_map():
        data = result.get(result_key)
        if field_name == "graham" and require_graham:
            # /report : graham obligatoire et validé strictement (l'erreur propage).
            if data is None:
                raise ValueError("Clé 'graham' absente dans result — analyse corrompue")
            parsed_fields[field_name] = model_cls.model_validate(data)
            continue
        if data is None:
            continue
        try:
            parsed_fields[field_name] = model_cls.model_validate(data)
        except Exception:
            logger.warning(
                "Skill %s ignoré (validation échouée) lors de la reconstruction", result_key
            )

    created_at = row["created_at"]
    created_at_str = (
        created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
    )

    return AnalyzeResponse(
        analysis_id=str(row["id"]),
        ticker=row["ticker"],
        workflow=row["workflow_name"],
        skills_applied=skills_used,
        cost_usd=float(row["cost_usd"]),
        created_at=created_at_str,
        **reconstruct_ratios_traces(row),
        **parsed_fields,
    )
