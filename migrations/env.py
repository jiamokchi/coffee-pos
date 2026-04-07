"""
migrations/env.py
Alembic 執行環境設定。
- 讀取 .env 取得 DATABASE_URL（不寫死在 alembic.ini）
- 支援 online（連線 DB 執行）與 offline（產生 SQL 腳本）兩種模式
- 自動偵測所有 SQLAlchemy Model，實現 autogenerate
"""
import sys
from logging.config import fileConfig
from pathlib import Path

# 讓 Python 找得到 app 套件
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import context
from sqlalchemy import engine_from_config, pool

# 載入 app 設定與所有 Model（autogenerate 需要）
from app.core.config import get_settings
from app.database import Base
import app.models  # noqa: F401 — 確保所有 Model 都被 import，autogenerate 才完整

# ── Alembic 設定物件 ──────────────────────────────────────────
config = context.config
settings = get_settings()

# 動態注入 DB URL，覆蓋 alembic.ini 的空白 sqlalchemy.url
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 設定 logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# autogenerate 比對目標：所有在 Base.metadata 的 Model
target_metadata = Base.metadata


# ══════════════════════════════════════════════════════════════
# Offline 模式：不需連線，直接輸出 SQL 腳本
# ══════════════════════════════════════════════════════════════
def run_migrations_offline() -> None:
    """
    用途：在 CI/CD 或無法直連 DB 的環境下產出 migration SQL。
    執行：alembic upgrade head --sql > migration.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # 比較選項
        compare_type=True,           # 偵測欄位型別變更
        compare_server_default=True, # 偵測 DEFAULT 值變更
        render_as_batch=True,        # SQLite 必備：支援 ALTER TABLE 模擬
    )
    with context.begin_transaction():
        context.run_migrations()


# ══════════════════════════════════════════════════════════════
# Online 模式：連線 DB 執行 migration
# ══════════════════════════════════════════════════════════════
def run_migrations_online() -> None:
    """
    標準執行模式：alembic upgrade head
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # migration 只需單次連線，不需 pool
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=True,    # SQLite 必備：支援 ALTER TABLE 模擬
        )
        with context.begin_transaction():
            context.run_migrations()


# ── 根據執行模式分派 ──────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
