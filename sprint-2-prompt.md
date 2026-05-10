# Sprint 2 — Prompt d'implémentation
**Infrastructure RAG — Phase 1**
*Généré le 7 mai 2026 — à utiliser après la complétion du Sprint 1*

---

# PRÉREQUIS

Le Sprint 1 doit être complété avant d'exécuter ce sprint :
- `app/skills/base.py` existe avec `Citation`, `UsageDetail`, `SkillBase`
- `execute()` retourne `tuple[BaseModel, UsageDetail]`
- `/healthz` vérifie PostgreSQL et Qdrant
- Tous les tests du Sprint 1 passent (`pytest tests/ -v`)

---

# RÔLE

Développeur Python senior spécialiste RAG et architecture de systèmes LLM.
Tu maîtrises FastAPI, asyncpg, Qdrant (client async Python), le SDK OpenAI
pour les embeddings, et les patterns de production pour les applications IA.

---

# CONTEXTE

Projet : copilote financier RAG — analyse d'investissement multi-frameworks.
**Phase 1 — objectif :** rendre le RAG opérationnel sur `graham_analysis`.
Qdrant tourne déjà dans Docker Compose (port 6333) mais la collection est vide.

**Corpus à vectoriser :**
```
.claude/skills/{skill-name}/SKILL.md          — 15 fichiers
.claude/skills/{skill-name}/references/*.md   — ~62 fichiers
.claude/skills/investment-thesis-builder/templates/*.md  — fichiers templates
Total : ~77 documents → ~500 chunks estimés
```

