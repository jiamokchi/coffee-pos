"""
app/database.py
SQLAlchemy 資料庫連線、Session 工廠與依賴注入。
支援同步 ORM（FastAPI route 中使用）。
"""
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── 建立 Engine ──────────────────────────────────────────────────────────────
connect_args = {}
if settings.USE_SQLITE:
    # SQLite 需要此參數才能在 FastAPI 多執行緒環境運作
    connect_args = {"check_same_thread": False}
else:
    # PostgreSQL 台灣時區設定
    connect_args = {"options": "-c timezone=Asia/Taipei"}

engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,        # 常駐連線數
    max_overflow=settings.DB_MAX_OVERFLOW,  # 超過 pool_size 可暫時擴充的上限
    pool_timeout=settings.DB_POOL_TIMEOUT,  # 等待可用連線的秒數
    pool_pre_ping=True,    # 每次取出連線前先 ping，自動重連斷線的 session
    echo=settings.DEBUG,   # DEBUG 模式下印出 SQL，正式環境設為 False
    connect_args=connect_args,
)


# ── 連線事件：確認連線成功 ────────────────────────────────────────────────────
@event.listens_for(engine, "connect")
def on_connect(dbapi_connection, connection_record):
    logger.debug("PostgreSQL 連線建立 ✓")


# ── Session 工廠 ──────────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,   # 手動控制 commit，避免資料不一致
    autoflush=False,    # 避免隱式 flush 造成未預期 DB 寫入
    expire_on_commit=False,  # commit 後物件仍可存取，方便 response 序列化
)


# ── ORM Base ──────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """所有 ORM Model 繼承此 Base"""
    pass


# ── FastAPI 依賴注入：取得 DB Session ─────────────────────────────────────────
def get_db():
    """
    使用 yield 確保每個 request 結束後正確關閉 Session。

    用法（在 router 中）：
        @router.post("/orders")
        def create_order(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()          # 路由正常完成 → 提交
    except Exception:
        db.rollback()        # 發生例外 → 回滾，保持資料一致性
        raise
    finally:
        db.close()           # 不論成功失敗，釋放連線回 pool


# ── 健康檢查工具 ──────────────────────────────────────────────────────────────
def check_db_connection() -> bool:
    """
    應用啟動時呼叫，確認 PostgreSQL 可正常連線。
    回傳 True 表示正常，False 表示異常。
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ 資料庫連線正常")
        return True
    except Exception as e:
        logger.error(f"❌ 資料庫連線失敗：{e}")
        return False
