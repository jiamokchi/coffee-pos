"""
app/core/config.py
讀取 .env 環境變數，集中管理所有設定。
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── 應用程式基本設定 ─────────────────────────────────────
    APP_NAME: str = "Coffee POS System"
    APP_ENV: str = "development"        # development | production
    DEBUG: bool = True
    USE_SQLITE: bool = False             # 若設為 True，則使用 SQLite

    # ── 資料庫設定 ───────────────────────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "coffee_pos"
    DB_USER: str = "pos_user"
    DB_PASSWORD: str = "changeme"

    # ── 連線池設定 ───────────────────────────────────────────
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    # ── 台灣電子發票 (綠界/財政部 API) ──────────────────────
    INVOICE_API_URL: str = "https://einvoice.nat.gov.tw"
    INVOICE_MERCHANT_ID: str = ""
    INVOICE_API_KEY: str = ""
    TAX_ID: str = ""                    # 店家統一編號

    # ── Google Drive 備份 ────────────────────────────────────
    GDRIVE_CREDENTIALS_FILE: str = "credentials.json"
    GDRIVE_BACKUP_FOLDER_ID: str = ""

    @property
    def DATABASE_URL(self) -> str:
        """根據設定回傳 PostgreSQL 或 SQLite 連線字串"""
        if self.USE_SQLITE:
            return "sqlite:///./coffee_pos.db"
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """非同步連線字串 (asyncpg，視需求啟用)"""
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """單例模式：整個應用共用同一份設定物件"""
    return Settings()
