# 系統規範與架構 (Rule & Architecture)

## 1. 系統環境需求

| 軟體 | 版本 | 下載 |
|---|---|---|
| Docker Desktop | 4.x 以上 | https://www.docker.com/products/docker-desktop/ |
| Node.js | 18 LTS 以上 | https://nodejs.org |
| Windows | 10 / 11 (64-bit) | — |

> Docker Desktop 安裝時請確認啟用 **WSL 2 Backend**。

## 2. 目錄結構架構

```
coffee_pos/
├── start.bat              ← 一鍵啟動（日常使用）
├── stop.bat               ← 關閉所有服務
├── setup.bat              ← 首次安裝精靈
├── create_shortcut.ps1    ← 建立桌面捷徑
├── docker-compose.yml     ← 服務編排
├── Dockerfile             ← API 容器設定
├── .env.example           ← 環境變數範本
│
├── app/                   ← FastAPI 後端
│   ├── main.py            ← 應用程式入口
│   ├── database.py        ← SQLAlchemy 連線
│   ├── models.py          ← ORM 資料模型
│   ├── schemas/           ← Pydantic 驗證
│   ├── api/               ← 路由層
│   │   ├── products.py
│   │   ├── ingredients.py
│   │   ├── orders.py
│   │   ├── inventory.py
│   │   ├── invoices.py
│   │   └── reports.py
│   ├── services/          ← 業務邏輯層
│   │   ├── bom_service.py       ← BOM 庫存扣減
│   │   ├── inventory_service.py ← 進貨 / WAC
│   │   ├── invoice_service.py   ← 電子發票
│   │   └── report_service.py    ← 財務報表
│   └── core/
│       └── config.py      ← 環境變數設定
│
├── migrations/            ← Alembic DB 版本管理
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
│
├── frontend/              ← React 前端
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx        ← 路由 + 導覽列
│   │   ├── index.css      ← 全域樣式
│   │   ├── lib/api.js     ← Axios 共用設定
│   │   ├── pages/
│   │   │   ├── Cashier.jsx    ← 收銀介面
│   │   │   ├── Inventory.jsx  ← 庫存管理
│   │   │   ├── Products.jsx   ← 商品管理
│   │   │   └── Reports.jsx    ← 財務報表
│   │   └── components/
│   │       └── NavIcon.jsx
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
├── scripts/
│   └── seed_data.py       ← 開發用測試資料
├── tests/
│   └── test_bom_service.py
├── backups/               ← 自動備份目錄（每日 pg_dump）
└── logs/                  ← 服務日誌
```

## 3. 開發與測試規範

- 採用 FastAPI 作為後端，React 作為前端。
- 資料庫更新應使用 Alembic 進行 Migration：
  ```bat
  docker compose exec api alembic revision --autogenerate -m "新增欄位說明"
  docker compose exec api alembic upgrade head
  ```
- 自動備份系統每 24 小時執行 `pg_dump`，存放於 `backups\`。

## 4. 根因對策記錄 (Troubleshooting)

**Q: start.bat 顯示「Docker Desktop 未執行」**
A: 先開啟 Docker Desktop，等待畫面出現 "Docker Desktop is running" 後再執行。

**Q: API 60 秒內未就緒**
A: 執行 `docker compose logs api` 查看錯誤訊息。常見原因是 .env 密碼與 DB 不一致。

**Q: 前端顯示「無法連線 API」**
A: 確認 `frontend/.env.local` 中 `VITE_API_URL=http://localhost:8000/api/v1`。

**Q: 如何重設資料庫**
A: 執行以下命令：
```bat
docker compose down -v    ← 刪除 volume（所有資料清空）
start.bat                 ← 重新初始化
```

**Q: 手動匯入測試資料**
A: 執行：
```bat
docker compose exec api python scripts/seed_data.py
```
