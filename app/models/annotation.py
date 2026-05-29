from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class Annotation(BaseModel):
    annotation_id: str
    analysis_id: str
    note: str
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AnnotationCreate(BaseModel):
    analysis_id: str
    note: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, value: list[str]) -> list[str]:
        """Minuscules, sans espaces, sans doublons ni vides — normalisation autoritaire serveur."""
        seen: list[str] = []
        for tag in value:
            cleaned = tag.strip().lower()
            if cleaned and cleaned not in seen:
                seen.append(cleaned)
        return seen
