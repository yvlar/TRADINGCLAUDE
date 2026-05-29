from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

_MAX_TAGS = 20
_MAX_TAG_LEN = 40


def normalize_tags(raw: list[str]) -> list[str]:
    """Normalise une liste de tags : trim, minuscule, sans doublon, ordre préservé.

    Minuscule garantit la cohérence du filtre `@>` JSONB entre écriture et lecture.
    """
    seen: set[str] = set()
    result: list[str] = []
    for tag in raw:
        cleaned = tag.strip().lower()[:_MAX_TAG_LEN]
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result[:_MAX_TAGS]


class Annotation(BaseModel):
    annotation_id: str
    analysis_id: str
    note: str
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime


class AnnotationCreate(BaseModel):
    analysis_id: str
    note: str = Field(min_length=1)
    tags: list[str] = []

    @field_validator("tags")
    @classmethod
    def _normalize(cls, value: list[str]) -> list[str]:
        return normalize_tags(value)
