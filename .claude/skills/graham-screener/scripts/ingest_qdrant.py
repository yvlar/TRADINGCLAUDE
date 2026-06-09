#!/usr/bin/env python3
"""
ingest_qdrant.py — Ingestion des candidats du screening Graham dans Qdrant,
au format compatible avec le pipeline RAG de TradingClaude.

Usage :
    # Ingestion réelle (text-embedding-3-small, même modèle que ingest_rag.py)
    python ingest_qdrant.py --input output/candidates.jsonl \\
        --collection graham_screening

    # Test sans serveur ni clé API (Qdrant en mémoire + embeddings factices)
    python ingest_qdrant.py --input output/candidates.jsonl \\
        --url ":memory:" --embedder dummy

URL Qdrant : --url, sinon variable d'environnement QDRANT_URL, sinon
http://localhost:6333. Clé OpenAI : --openai-key, sinon OPENAI_API_KEY.

Dépendances : qdrant-client; openai (embedder openai seulement).
Conventions : identifiants en anglais, commentaires en français.
"""

import argparse
import hashlib
import json
import os
import uuid
from pathlib import Path

# Aligné sur scripts/ingest_rag.py : text-embedding-3-small produit 1536 dims
_OPENAI_MODEL = "text-embedding-3-small"
_OPENAI_DIMS = 1536


def make_embedder(kind: str, dim: int, openai_key: str | None):
    """Retourne (fonction textes -> vecteurs, dimension) selon l'embedder choisi.

    - openai : text-embedding-3-small (1536 dims), même modèle que le corpus
      investment_knowledge du projet (scripts/ingest_rag.py).
    - dummy  : vecteur déterministe dérivé d'un hash (tests hors-ligne).
    """
    if kind == "openai":
        from openai import OpenAI
        if not openai_key:
            raise SystemExit("Clé OpenAI requise : --openai-key ou OPENAI_API_KEY")
        client = OpenAI(api_key=openai_key)

        def embed(texts):
            response = client.embeddings.create(model=_OPENAI_MODEL, input=texts)
            return [item.embedding for item in response.data]
        return embed, _OPENAI_DIMS

    def embed_dummy(texts):
        # Hash SHA-256 répété -> pseudo-vecteur stable; uniquement pour tester
        vectors = []
        for t in texts:
            h = hashlib.sha256(t.encode()).digest()
            raw = (h * (dim // len(h) + 1))[:dim]
            vectors.append([b / 255.0 for b in raw])
        return vectors
    return embed_dummy, dim


def main():
    parser = argparse.ArgumentParser(description="Ingestion Qdrant des candidats Graham")
    parser.add_argument("--input", required=True, help="Fichier candidates.jsonl")
    parser.add_argument("--url", default=None,
                        help="URL Qdrant, ou ':memory:' pour un test local "
                             "(défaut : $QDRANT_URL ou http://localhost:6333)")
    parser.add_argument("--collection", default="graham_screening")
    parser.add_argument("--embedder", default="openai", choices=["openai", "dummy"])
    parser.add_argument("--openai-key", default=None,
                        help="Clé OpenAI (défaut : $OPENAI_API_KEY)")
    parser.add_argument("--dim", type=int, default=_OPENAI_DIMS,
                        help=f"Dimension des vecteurs (défaut : {_OPENAI_DIMS})")
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct

    url = args.url or os.environ.get("QDRANT_URL", "http://localhost:6333")

    # ':memory:' = instance éphémère en RAM, parfaite pour valider le flux
    client = (QdrantClient(location=":memory:") if url == ":memory:"
              else QdrantClient(url=url))

    openai_key = args.openai_key or os.environ.get("OPENAI_API_KEY")
    embed, dim = make_embedder(args.embedder, args.dim, openai_key)

    # Création idempotente de la collection (cosine, comme le reste du pipeline)
    if not client.collection_exists(args.collection):
        client.create_collection(
            collection_name=args.collection,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        print(f"Collection '{args.collection}' créée ({dim} dim, cosine)")

    # Lecture du JSONL et upsert par lots
    docs = [json.loads(line) for line in
            Path(args.input).read_text().splitlines() if line.strip()]
    if not docs:
        print("Aucun candidat à ingérer — fichier vide.")
        return

    total = 0
    for i in range(0, len(docs), args.batch_size):
        batch = docs[i:i + args.batch_size]
        vectors = embed([d["text"] for d in batch])
        points = [
            PointStruct(
                # ID déterministe dérivé de l'ID logique -> ré-ingestion idempotente
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, d["id"])),
                vector=vectors[j],
                # chunk_text : champ lu par RagClient.search (app/rag/client.py)
                payload={**d["payload"], "chunk_text": d["text"], "logical_id": d["id"]},
            )
            for j, d in enumerate(batch)
        ]
        client.upsert(collection_name=args.collection, points=points)
        total += len(points)

    print(f"Ingestion terminée : {total} candidats dans '{args.collection}'")

    # Vérification rapide : une requête de similarité sur le premier document
    sample_vector = embed([docs[0]["text"]])[0]
    hits = client.query_points(collection_name=args.collection,
                               query=sample_vector, limit=3).points
    print("Vérification — top résultats :")
    for h in hits:
        p = h.payload
        print(f"  {p['ticker']} (score Graham {p['score']}/{p['evaluated']}, "
              f"similarité {h.score:.3f})")


if __name__ == "__main__":
    main()
