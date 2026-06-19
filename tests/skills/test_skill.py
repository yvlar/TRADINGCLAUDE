"""Tests unitaires du GrahamAnalysisSkill — fonctions pures et exécution mockée."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.skills.base import Citation, SkillConfig, UsageDetail
from app.skills.tier2.graham_analysis.schemas import GrahamAnalysisInput, GrahamAnalysisOutput
from app.skills.tier2.graham_analysis.skill import GrahamAnalysisSkill
from app.utils.costs import calculate_cost


def _tool_use_response(output: GrahamAnalysisOutput, **usage_overrides) -> MagicMock:
    """Construit une réponse Claude simulée avec bloc tool_use."""
    mock_block = MagicMock()
    mock_block.type = "tool_use"
    mock_block.input = output.model_dump(
        exclude={"defensive_score", "defensive_verdict", "confidence_score"}
    )
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.stop_reason = "tool_use"
    defaults = dict(
        input_tokens=100,
        output_tokens=50,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=500,
    )
    defaults.update(usage_overrides)
    mock_response.usage = SimpleNamespace(**defaults)
    return mock_response


# ---------------------------------------------------------------------------
# calculate_cost — tests de la fonction de calcul de coût
# ---------------------------------------------------------------------------

class TestCalculateCost:
    def test_modele_connu_calcul_correct(self, mock_usage_no_cache):
        """Vérifie le calcul exact pour claude-sonnet-4-6 sans cache hit."""
        attendu = (
            1000 * 3.00 / 1_000_000
            + 200 * 15.00 / 1_000_000
            + 0 * 0.30 / 1_000_000
            + 1500 * 3.75 / 1_000_000
        )
        resultat = calculate_cost(mock_usage_no_cache, "claude-sonnet-4-6")
        assert abs(resultat - attendu) < 1e-10

    def test_cache_hit_moins_cher_que_input_normal(self, mock_usage_cache_hit):
        """Un appel avec cache hit doit coûter moins cher qu'un appel sans cache."""
        usage_sans_cache = SimpleNamespace(
            input_tokens=1550, output_tokens=200,
            cache_read_input_tokens=0, cache_creation_input_tokens=0,
        )
        cout_cache = calculate_cost(mock_usage_cache_hit, "claude-sonnet-4-6")
        cout_sans_cache = calculate_cost(usage_sans_cache, "claude-sonnet-4-6")
        assert cout_cache < cout_sans_cache

    def test_modele_inconnu_leve_valueerror(self, mock_usage_no_cache):
        """Un modèle absent de PRICING lève ValueError plutôt que de retomber silencieusement."""
        with pytest.raises(ValueError, match="claude-inconnu-99-0"):
            calculate_cost(mock_usage_no_cache, "claude-inconnu-99-0")

    def test_modele_opus_plus_cher_que_sonnet(self, mock_usage_no_cache):
        """claude-opus-4-7 doit coûter plus cher que claude-sonnet-4-6."""
        cout_sonnet = calculate_cost(mock_usage_no_cache, "claude-sonnet-4-6")
        cout_opus = calculate_cost(mock_usage_no_cache, "claude-opus-4-7")
        assert cout_opus > cout_sonnet

    def test_sans_attributs_cache_utilise_zero(self):
        """Ancien modèle sans cache_read_input_tokens — getattr retourne 0."""
        usage_ancien = SimpleNamespace(input_tokens=500, output_tokens=100)
        resultat = calculate_cost(usage_ancien, "claude-sonnet-4-6")
        attendu = 500 * 3.00 / 1_000_000 + 100 * 15.00 / 1_000_000
        assert abs(resultat - attendu) < 1e-10

    def test_cout_strictement_positif(self, mock_usage_no_cache):
        assert calculate_cost(mock_usage_no_cache, "claude-sonnet-4-6") > 0


# ---------------------------------------------------------------------------
# GrahamAnalysisSkill — tests de construction et format du prompt
# ---------------------------------------------------------------------------

