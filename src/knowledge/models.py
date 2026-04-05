from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TagOut(BaseModel):
    id: str
    name: str
    color: Optional[str] = None


class AttachmentOut(BaseModel):
    id: str
    filename: str
    mime_type: str
    size_bytes: int
    extraction_status: str
    extraction_error: Optional[str] = None


class ConfidenceOut(BaseModel):
    score_level: str
    score_value: Optional[float] = None
    method: str
    rationale: str
    evaluated_at: datetime


class KnowledgeVersionItem(BaseModel):
    id: str
    created_at: datetime
    created_by: str


class KnowledgeCreate(BaseModel):
    title: str = ""
    content: str = Field(..., min_length=5)
    source_type: str = "text"
    tags: List[str] = []


class KnowledgeUrlCreate(BaseModel):
    url: str
    title: str = ""
    tags: List[str] = []


class KnowledgeUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = Field(None, min_length=5)
    tags: Optional[List[str]] = None


class KnowledgeListItem(BaseModel):
    id: str
    title: str
    source_type: str
    tags: List[TagOut]
    confidence: Optional[ConfidenceOut] = None
    version_count: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class KnowledgeDetail(BaseModel):
    id: str
    title: str
    source_type: str
    current_version: Optional[dict] = None
    versions: List[KnowledgeVersionItem]
    attachments: List[AttachmentOut]
    tags: List[TagOut]
    confidence: Optional[ConfidenceOut] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
