from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Annotation(BaseModel):
    annotation_id: str
    analysis_id: str
    note: str
    created_at: datetime
    updated_at: datetime


class AnnotationCreate(BaseModel):
    analysis_id: str
    note: str = Field(min_length=1)
