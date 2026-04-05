from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.config import get_settings, PROJECT_ROOT
from src.db.connection import init_db
from src.auth.router import router as auth_router
from src.system.router import router as system_router
from src.knowledge.router import router as knowledge_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await init_db(settings.database_url)
    yield


app = FastAPI(title="AI 知识管理助手", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(system_router)
app.include_router(knowledge_router)

static_dir = PROJECT_ROOT / "src" / "web" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "AI 知识管理助手 API 服务运行中"}
