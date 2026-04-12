import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.config import get_settings, PROJECT_ROOT
from src.db.connection import init_db, get_db
from src.external.llm import is_llm_available
from src.tasks import queue as tq
from src.auth.router import router as auth_router
from src.system.router import router as system_router
from src.knowledge.router import router as knowledge_router
from src.chat.router import router as chat_router
from src.research.router import router as research_router


def _setup_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_settings.level.upper(), logging.INFO)
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(settings.log_dir / "app.log", encoding="utf-8"),
        ],
    )


async def _health_monitor() -> None:
    """Periodically check external service health and re-queue pending_recheck tasks."""
    logger = logging.getLogger("app")
    while True:
        try:
            await asyncio.sleep(60)
            if not await is_llm_available():
                continue
            db = await get_db()
            try:
                async with db.execute(
                    "SELECT id FROM research_tasks WHERE status = 'pending_recheck'"
                ) as cursor:
                    rows = await cursor.fetchall()
                if rows:
                    now = datetime.now(timezone.utc).isoformat()
                    for (task_id,) in rows:
                        await db.execute(
                            "UPDATE research_tasks SET status = ?, updated_at = ? WHERE id = ?",
                            ("queued", now, task_id),
                        )
                        await db.commit()
                        await tq.submit_task(task_id)
                        logger.info("Re-queued pending_recheck task %s", task_id)
            finally:
                await db.close()
        except Exception:
            logger.exception("Health monitor error")


async def _cleanup_scheduler() -> None:
    """Periodically run version retention and log cleanup."""
    logger = logging.getLogger("app")
    from src.system.service import cleanup_old_versions, cleanup_old_logs

    while True:
        try:
            await asyncio.sleep(86400)  # run once per day
            db = await get_db()
            try:
                removed = await cleanup_old_versions(db)
                if removed:
                    logger.info("Version retention cleanup removed %s versions", removed)
            finally:
                await db.close()
            logs_removed = await cleanup_old_logs()
            if logs_removed:
                logger.info("Log cleanup removed %s files", logs_removed)
        except Exception:
            logger.exception("Cleanup scheduler error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _setup_logging()
    settings = get_settings()
    await init_db(settings.database_url)
    tq.init_concurrency()

    from src.research.worker import run_research_task

    worker_count = max(1, settings.storage_settings.research_concurrency_limit)
    worker_tasks = [
        tq.spawn_worker(run_research_task) for _ in range(worker_count)
    ]
    monitor_task = asyncio.create_task(_health_monitor())
    cleanup_task = asyncio.create_task(_cleanup_scheduler())
    yield
    monitor_task.cancel()
    cleanup_task.cancel()
    for t in worker_tasks:
        t.cancel()


app = FastAPI(title="AI 知识管理助手", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.getLogger("app").exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后重试"},
    )


app.include_router(auth_router)
app.include_router(system_router)
app.include_router(knowledge_router)
app.include_router(chat_router)
app.include_router(research_router)

static_dir = PROJECT_ROOT / "src" / "web" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "AI 知识管理助手 API 服务运行中"}
