from typing import Annotated, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from src.auth.crypto import get_cached_master_key
from src.auth.dependencies import CurrentUser, get_current_user
from src.db.connection import get_db
from src.knowledge.models import (
    KnowledgeCreate,
    KnowledgeDetail,
    KnowledgeListItem,
    KnowledgeUpdate,
    KnowledgeUrlCreate,
    TagOut,
)
from src.knowledge import service

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class ApiResponse(BaseModel):
    data: dict


class ListResponse(BaseModel):
    data: List[KnowledgeListItem]
    pagination: dict


class TagListResponse(BaseModel):
    data: List[TagOut]


@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge(
    body: KnowledgeCreate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    db = await get_db()
    try:
        item_id = await service.create_knowledge_text(db, body)
        detail = await service.get_knowledge_detail(db, item_id)
        return ApiResponse(data=detail.model_dump())
    finally:
        await db.close()


@router.post("/upload", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def upload_knowledge(
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()] = "",
    tags: Annotated[str, Form()] = "",
    user: Annotated[CurrentUser, Depends(get_current_user)] = None,
):
    master_key = get_cached_master_key(user.token)
    if master_key is None:
        raise HTTPException(status_code=401, detail="Session expired")

    file_bytes = await file.read()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    db = await get_db()
    try:
        item_id = await service.create_knowledge_upload(
            db,
            filename=file.filename or "upload",
            mime_type=file.content_type or "application/octet-stream",
            file_bytes=file_bytes,
            title=title,
            tags=tag_list,
            master_key=master_key,
        )
        detail = await service.get_knowledge_detail(db, item_id)
        return ApiResponse(data=detail.model_dump())
    finally:
        await db.close()


@router.post("/url", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_url_knowledge(
    body: KnowledgeUrlCreate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    db = await get_db()
    try:
        item_id = await service.create_knowledge_url(
            db, url=body.url, title=body.title, tags=body.tags
        )
        detail = await service.get_knowledge_detail(db, item_id)
        return ApiResponse(data=detail.model_dump())
    finally:
        await db.close()


@router.get("", response_model=ListResponse)
async def list_knowledge(
    q: str = Query(default=""),
    tags: str = Query(default=""),
    include_deleted: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    user: Annotated[CurrentUser, Depends(get_current_user)] = None,
):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    db = await get_db()
    try:
        items, total = await service.get_knowledge_list(
            db, q=q, tag_names=tag_list, include_deleted=include_deleted, offset=offset, limit=limit
        )
        return ListResponse(
            data=items,
            pagination={"offset": offset, "limit": limit, "total": total},
        )
    finally:
        await db.close()


@router.get("/{item_id}", response_model=ApiResponse)
async def get_knowledge(
    item_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    db = await get_db()
    try:
        detail = await service.get_knowledge_detail(db, item_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Knowledge not found")
        return ApiResponse(data=detail.model_dump())
    finally:
        await db.close()


@router.patch("/{item_id}", response_model=ApiResponse)
async def update_knowledge(
    item_id: str,
    body: KnowledgeUpdate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    db = await get_db()
    try:
        ok = await service.update_knowledge(db, item_id, body)
        if not ok:
            raise HTTPException(status_code=404, detail="Knowledge not found")
        detail = await service.get_knowledge_detail(db, item_id)
        return ApiResponse(data=detail.model_dump())
    finally:
        await db.close()


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge(
    item_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    db = await get_db()
    try:
        ok = await service.delete_knowledge(db, item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Knowledge not found")
        return None
    finally:
        await db.close()


@router.get("/tags/all", response_model=TagListResponse)
async def get_tags(
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    db = await get_db()
    try:
        tags = await service.list_tags(db)
        return TagListResponse(data=tags)
    finally:
        await db.close()