class TestGrahamAnalysisSkillConstruction:
    @pytest.fixture
    def skill(self):
        """Skill instancié avec prompt chargé depuis le fichier réel."""
        mock_client = MagicMock(spec=["messages"])
        return GrahamAnalysisSkill(client=mock_client, model="claude-sonnet-4-6")

    def test_skill_id_correct(self, skill):
        assert skill.skill_id == "graham_analysis"

    def test_tier_correct(self, skill):
        assert skill.tier == 2

    def test_system_prompt_charge(self, skill):
        assert len(skill._system_prompt_text) > 1000

    def test_get_system_prompt_retourne_liste(self, skill):
        blocks = skill.get_system_prompt()
        assert isinstance(blocks, list)
        assert len(blocks) == 1

    def test_get_system_prompt_format_cache_control(self, skill):
        block = skill.get_system_prompt()[0]
        assert block["type"] == "text"
        assert "cache_control" in block
        assert block["cache_control"]["type"] == "ephemeral"

    def test_get_system_prompt_texte_non_vide(self, skill):
        block = skill.get_system_prompt()[0]
        assert len(block["text"]) > 500

    def test_build_user_message_contient_ticker(self, skill, ratios_msft):
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        msg = skill._build_user_message(inp, [])
        assert "MSFT" in msg

    def test_build_user_message_contient_pe(self, skill, ratios_msft):
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        msg = skill._build_user_message(inp, [])
        assert "34.2" in msg

    def test_build_user_message_contient_bloc_json(self, skill, ratios_msft):
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        msg = skill._build_user_message(inp, [])
        assert "```json" in msg

    def test_build_user_message_avec_citations(self, skill, ratios_msft):
        """Avec citations, le message contient le bloc 'Contexte de référence'."""
        cit = Citation(source="file.md", extrait="texte pertinent", score=0.9)
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        msg = skill._build_user_message(inp, [cit])
        assert "Contexte de référence" in msg
        assert "file.md" in msg

    def test_build_user_message_sans_citations_pas_de_contexte(self, skill, ratios_msft):
        """Sans citations, le message ne contient pas le bloc 'Contexte de référence'."""
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        msg = skill._build_user_message(inp, [])
        assert "Contexte de référence" not in msg

    @pytest.mark.asyncio
    async def test_get_citations_retourne_liste_vide(self, skill):
        """En Phase 0 (rag_service=None), get_citations retourne toujours []."""
        result = await skill.get_citations("current ratio")
        assert result == []


# ---------------------------------------------------------------------------
# GrahamAnalysisSkill.execute — tests avec API Claude mockée (Tool Use)
# ---------------------------------------------------------------------------

class TestGrahamAnalysisSkillExecute:
    @pytest.mark.asyncio
    async def test_execute_retourne_output_valide(self, skill_avec_mock_client, ratios_msft):
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        output, usage = await skill_avec_mock_client.execute(inp)
        assert isinstance(output, GrahamAnalysisOutput)

    @pytest.mark.asyncio
    async def test_execute_ticker_correct(self, skill_avec_mock_client, ratios_msft):
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        output, usage = await skill_avec_mock_client.execute(inp)
        assert output.ticker == "MSFT"

    @pytest.mark.asyncio
    async def test_execute_cost_usd_non_nul(self, skill_avec_mock_client, ratios_msft):
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        output, usage = await skill_avec_mock_client.execute(inp)
        assert usage.cost_usd > 0.0

    @pytest.mark.asyncio
    async def test_execute_citations_vides_sans_rag(self, skill_avec_mock_client, ratios_msft):
        """Sans RAG injecté, les citations de l'output sont vides."""
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        output, usage = await skill_avec_mock_client.execute(inp)
        assert output.citations == []

    @pytest.mark.asyncio
    async def test_execute_appelle_messages_create(self, skill_avec_mock_client, ratios_msft):
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        await skill_avec_mock_client.execute(inp)
        skill_avec_mock_client._client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_passe_model_correct(self, skill_avec_mock_client, ratios_msft):
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        await skill_avec_mock_client.execute(inp)
        call_kwargs = skill_avec_mock_client._client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-sonnet-4-6"

    @pytest.mark.asyncio
    async def test_execute_passe_system_avec_cache_control(self, skill_avec_mock_client, ratios_msft):
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        await skill_avec_mock_client.execute(inp)
        call_kwargs = skill_avec_mock_client._client.messages.create.call_args.kwargs
        system = call_kwargs["system"]
        assert isinstance(system, list)
        assert system[0]["cache_control"]["type"] == "ephemeral"

    @pytest.mark.asyncio
    async def test_execute_retourne_usage_detail(self, skill_avec_mock_client, ratios_msft):
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        _, usage = await skill_avec_mock_client.execute(inp)
        assert isinstance(usage, UsageDetail)

    @pytest.mark.asyncio
    async def test_execute_usage_tokens_non_nuls(self, skill_avec_mock_client, ratios_msft):
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        _, usage = await skill_avec_mock_client.execute(inp)
        assert usage.tokens_input == 1000
        assert usage.tokens_output == 200
        assert usage.tokens_cache_creation == 1500
        assert usage.model == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# TestGetCitations — RAG dans GrahamAnalysisSkill
