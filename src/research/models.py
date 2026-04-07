from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ResearchTaskOut(BaseModel):
    id: str
    topic: str
    status: str
    progress_percent: int
    search_source_used: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ResearchTaskDetail(ResearchTaskOut):
    scope_description: Optional[str] = None
    sections: List[dict] = []
    citations: List[dict] = []
    saved_item_id: Optional[str] = None
    error_message: Optional[str] = None


class ResearchCreate(BaseModel):
    topic: str
    scope_description: Optional[str] = None


class ResearchRespond(BaseModel):
    answer: str
    custom_input: Optional[str] = None


class PendingQuestion(BaseModel):
    question: str
    options: List[str]
