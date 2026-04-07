from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class CitationOut(BaseModel):
    citation_index: int
    item_id: str
    item_title: str
    chunk_text: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    citations: Optional[List[CitationOut]] = None
    created_at: datetime


class ConversationOut(BaseModel):
    id: str
    title: str
    message_count: int = 0
    last_message_at: Optional[datetime] = None
    created_at: datetime


class ChatRequest(BaseModel):
    content: str
    stream: bool = False


class StreamDelta(BaseModel):
    delta: str


class StreamCitation(BaseModel):
    citations: List[CitationOut]