# ---------------------------------------------------------------------------

class TestGetCitations:
    @pytest.mark.asyncio
    async def test_get_citations_sans_rag_retourne_vide(self):
        """Sans RagService injecté, get_citations retourne []."""
        mock_client = MagicMock()
        skill = GrahamAnalysisSkill(client=mock_client, model="claude-sonnet-4-6", rag_service=None)
        result = await skill.get_citations("current ratio Graham")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_citations_avec_rag_retourne_citations(self, mock_rag_service):
        """Avec RagService injecté, get_citations délègue au service."""
        mock_client = MagicMock()
        skill = GrahamAnalysisSkill(
            client=mock_client, model="claude-sonnet-4-6", rag_service=mock_rag_service
        )
        result = await skill.get_citations("current ratio Graham", k=3)
        mock_rag_service.search.assert_called_once_with("current ratio Graham", k=3)
        assert len(result) == 1
        assert result[0].score == 0.91

    @pytest.mark.asyncio
    async def test_execute_injective_citations_dans_output(
        self, skill_avec_mock_client_et_rag, ratios_msft
    ):
        """Les citations du RAG sont présentes dans GrahamAnalysisOutput."""
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        output, _ = await skill_avec_mock_client_et_rag.execute(inp)
        assert len(output.citations) == 1
        assert output.citations[0].score == 0.91

    @pytest.mark.asyncio
    async def test_execute_user_message_contient_contexte_rag(
        self, skill_avec_mock_client_et_rag, ratios_msft
    ):
        """Le message utilisateur contient le bloc 'Contexte de référence' si RAG actif."""
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        await skill_avec_mock_client_et_rag.execute(inp)
        call_kwargs = skill_avec_mock_client_et_rag._client.messages.create.call_args.kwargs
        user_content = call_kwargs["messages"][0]["content"]
        assert "Contexte de référence" in user_content

    @pytest.mark.asyncio
    async def test_execute_sans_rag_pas_de_contexte_dans_message(
        self, skill_avec_mock_client, ratios_msft
    ):
        """Sans RAG, le message utilisateur ne contient pas de bloc contexte."""
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        await skill_avec_mock_client.execute(inp)
        call_kwargs = skill_avec_mock_client._client.messages.create.call_args.kwargs
        user_content = call_kwargs["messages"][0]["content"]
        assert "Contexte de référence" not in user_content


# ---------------------------------------------------------------------------
# TestSkillAvecConfig — SkillConfig, timeout et tracer Langfuse
# ---------------------------------------------------------------------------

class TestSkillAvecConfig:
    @pytest.mark.asyncio
    async def test_execute_utilise_timeout_config(self, ratios_msft, graham_output_msft):
        """Le timeout de SkillConfig est passé à call_claude_with_retry."""
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _tool_use_response(graham_output_msft)

        config = SkillConfig(timeout_s=42.0, max_retries=0)
        skill = GrahamAnalysisSkill(client=mock_client, model="claude-sonnet-4-6", config=config)
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        await skill.execute(inp)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["timeout"] == 42.0

    @pytest.mark.asyncio
    async def test_execute_appelle_tracer_si_present(self, ratios_msft, graham_output_msft):
        """Si config.tracer est fourni, record_generation est appelé."""
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _tool_use_response(graham_output_msft)

        mock_tracer = MagicMock()
        config = SkillConfig(tracer=mock_tracer)
        skill = GrahamAnalysisSkill(client=mock_client, model="claude-sonnet-4-6", config=config)
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        await skill.execute(inp)

        mock_tracer.record_generation.assert_called_once()
        call_kwargs = mock_tracer.record_generation.call_args.kwargs
        assert call_kwargs["skill_id"] == "graham_analysis"
        assert call_kwargs["ticker"] == "MSFT"
        assert call_kwargs["model"] == "claude-sonnet-4-6"

    @pytest.mark.asyncio
    async def test_execute_sans_tracer_ne_plante_pas(self, ratios_msft, graham_output_msft):
        """Sans tracer, execute() fonctionne normalement."""
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _tool_use_response(graham_output_msft)

        skill = GrahamAnalysisSkill(
            client=mock_client, model="claude-sonnet-4-6", config=SkillConfig(tracer=None)
        )
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        output, usage = await skill.execute(inp)
        assert isinstance(output, GrahamAnalysisOutput)
