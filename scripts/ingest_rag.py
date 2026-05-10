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
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            pairs.append((skill_dir, skill_md))
        refs_dir = skill_dir / "references"
        if refs_dir.exists():
            for md in sorted(refs_dir.glob("*.md")):
                pairs.append((skill_dir, md))
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
                    vector=[],
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

    texts = [p.payload["chunk_text"] for p in all_points]
    vectors: list[list[float]] = []
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        vectors.extend(_embed_batch(openai_client, batch))
        logger.info("  Batch %d/%d embeddé", min(i + _BATCH_SIZE, len(texts)), len(texts))

    for point, vector in zip(all_points, vectors):
        point.vector = vector

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
