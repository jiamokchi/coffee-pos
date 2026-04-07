"""
app/main.py
FastAPI 應用程式入口。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.core.config import get_settings
from app.database import Base, check_db_connection, engine
from app.api import orders, inventory, reports, products, ingredients, invoices, images

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用啟動 / 關閉鉤子"""
    # 啟動：建立資料表（開發用；正式環境請改用 alembic migrate）
    Base.metadata.create_all(bind=engine)
    check_db_connection()
    yield
    # 關閉：可在此釋放資源


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 掛載路由 ───────────────────────────────────────────────────
PREFIX = "/api/v1"
app.include_router(products.router,    prefix=PREFIX)
app.include_router(ingredients.router, prefix=PREFIX)
app.include_router(orders.router,      prefix=PREFIX)
app.include_router(inventory.router,   prefix=PREFIX)
app.include_router(invoices.router,    prefix=PREFIX)
app.include_router(reports.router,     prefix=PREFIX)
app.include_router(images.router,      prefix=PREFIX)

@app.get("/health")
def health_check():
    return {"status": "ok", "db": check_db_connection(), "version": "1.1.0"}


@app.get("/debug/routes")
def debug_routes():
    """列出所有已註冊路由（用於確認 images router 已載入）"""
    return [{"path": r.path, "methods": list(r.methods)} for r in app.routes if hasattr(r, "methods")]


# ── 掛載前端靜態檔案 ───────────────────────────────────────────
# 優先順序：API 路由 > 靜態檔案 > SPA Index Fallback
FRONTEND_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")

if os.path.exists(FRONTEND_PATH):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_PATH, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # 如果路徑不是以 api 開頭，且不是現有檔案，就回傳 index.html (React Router)
        file_path = os.path.join(FRONTEND_PATH, full_path)
        if not full_path.startswith("api/") and not os.path.isfile(file_path):
            return FileResponse(os.path.join(FRONTEND_PATH, "index.html"))
        return FileResponse(file_path)
