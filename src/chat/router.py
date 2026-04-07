from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.auth.dependencies import CurrentUser, get_current_user
from src.chat import service
from src.chat.models import ConversationOut, MessageOut
from src.db.connection import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ApiResponse(BaseModel):
    data: dict


class MessagesResponse(BaseModel):
    data: list


class ConversationsListResponse(BaseModel):
    data: List[ConversationOut]
    pagination: dict


class ChatRequest(BaseModel):
    content: str
    stream: bool = False


@router.get("/conversations", response_model=ConversationsListResponse)
async def list_conversations(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    user: Annotated[CurrentUser, Depends(get_current_user)] = None,
):
    db = await get_db()
    try:
        items, total = await service.list_conversations(db, offset=offset, limit=limit)
        return ConversationsListResponse(
            data=items,
            pagination={"offset": offset, "limit": limit, "total": total},
        )
    finally:
        await db.close()


@router.post("/conversations", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    user: Annotated[CurrentUser, Depends(get_current_user)] = None,
):
    db = await get_db()
    try:
        conv_id = await service.create_conversation(db)
        return ApiResponse(data={"id": conv_id, "title": "新会话"})
    finally:
        await db.close()


@router.get("/conversations/{conversation_id}/messages", response_model=MessagesResponse)
async def get_messages(
    conversation_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)] = None,
):
    db = await get_db()
    try:
        messages = await service.get_messages(db, conversation_id)
        return MessagesResponse(data=[m.model_dump() for m in messages])
    finally:
        await db.close()


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    body: ChatRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)] = None,
):
    if body.stream:
        async def _event_stream():
            db = await get_db()
            try:
                async for chunk in service.stream_message(db, conversation_id, body.content):
                    yield chunk
            finally:
                await db.close()

        return StreamingResponse(
            _event_stream(),
            media_type="text/event-stream",
        )
    else:
        db = await get_db()
        try:
            msg = await service.send_message(db, conversation_id, body.content)
            return ApiResponse(data=msg.model_dump())
        finally:
            await db.close()
