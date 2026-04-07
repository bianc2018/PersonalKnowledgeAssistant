from datetime import datetime, timezone

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field
from src.auth.crypto import hash_password, generate_salt
from src.auth.dependencies import CurrentUser, get_current_user
from src.config import get_settings
from src.db.connection import get_db
from src.system import service as system_service

router = APIRouter(prefix="/api/system", tags=["system"])


class InitRequest(BaseModel):
    password: str = Field(..., min_length=8)


class InitResponse(BaseModel):
    message: str


class ConfigPutRequest(BaseModel):
    llm_config: dict | None = None
    embedding_config: dict | None = None
    search_config: dict | None = None
    privacy_settings: dict | None = None
    retry_settings: dict | None = None
    storage_settings: dict | None = None
    log_settings: dict | None = None


class PasswordRequest(BaseModel):
    password: str


class StatusResponse(BaseModel):
    initialized: bool
    version: str = "0.1.0"
    llm_connected: bool = False
    search_source_available: str | None = None
    embedding_available: bool = False
    knowledge_count: int = 0
    storage_used_bytes: int = 0


@router.post("/init", response_model=InitResponse, status_code=status.HTTP_201_CREATED)
async def system_init(body: InitRequest):
    settings = get_settings()
    db = await get_db()
    try:
        async with db.execute(
            "SELECT initialized FROM system_config WHERE id = 1"
        ) as cursor:
            row = await cursor.fetchone()

        if row and row[0]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="System already initialized",
            )

        if not any(c.isalpha() for c in body.password) or not any(c.isdigit() for c in body.password):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must contain at least one letter and one digit",
            )

        salt = generate_salt()
        password_hash = hash_password(body.password)
        now = datetime.now(timezone.utc).isoformat()

        await db.execute(
            """
            INSERT INTO system_config (
                id, initialized, password_hash, salt,
                llm_config, embedding_config, search_config,
                privacy_settings, retry_settings, storage_settings, log_settings, updated_at
            ) VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                initialized=excluded.initialized,
                password_hash=excluded.password_hash,
                salt=excluded.salt,
                updated_at=excluded.updated_at
            """,
            (
                1,
                password_hash,
                salt,
                "{}",
                "{}",
                "{}",
                '{"allow_full_content": false, "allow_web_search": true, "allow_log_upload": false}',
                '{"retry_times": 3, "timeout_seconds": 30}',
                '{"archive_threshold_gb": 10.0, "research_concurrency_limit": 2, "version_retention_policy": null}',
                '{"level": "INFO", "retention_days": 30}',
                now,
            ),
        )
        await db.commit()
        return InitResponse(message="系统初始化完成")
    finally:
        await db.close()


@router.get("/status", response_model=StatusResponse)
async def system_status():
    settings = get_settings()
    db = await get_db()
    try:
        async with db.execute(
            "SELECT initialized FROM system_config WHERE id = 1"
        ) as cursor:
            row = await cursor.fetchone()

        initialized = bool(row[0]) if row else False

        llm_connected = False
        embedding_available = False
        search_source = None

        if initialized:
            async with db.execute(
                "SELECT llm_config, embedding_config, search_config FROM system_config WHERE id = 1"
            ) as cursor:
                cfg_row = await cursor.fetchone()
            if cfg_row:
                import json
                llm_cfg = json.loads(cfg_row[0]) if cfg_row[0] else {}
                emb_cfg = json.loads(cfg_row[1]) if cfg_row[1] else {}
                srch_cfg = json.loads(cfg_row[2]) if cfg_row[2] else {}
                llm_connected = bool(llm_cfg.get("base_url") and llm_cfg.get("api_key") and llm_cfg.get("model"))
                embedding_available = bool(emb_cfg.get("base_url") and emb_cfg.get("api_key") and emb_cfg.get("model"))
                search_source = srch_cfg.get("provider") if srch_cfg else None

        async with db.execute(
            "SELECT COUNT(*) FROM knowledge_items WHERE is_deleted = 0"
        ) as cursor:
            count_row = await cursor.fetchone()

        knowledge_count = count_row[0] if count_row else 0

        files_dir = settings.files_dir
        storage_used = sum(f.stat().st_size for f in files_dir.rglob("*") if f.is_file()) if files_dir.exists() else 0

        return StatusResponse(
            initialized=initialized,
            llm_connected=llm_connected,
            search_source_available=search_source,
            embedding_available=embedding_available,
            knowledge_count=knowledge_count,
            storage_used_bytes=storage_used,
        )
    finally:
        await db.close()


@router.get("/config")
async def get_config(
    user: Annotated[CurrentUser, Depends(get_current_user)] = None,
):
    db = await get_db()
    try:
        cfg = await system_service.load_config(db)
        # Mask api keys
        for key in ("llm_config", "embedding_config", "search_config"):
            if key in cfg and cfg[key] and isinstance(cfg[key], dict) and cfg[key].get("api_key"):
                cfg[key]["api_key"] = cfg[key]["api_key"][:4] + "****"
        return {"data": cfg}
    finally:
        await db.close()


@router.put("/config")
async def put_config(
    body: ConfigPutRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)] = None,
):
    db = await get_db()
    try:
        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        cfg = await system_service.update_config(db, updates)
        return {"data": cfg}
    finally:
        await db.close()


@router.post("/export")
async def export_system(
    body: PasswordRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)] = None,
):
    db = await get_db()
    try:
        data = await system_service.export_backup(db, body.password)
        return Response(
            content=data,
            media_type="application/octet-stream",
            headers={"Content-Disposition": 'attachment; filename="backup.zip.enc"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        await db.close()


@router.post("/import")
async def import_system(
    file: Annotated[UploadFile, File()],
    password: Annotated[str, Form()] = "",
    user: Annotated[CurrentUser, Depends(get_current_user)] = None,
):
    file_bytes = await file.read()
    db = await get_db()
    try:
        result = await system_service.import_backup(db, file_bytes, password)
        return {"data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        await db.close()


@router.post("/reset")
async def reset_system(
    body: PasswordRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)] = None,
):
    db = await get_db()
    try:
        await system_service.reset_system(db, body.password)
        return {"data": {"message": "系统已重置。所有本地加密数据已清除，请重新初始化并导入备份。"}}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        await db.close()
