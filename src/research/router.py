import asyncio
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.auth.dependencies import CurrentUser, get_current_user
from src.db.connection import get_db
from src.research import service
from src.research.models import (
    ResearchCreate,
    ResearchRespond,
    ResearchTaskDetail,
    ResearchTaskOut,
)
from src.tasks import queue as tq

router = APIRouter(prefix="/api/research", tags=["research"])


class ApiResponse(BaseModel):
    data: dict


class ListResponse(BaseModel):
    data: List[ResearchTaskOut]
    pagination: dict


@router.post("", response_model=ApiResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_research(
    body: ResearchCreate,
    user: Annotated[CurrentUser, Depends(get_current_user)] = None,
):
    db = await get_db()
    try:
        task_id = await service.create_task(db, body)
        return ApiResponse(
            data={
                "id": task_id,
                "topic": body.topic,
                "status": "queued",
                "progress_percent": 0,
                "created_at": "",
            }
        )
    finally:
        await db.close()


@router.get("", response_model=ListResponse)
async def list_research(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    user: Annotated[CurrentUser, Depends(get_current_user)] = None,
):
    db = await get_db()
    try:
        items, total = await service.list_tasks(db, offset=offset, limit=limit)
        return ListResponse(
            data=items,
            pagination={"offset": offset, "limit": limit, "total": total},
        )
    finally:
        await db.close()


@router.get("/{task_id}", response_model=ApiResponse)
async def get_research(
    task_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)] = None,
):
    db = await get_db()
    try:
        detail = await service.get_task_detail(db, task_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Task not found")
        return ApiResponse(data=detail.model_dump())
    finally:
        await db.close()


@router.get("/{task_id}/events")
async def research_events(
    task_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)] = None,
):
    q = tq.subscribe(task_id)

    async def _stream():
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield f"data: {msg}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat / keepalive
                    yield "\n"
        finally:
            tq.unsubscribe(task_id, q)

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
    )


@router.post("/{task_id}/respond", response_model=ApiResponse)
async def respond_research(
    task_id: str,
    body: ResearchRespond,
    user: Annotated[CurrentUser, Depends(get_current_user)] = None,
):
    ok = await service.respond_to_task(task_id, body.answer)
    if not ok:
        raise HTTPException(
            status_code=400, detail="Task is not awaiting input or already completed"
        )
    return ApiResponse(data={"message": "决策已提交，调研继续"})


@router.post("/{task_id}/save", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def save_research(
    task_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)] = None,
):
    item_id = await service.save_report(task_id)
    if not item_id:
        raise HTTPException(
            status_code=400, detail="Unable to save report (task may not be completed)"
        )
    return ApiResponse(
        data={"item_id": item_id, "title": "调研报告", "message": "报告已保存到知识库"}
    )