**Collection Qdrant cible** (section 7.4 de l'architecture) :
```
Nom        : investment_knowledge
Distance   : Cosine
Dimensions : 1536  (text-embedding-3-small d'OpenAI)
Payload    : {skill_id, source_file, section, chunk_index, chunk_text}
```

**Décision d'embedding — S2-1 (tranchée) :**

| Option | Dimensions | Coût ingestion (~500 chunks) | Infrastructure |
|--------|-----------|------------------------------|----------------|
| `text-embedding-3-small` (OpenAI) | 1536 | < 0,01 $ total | Clé API OpenAI |
| `nomic-embed-text` (local Ollama) | 768 | 0 $ | Ollama + 270 MB RAM |

**Choix retenu : `text-embedding-3-small`.**
Raisons : dimensions déjà spécifiées dans l'architecture, pas d'infrastructure
supplémentaire à gérer, coût négligeable pour le corpus cible (~77 docs).
Si `OPENAI_API_KEY` est absent, le service démarre normalement mais
`get_citations()` lève `RuntimeError("OPENAI_API_KEY manquante — RAG désactivé")`.

**Stack :** Python 3.11, FastAPI, asyncpg, Qdrant v1.9, OpenAI SDK (embeddings uniquement)
**Langue du code :** anglais | **Commentaires, docstrings :** français
**Tests :** pytest-asyncio, aucun service réel dans les tests unitaires

**Nouvelles variables d'environnement à ajouter dans `.env.example` :**

```
OPENAI_API_KEY=sk-...          # Requis pour les embeddings RAG (Phase 1+)
QDRANT_URL=http://qdrant:6333  # Déjà présent après Sprint 1
QDRANT_COLLECTION=investment_knowledge
RAG_TOP_K=5                    # Nombre de citations retournées par get_citations()
```

---

# TÂCHE

Exécuter les 6 tâches du Sprint 2 dans l'ordre indiqué.
Les dépendances : S2-3 et S2-4 dépendent de S2-2. S2-5 dépend de S2-4.

---

## S2-2 — Créer `scripts/ingest_rag.py`

Script autonome exécuté **une fois** manuellement pour peupler Qdrant.
Doit être idempotent : une deuxième exécution met à jour les points existants
(upsert) sans dupliquer.

**Algorithme de chunking :**

1. Lire chaque fichier `.md` en UTF-8
2. Découper par sections `## ` et `### ` (regex : `^#{2,3} `)
3. Chaque chunk = header + corps jusqu'au prochain header
4. Ignorer les chunks < 50 caractères (headers vides)
5. ID du point : `uuid5(NAMESPACE_URL, f"{source_file}#{chunk_index}")` — déterministe

**Payload par point :**

```python
{
    "skill_id":    "graham_stock_screening",   # répertoire normalisé (- → _)
    "source_file": "graham-stock-screening/references/graham-defensif.md",
    "section":     "## Les 8 critères",        # texte du header
    "chunk_index": 0,                          # position 0-based dans le doc
    "chunk_text":  "...",                      # texte complet du chunk (stocké dans payload)
}
```

**Usage :**

```bash
python scripts/ingest_rag.py \
  --skills-dir .claude/skills \
  --qdrant-url http://localhost:6333 \
  --collection investment_knowledge \
  --openai-key sk-...
```

**Contenu complet de `scripts/ingest_rag.py` :**

```python
#!/usr/bin/env python3
"""Script d'ingestion RAG : vectorise le corpus .claude/skills/ dans Qdrant."""
from __future__ import annotations

import argparse
import logging
import re
import uuid
from pathlib import Path

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    PointStruct,
    VectorParams,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_COLLECTION = "investment_knowledge"
_DIMS = 1536
_NAMESPACE = uuid.NAMESPACE_URL
_MIN_CHUNK_LEN = 50
_BATCH_SIZE = 100


def _chunk_document(text: str) -> list[dict]:
    """Découpe un document markdown en chunks par sections h2/h3."""
    pattern = re.compile(r"^(#{2,3} .+)$", re.MULTILINE)
    matches = list(pattern.finditer(text))

    chunks: list[dict] = []
    if not matches:
        if len(text.strip()) >= _MIN_CHUNK_LEN:
            chunks.append({"section": "", "text": text.strip()})
        return chunks

    # Chunk avant la première section (préambule)
    preambule = text[: matches[0].start()].strip()
    if len(preambule) >= _MIN_CHUNK_LEN:
        chunks.append({"section": "", "text": preambule})

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if len(body) >= _MIN_CHUNK_LEN:
            chunks.append({"section": match.group(1), "text": body})

    return chunks


def _skill_id_from_path(skill_dir: Path) -> str:
    """Convertit 'graham-stock-screening' → 'graham_stock_screening'."""
    return skill_dir.name.replace("-", "_")


def _collect_files(skills_dir: Path) -> list[tuple[Path, Path]]:
    """Retourne (skill_dir, fichier_md) pour tous les fichiers à vectoriser."""
    pairs: list[tuple[Path, Path]] = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        # SKILL.md
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            pairs.append((skill_dir, skill_md))
        # references/*.md
        for md in sorted((skill_dir / "references").glob("*.md")):
            pairs.append((skill_dir, md))
        # templates/*.md (investment-thesis-builder)
        templates_dir = skill_dir / "templates"
        if templates_dir.exists():
            for md in sorted(templates_dir.glob("*.md")):
                pairs.append((skill_dir, md))
    return pairs


def _embed_batch(client: OpenAI, texts: list[str]) -> list[list[float]]:
    """Embed une liste de textes avec text-embedding-3-small."""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    return [item.embedding for item in response.data]


def _ensure_collection(qdrant: QdrantClient, collection: str) -> None:
    """Crée la collection si elle n'existe pas déjà."""
    existing = {c.name for c in qdrant.get_collections().collections}
    if collection not in existing:
        qdrant.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=_DIMS, distance=Distance.COSINE),
        )
        logger.info("Collection '%s' créée (%d dims, Cosine)", collection, _DIMS)
    else:
        logger.info("Collection '%s' déjà existante — upsert en cours", collection)


def ingest(skills_dir: Path, qdrant_url: str, collection: str, openai_key: str) -> None:
    """Point d'entrée principal de l'ingestion."""
    openai_client = OpenAI(api_key=openai_key)
    qdrant_client = QdrantClient(url=qdrant_url)

    _ensure_collection(qdrant_client, collection)

    pairs = _collect_files(skills_dir)
    logger.info("%d fichiers à traiter", len(pairs))

    all_points: list[PointStruct] = []
    total_chunks = 0

    for skill_dir, md_path in pairs:
        skill_id = _skill_id_from_path(skill_dir)
        source_file = str(md_path.relative_to(skills_dir.parent))
        text = md_path.read_text(encoding="utf-8")
        chunks = _chunk_document(text)

        for idx, chunk in enumerate(chunks):
            point_id = str(uuid.uuid5(_NAMESPACE, f"{source_file}#{idx}"))
            all_points.append(
                PointStruct(
                    id=point_id,
                    vector=[],  # rempli en batch ci-dessous
                    payload={
                        "skill_id":    skill_id,
                        "source_file": source_file,
                        "section":     chunk["section"],
                        "chunk_index": idx,
                        "chunk_text":  chunk["text"],
                    },
                )
            )
        total_chunks += len(chunks)
        logger.info("  %s → %d chunks", source_file, len(chunks))

    logger.info("Total : %d chunks à embedder", total_chunks)

    # Embedding en batches
    texts = [p.payload["chunk_text"] for p in all_points]
    vectors: list[list[float]] = []
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        vectors.extend(_embed_batch(openai_client, batch))
        logger.info("  Batch %d/%d embeddé", min(i + _BATCH_SIZE, len(texts)), len(texts))

    for point, vector in zip(all_points, vectors):
        point.vector = vector

    # Upsert par batches
    for i in range(0, len(all_points), _BATCH_SIZE):
        batch = all_points[i : i + _BATCH_SIZE]
        qdrant_client.upsert(collection_name=collection, points=batch)

    logger.info("Ingestion terminée : %d points upsertés dans '%s'", len(all_points), collection)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingestion RAG du corpus .claude/skills/")
    parser.add_argument("--skills-dir", type=Path, default=Path(".claude/skills"))
    parser.add_argument("--qdrant-url", default="http://localhost:6333")
    parser.add_argument("--collection", default=_COLLECTION)
    parser.add_argument("--openai-key", required=True)
    args = parser.parse_args()

    ingest(
        skills_dir=args.skills_dir,
        qdrant_url=args.qdrant_url,
        collection=args.collection,
        openai_key=args.openai_key,
    )
```

**Ajouter dans `requirements.txt` :**

```
qdrant-client>=1.9.0
openai>=1.0.0
```

**Note :** Le script utilise le client Qdrant synchrone (pas async) car c'est un script
one-shot — pas besoin du surcoût async pour un processus batch.

---

## S2-3 — Initialiser la collection au démarrage du service (`app/api/main.py`)

Au démarrage FastAPI, le service doit s'assurer que la collection `investment_knowledge`
existe dans Qdrant (elle est créée par le script d'ingestion, mais le service ne doit
pas planter si elle est absente).

**Créer `app/rag/__init__.py`** (vide).

**Créer `app/rag/client.py` :**

```python
# app/rag/client.py
from __future__ import annotations

import logging

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, VectorParams

from app.skills.base import Citation

logger = logging.getLogger(__name__)

_DIMS = 1536


class RagClient:
    """Wrapper async autour de QdrantClient pour la recherche vectorielle."""

    def __init__(self, url: str, collection: str) -> None:
        self._client = AsyncQdrantClient(url=url)
        self._collection = collection

    async def ensure_collection(self) -> None:
        """Crée la collection si absente. Idempotent."""
        existing = await self._client.get_collections()
        names = {c.name for c in existing.collections}
        if self._collection not in names:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=_DIMS, distance=Distance.COSINE),
            )
            logger.warning(
                "Collection '%s' absente — créée vide. Lancer scripts/ingest_rag.py.",
                self._collection,
            )

    async def search(
        self, query_vector: list[float], k: int = 5
    ) -> list[Citation]:
        """Recherche les k chunks les plus proches et retourne des Citations."""
        results = await self._client.search(
            collection_name=self._collection,
            query_vector=query_vector,
            limit=k,
            with_payload=True,
        )
        return [
            Citation(
                source=r.payload["source_file"],
                extrait=r.payload["chunk_text"],
                score=r.score,
            )
            for r in results
        ]

    async def close(self) -> None:
        await self._client.close()
```

**Créer `app/rag/embeddings.py` :**

```python
# app/rag/embeddings.py
from __future__ import annotations

from openai import AsyncOpenAI


class EmbeddingClient:
    """Wrapper async autour de l'API OpenAI pour text-embedding-3-small."""

    _MODEL = "text-embedding-3-small"

    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)

    async def embed(self, text: str) -> list[float]:
        """Retourne le vecteur d'embedding pour un texte."""
        response = await self._client.embeddings.create(
            model=self._MODEL,
            input=text,
        )
        return response.data[0].embedding
```

**Créer `app/rag/service.py` — point d'entrée unifié pour les skills :**

```python
# app/rag/service.py
from __future__ import annotations

import logging

from app.rag.client import RagClient
from app.rag.embeddings import EmbeddingClient
from app.skills.base import Citation

logger = logging.getLogger(__name__)


class RagService:
    """Façade utilisée par les skills : embed la query, cherche dans Qdrant."""

    def __init__(self, rag_client: RagClient, embedder: EmbeddingClient) -> None:
        self._rag = rag_client
        self._embedder = embedder

    async def search(self, query: str, k: int = 5) -> list[Citation]:
        """Recherche sémantique dans le corpus RAG."""
        try:
            vector = await self._embedder.embed(query)
            return await self._rag.search(vector, k=k)
        except Exception:
            logger.exception("Erreur RAG lors de la recherche — citations vides retournées")
            return []
```

**Mettre à jour le `lifespan` dans `app/api/main.py` :**

```python
import os
from app.rag.client import RagClient
from app.rag.embeddings import EmbeddingClient
from app.rag.service import RagService

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    api_key      = _get_env("ANTHROPIC_API_KEY")
    model        = _get_env("CLAUDE_MODEL", "claude-sonnet-4-6")
    db_url       = _get_env("DATABASE_URL", "postgresql://copilote:copilote@postgres:5432/copilote")
    qdrant_url   = _get_env("QDRANT_URL", "http://qdrant:6333")
    qdrant_coll  = _get_env("QDRANT_COLLECTION", "investment_knowledge")
    openai_key   = os.environ.get("OPENAI_API_KEY")  # optionnel — RAG désactivé si absent
    top_k        = int(_get_env("RAG_TOP_K", "5"))

    db_pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10)

    anthropic_client = anthropic.AsyncAnthropic(api_key=api_key)

    # RAG — initialisé seulement si la clé OpenAI est présente
    rag_client = RagClient(url=qdrant_url, collection=qdrant_coll)
    await rag_client.ensure_collection()

    rag_service: RagService | None = None
    if openai_key:
        embedder = EmbeddingClient(api_key=openai_key)
        rag_service = RagService(rag_client=rag_client, embedder=embedder)
        logger.info("RAG activé — collection '%s'", qdrant_coll)
    else:
        logger.warning("OPENAI_API_KEY absente — RAG désactivé, citations = []")

    graham_skill = GrahamAnalysisSkill(
        client=anthropic_client,
        model=model,
        rag_service=rag_service,
        top_k=top_k,
    )
    orchestrator = Orchestrator(db_pool=db_pool, graham_skill=graham_skill)

    app.state.orchestrator = orchestrator
    app.state.db_pool      = db_pool
    app.state.qdrant_url   = qdrant_url

    logger.info("Copilote financier démarré — version %s", _VERSION)
    yield

    await db_pool.close()
    await rag_client.close()
```

---

## S2-4 — Implémenter `get_citations()` dans `GrahamAnalysisSkill`

Mettre à jour le constructeur et `get_citations()` dans
`app/skills/tier2/graham_analysis/skill.py`.

**Changements dans `skill.py` :**

```python
# Ajouter l'import
from app.rag.service import RagService

class GrahamAnalysisSkill(SkillBase):

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str,
        rag_service: RagService | None = None,
        top_k: int = 5,
    ) -> None:
        self._client = client
        self._model = model
        self._rag = rag_service
        self._top_k = top_k
        self._system_prompt_text = self._load_system_prompt()

    async def get_citations(self, query: str, k: int = 5) -> list[Citation]:
        """
        Recherche RAG dans Qdrant pour les passages Graham pertinents.
        Retourne [] si le RAG n'est pas initialisé (Phase 0 / OPENAI_API_KEY absente).
        """
        if self._rag is None:
            return []
        return await self._rag.search(query, k=k)
```

---

## S2-5 — Injecter les citations dans le message utilisateur

Modifier `execute()` et `_build_user_message()` dans `GrahamAnalysisSkill` pour :

1. Appeler `get_citations()` avec une query construite depuis le ticker et les ratios
2. Injecter les citations en tête du message utilisateur (avant les ratios)
3. Stocker les citations dans `GrahamAnalysisOutput.citations`

**Mise à jour de `schemas.py` :**

Le champ `citations` est actuellement `list[str]`. Le changer en `list[Citation]`
pour correspondre au type retourné par `get_citations()` :

```python
# Dans GrahamAnalysisOutput, remplacer :
citations: list[str] = Field(default_factory=list, ...)

# Par :
from app.skills.base import Citation
citations: list[Citation] = Field(default_factory=list, ...)
```

**Mise à jour de `execute()` dans `skill.py` :**

```python
async def execute(
    self, input_data: GrahamAnalysisInput
) -> tuple[GrahamAnalysisOutput, UsageDetail]:

    # Construire la query RAG depuis le contexte de l'analyse
    rag_query = (
        f"Graham screening criteria {input_data.ticker} "
        f"PE {input_data.ratios.pe} PB {input_data.ratios.pb} "
        f"debt equity {input_data.ratios.debt_equity}"
    )
    citations = await self.get_citations(rag_query, k=self._top_k)

    user_message = self._build_user_message(input_data, citations)

    response = await self._client.messages.create(
        model=self._model,
        system=self.get_system_prompt(),
        messages=[{"role": "user", "content": user_message}],
        max_tokens=2048,
    )

    raw_text = response.content[0].text
    data = _parse_claude_json(raw_text)

    cost_usd = calculate_cost(response.usage, self._model)

    usage_detail = UsageDetail(
        tokens_input=response.usage.input_tokens,
        tokens_output=response.usage.output_tokens,
        tokens_cache_read=getattr(response.usage, "cache_read_input_tokens", 0),
        tokens_cache_creation=getattr(response.usage, "cache_creation_input_tokens", 0),
        cost_usd=cost_usd,
        model=self._model,
    )

    graham_output = GrahamAnalysisOutput.model_validate(data)
    graham_output.citations = citations  # injection post-validation
    return graham_output, usage_detail
```

**Mise à jour de `_build_user_message()` :**

```python
def _build_user_message(
    self, input_data: GrahamAnalysisInput, citations: list[Citation]
) -> str:
    """Construit le message utilisateur avec citations RAG et ratios."""
    parts: list[str] = []

    if citations:
        parts.append("## Contexte de référence (corpus Graham)\n")
        for i, cit in enumerate(citations, 1):
            parts.append(
                f"**[{i}] {cit.source}** (score : {cit.score:.2f})\n{cit.extrait}\n"
            )
        parts.append("---\n")

    ratios_json = input_data.ratios.model_dump_json(indent=2)
    parts.append(
        f"Analyse les ratios financiers de **{input_data.ticker}** :\n\n"
        f"```json\n{ratios_json}\n```\n\n"
        "Applique les 8 critères défensifs et les 5 critères entrepreneuriaux de Graham. "
        "Retourne uniquement le JSON structuré conforme au format de sortie défini."
    )

    return "\n".join(parts)
```

**Note sur `graham_output.citations = citations` :**
Le `@model_validator` s'exécute pendant `model_validate()`, donc il ne voit pas
les citations. L'assignation post-validation est correcte : `citations` n'est pas
validée par le validator (qui ne porte que sur les counts de critères).

---

## S2-6 — Logging structuré JSON avec cache hit ratio et latence

Ajouter un formatter JSON sur le logger racine et logger les métriques après chaque
appel Claude. Pas de dépendance externe — utiliser uniquement `logging` stdlib.

**Créer `app/logging_config.py` :**

```python
# app/logging_config.py
from __future__ import annotations

import json
import logging
import os
import time


class JsonFormatter(logging.Formatter):
    """Formatter qui émet chaque enregistrement de log comme une ligne JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict = {
            "ts":      self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level":   record.levelname,
            "logger":  record.name,
            "msg":     record.getMessage(),
        }
        # Champs structurés ajoutés via extra={}
        for key in ("skill_id", "ticker", "latency_ms", "cost_usd",
                    "cache_hit_ratio", "tokens_input", "tokens_output",
                    "tokens_cache_read", "tokens_cache_creation", "model"):
            if hasattr(record, key):
                log_obj[key] = getattr(record, key)
        if record.exc_info:
            log_obj["exc"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


def configure_logging() -> None:
    """Configure le logging JSON si LOG_FORMAT=json, sinon garde le format texte."""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_format = os.environ.get("LOG_FORMAT", "text").lower()

    handler = logging.StreamHandler()
    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s — %(message)s")
        )

    logging.basicConfig(level=log_level, handlers=[handler], force=True)
```

**Mettre à jour `app/api/main.py` pour appeler `configure_logging()` au démarrage :**

```python
from app.logging_config import configure_logging
configure_logging()  # avant la création de l'app FastAPI
```

**Ajouter la variable dans `.env.example` :**

```
LOG_FORMAT=json   # 'json' pour production, 'text' pour dev local
```

**Instrumenter `execute()` dans `skill.py` pour logger les métriques :**

Entourer l'appel `messages.create()` d'un timer et logger après réception :

```python
import time

async def execute(self, input_data: GrahamAnalysisInput) -> tuple[GrahamAnalysisOutput, UsageDetail]:

    citations = await self.get_citations(rag_query, k=self._top_k)
    user_message = self._build_user_message(input_data, citations)

    t0 = time.perf_counter()
    response = await self._client.messages.create(
        model=self._model,
        system=self.get_system_prompt(),
        messages=[{"role": "user", "content": user_message}],
        max_tokens=2048,
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)

    raw_text = response.content[0].text
    data = _parse_claude_json(raw_text)
    cost_usd = calculate_cost(response.usage, self._model)

    tokens_input    = response.usage.input_tokens
    tokens_output   = response.usage.output_tokens
    tokens_cache_r  = getattr(response.usage, "cache_read_input_tokens", 0)
    tokens_cache_c  = getattr(response.usage, "cache_creation_input_tokens", 0)
    total_consumed  = tokens_input + tokens_cache_r + tokens_cache_c
    cache_hit_ratio = round(tokens_cache_r / total_consumed, 4) if total_consumed else 0.0

    logger.info(
        "execute terminé",
        extra={
            "skill_id":             self.skill_id,
            "ticker":               input_data.ticker,
            "latency_ms":           latency_ms,
            "cost_usd":             round(cost_usd, 6),
            "cache_hit_ratio":      cache_hit_ratio,
            "tokens_input":         tokens_input,
            "tokens_output":        tokens_output,
            "tokens_cache_read":    tokens_cache_r,
            "tokens_cache_creation": tokens_cache_c,
            "model":                self._model,
        },
    )

    usage_detail = UsageDetail(
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        tokens_cache_read=tokens_cache_r,
        tokens_cache_creation=tokens_cache_c,
        cost_usd=cost_usd,
        model=self._model,
    )

    graham_output = GrahamAnalysisOutput.model_validate(data)
    graham_output.citations = citations
    return graham_output, usage_detail
```

**Exemple de ligne de log en production (LOG_FORMAT=json) :**

```json
{
  "ts": "2026-05-07T14:32:01",
  "level": "INFO",
  "logger": "app.skills.tier2.graham_analysis.skill",
  "msg": "execute terminé",
  "skill_id": "graham_analysis",
  "ticker": "BNS",
  "latency_ms": 1843,
  "cost_usd": 0.000423,
  "cache_hit_ratio": 0.8762,
  "tokens_input": 148,
  "tokens_output": 812,
  "tokens_cache_read": 1043,
  "tokens_cache_creation": 0,
  "model": "claude-sonnet-4-6"
}
```

---

# MISE À JOUR DES TESTS

## Fixtures à ajouter dans `tests/conftest.py`

```python
from unittest.mock import AsyncMock, MagicMock
from app.rag.service import RagService
from app.skills.base import Citation

@pytest.fixture
def mock_rag_service():
    """RagService mocké retournant des citations de test."""
    service = AsyncMock(spec=RagService)
    service.search.return_value = [
        Citation(
            source="graham-stock-screening/references/graham-defensif.md",
            extrait="## Les 8 critères\nL'investisseur défensif applique 8 critères stricts.",
            score=0.91,
        )
    ]
    return service

@pytest.fixture
def mock_rag_service_vide():
    """RagService mocké retournant une liste vide (RAG désactivé)."""
    service = AsyncMock(spec=RagService)
    service.search.return_value = []
    return service
```

## Nouveaux tests à ajouter dans `tests/test_skill.py`

```python
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
```

**Ajouter la fixture `skill_avec_mock_client_et_rag` dans `conftest.py`** (ou dans
le module de test) : identique à `skill_avec_mock_client` mais passe `mock_rag_service`.

## Nouveaux tests pour `app/rag/`

Créer `tests/test_rag.py` :

```python
"""Tests unitaires du module app/rag/ — aucun service Qdrant ou OpenAI réel."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.rag.service import RagService
from app.skills.base import Citation


class TestRagServiceSearch:
    @pytest.mark.asyncio
    async def test_search_retourne_liste_citations(self):
        mock_client = AsyncMock()
        mock_embedder = AsyncMock()
        mock_embedder.embed.return_value = [0.1] * 1536

        expected = [Citation(source="file.md", extrait="texte", score=0.9)]
        mock_client.search.return_value = expected

        service = RagService(rag_client=mock_client, embedder=mock_embedder)
        result = await service.search("current ratio", k=3)

        mock_embedder.embed.assert_called_once_with("current ratio")
        mock_client.search.assert_called_once_with([0.1] * 1536, k=3)
        assert result == expected

    @pytest.mark.asyncio
    async def test_search_retourne_vide_si_exception(self):
        """En cas d'erreur Qdrant ou OpenAI, retourne [] sans propager l'exception."""
        mock_client = AsyncMock()
        mock_embedder = AsyncMock()
        mock_embedder.embed.side_effect = ConnectionError("OpenAI indisponible")

        service = RagService(rag_client=mock_client, embedder=mock_embedder)
        result = await service.search("test query")
        assert result == []
```

## Mises à jour dans `tests/test_api.py`

Le constructeur de `GrahamAnalysisSkill` a changé (paramètre `rag_service`).
Le patch existant dans la fixture `async_client` cible `_load_system_prompt` —
il fonctionne toujours. Ajouter `rag_service=None` dans la construction mockée
si le test instancie directement le skill.

---

# CONTRAINTES NON-NÉGOCIABLES

- Ne pas modifier l'interface publique de l'API (les champs de `AnalyzeResponse` restent identiques)
- `GrahamAnalysisSkill(rag_service=None)` doit fonctionner → backward compat Phase 0
- Le service démarre sans `OPENAI_API_KEY` — RAG silencieusement désactivé, citations = []
- Pas de `print()`, pas de TODO, pas de placeholders
- `scripts/ingest_rag.py` est exécutable depuis la racine du repo — les chemins relatifs partent de là
- Chaque fichier fourni est complet et autonome

---

# CRITÈRE DE SUCCÈS UNIQUE

**Après ingestion et démarrage :**

```bash
# 1. Ingérer le corpus
python scripts/ingest_rag.py \
  --skills-dir .claude/skills \
  --qdrant-url http://localhost:6333 \
  --openai-key $OPENAI_API_KEY

# 2. Démarrer le service
docker-compose up -d --build copilote

# 3. Vérifier healthz (doit retourner qdrant: ok)
curl localhost:8000/healthz
# {"status":"ok","version":"0.1.1","postgres":"ok","qdrant":"ok"}

# 4. Lancer une analyse — les citations doivent être non vides
curl -X POST localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"ticker":"BNS","ratios":{"pe":11.0,"pb":1.3,"current_ratio":null,
       "debt_equity":0.45,"eps_growth_10y":0.27,"price":80,"book_value":61.5}}'
# Attendu : "citations": [{source, extrait, score}, ...]

# 5. Tous les tests passent
pytest tests/ -v
```

**Validation du logging :**

```bash
docker-compose logs copilote | python -m json.tool
# Chaque ligne doit être du JSON valide avec cache_hit_ratio et latency_ms
```

---

# FORMAT DE SORTIE

**Fichiers à CRÉER :**

| Fichier | Description |
|---------|-------------|
| `scripts/ingest_rag.py` | Script batch d'ingestion du corpus dans Qdrant |
| `app/rag/__init__.py` | Package marker (vide) |
| `app/rag/client.py` | `RagClient` — wrapper async Qdrant |
| `app/rag/embeddings.py` | `EmbeddingClient` — wrapper async OpenAI embeddings |
| `app/rag/service.py` | `RagService` — façade embed + search pour les skills |
| `app/logging_config.py` | `JsonFormatter` + `configure_logging()` |
| `tests/test_rag.py` | Tests unitaires du module RAG |

**Fichiers à MODIFIER :**

| Fichier | Changement |
|---------|-----------|
| `app/api/main.py` | Lifespan : init RagClient + EmbeddingClient + RagService, passer à GrahamAnalysisSkill |
| `app/skills/tier2/graham_analysis/skill.py` | Constructeur + `get_citations()` + `execute()` avec timer et logger |
| `app/skills/tier2/graham_analysis/schemas.py` | `citations: list[str]` → `list[Citation]` |
| `requirements.txt` | Ajouter `qdrant-client>=1.9.0`, `openai>=1.0.0` |
| `.env.example` | Ajouter `OPENAI_API_KEY`, `QDRANT_COLLECTION`, `RAG_TOP_K`, `LOG_FORMAT` |
| `tests/conftest.py` | Ajouter fixtures `mock_rag_service`, `mock_rag_service_vide`, `skill_avec_mock_client_et_rag` |
| `tests/test_skill.py` | Ajouter classe `TestGetCitations` avec 5 tests |
| `tests/test_api.py` | Adapter aux changements de constructeur GrahamAnalysisSkill |

---

# MODE DE RÉPONSE

1. Lire `architecture-copilote-financier.md` sections 2 (corpus), 7.4 (Qdrant) et 8.2 (prompt caching) AVANT de coder
2. Traiter les tâches dans l'ordre S2-2 → S2-6 (S2-2 crée le script d'ingestion en premier pour valider la logique de chunking)
3. Pas de commentaires décoratifs (`# ===`), pas de TODO, pas de placeholders
4. Après les fichiers, donner uniquement :
   - Liste des fichiers créés/modifiés (path + 1 ligne de description)
   - Commande de validation (`pytest tests/ -v` + curl)
   - Points d'attention si applicable

---

*Sprint 2 — à exécuter après complétion et validation du Sprint 1.*
*Réviser ce prompt si l'architecture change entre la rédaction et l'exécution.*
