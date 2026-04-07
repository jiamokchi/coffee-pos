"""
app/services/invoice_service.py
台灣電子發票服務（MIG 4.0）。

支援：
  - 開立發票（一般載具 / 手機條碼 / 自然人憑證 / 公司戶）
  - 作廢發票
  - 隨機碼產生
  - 發票號碼格式驗證
"""
import logging
import random
import re
import string
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Invoice, Order

logger = logging.getLogger(__name__)
settings = get_settings()

# 台灣統一發票號碼格式：2 大寫英文 + 8 位數字
INV_NO_PATTERN = re.compile(r"^[A-Z]{2}\d{8}$")

# 載具類型常數
CARRIER_PHONE  = "3J0002"   # 手機條碼
CARRIER_MOICA  = "CQ0001"   # 自然人憑證


class InvoiceError(Exception):
    """發票作業通用例外"""
    pass


# ══════════════════════════════════════════════════════════════
# 開立發票
# ══════════════════════════════════════════════════════════════

def issue_invoice(
    db: Session,
    order_id: int,
    carrier_type: str | None = None,
    carrier_id: str | None = None,
    buyer_ubn: str | None = None,
) -> Invoice:
    """
    為已完成的訂單開立電子發票。

    流程：
    1. 驗證訂單與載具格式
    2. 呼叫財政部 / 綠界 API 取得發票號碼
    3. 寫入 invoices 資料表

    Args:
        carrier_type: None=雲端發票, 3J0002=手機條碼, CQ0001=自然人憑證
        carrier_id:   載具識別碼（手機條碼 / 憑證號碼）
        buyer_ubn:    買方統一編號（公司戶抬頭）
    """
    order: Order | None = db.get(Order, order_id)
    if order is None:
        raise ValueError(f"訂單 {order_id} 不存在")
    if order.status != "COMPLETED":
        raise InvoiceError("只有已完成的訂單才能開立發票")

    # 避免重複開立
    existing = db.query(Invoice).filter(Invoice.order_id == order_id).first()
    if existing and existing.status == "OPEN":
        raise InvoiceError(f"訂單 {order_id} 已有有效發票 {existing.inv_no}")

    # 驗證載具格式
    if carrier_type and carrier_id:
        _validate_carrier(carrier_type, carrier_id)

    # 驗證統一編號（8位數字）
    if buyer_ubn and not re.match(r"^\d{8}$", buyer_ubn):
        raise ValueError("統一編號格式錯誤（應為 8 位數字）")

    # 呼叫發票 API（取得 inv_no）
    inv_no, random_no = _call_invoice_api(order=order, buyer_ubn=buyer_ubn)

    invoice = Invoice(
        order_id=order_id,
        inv_no=inv_no,
        random_no=random_no,
        buyer_ubn=buyer_ubn,
        carrier_type=carrier_type,
        carrier_id=carrier_id,
        status="OPEN",
        issued_at=datetime.now(tz=timezone.utc),
    )
    db.add(invoice)
    db.flush()

    logger.info(f"✅ 發票開立成功：{inv_no} (訂單 {order_id})")
    return invoice


# ══════════════════════════════════════════════════════════════
# 作廢發票
# ══════════════════════════════════════════════════════════════

def void_invoice(db: Session, invoice_id: int, reason: str = "") -> Invoice:
    """作廢發票（當月才可作廢，跨月需折讓）"""
    invoice: Invoice | None = db.get(Invoice, invoice_id)
    if invoice is None:
        raise ValueError(f"發票 {invoice_id} 不存在")
    if invoice.status != "OPEN":
        raise InvoiceError(f"發票 {invoice.inv_no} 狀態為 {invoice.status}，無法作廢")

    now = datetime.now(tz=timezone.utc)
    issued = invoice.issued_at

    # 判斷是否跨月
    if issued and (now.year != issued.year or now.month != issued.month):
        raise InvoiceError(
            f"發票 {invoice.inv_no} 已跨月（開立於 {issued.date()}），"
            "跨月作廢須改用折讓單，請洽會計"
        )

    # 呼叫 API 作廢
    _call_void_api(inv_no=invoice.inv_no)

    invoice.status = "CANCELLED"
    db.flush()

    logger.info(f"🚫 發票 {invoice.inv_no} 已作廢。原因：{reason or '未說明'}")
    return invoice


# ══════════════════════════════════════════════════════════════
# 內部工具
# ══════════════════════════════════════════════════════════════

def _generate_random_no() -> str:
    """產生 4 位隨機碼"""
    return "".join(random.choices(string.digits, k=4))


def _validate_carrier(carrier_type: str, carrier_id: str) -> None:
    """驗證載具格式"""
    if carrier_type == CARRIER_PHONE:
        # 手機條碼：/ + 7位大寫英數字
        if not re.match(r"^/[A-Z0-9\+\-\.]{7}$", carrier_id):
            raise ValueError(f"手機條碼格式錯誤：{carrier_id}（應為 /XXXXXXX）")
    elif carrier_type == CARRIER_MOICA:
        # 自然人憑證：2 大寫英文 + 14 位數字
        if not re.match(r"^[A-Z]{2}\d{14}$", carrier_id):
            raise ValueError(f"自然人憑證格式錯誤：{carrier_id}")


def _call_invoice_api(order: Order, buyer_ubn: str | None) -> tuple[str, str]:
    """
    呼叫財政部電子發票平台（或綠界科技代開）API。
    此為示意實作，正式環境請依 MIG 4.0 規格對接。

    開發模式：回傳模擬號碼，不呼叫外部 API。
    """
    if settings.APP_ENV == "development" or not settings.INVOICE_API_KEY:
        # 開發/測試：產生模擬發票號碼
        letters = "".join(random.choices(string.ascii_uppercase, k=2))
        digits = "".join(random.choices(string.digits, k=8))
        mock_inv_no = f"{letters}{digits}"
        mock_random = _generate_random_no()
        logger.debug(f"[DEV] 模擬發票號碼：{mock_inv_no}-{mock_random}")
        return mock_inv_no, mock_random

    # 正式環境：呼叫外部 API（以綠界為例，需依實際 API 文件調整）
    try:
        payload = {
            "MerchantID": settings.INVOICE_MERCHANT_ID,
            "RelateNumber": str(order.id),
            "TaxType": "1",          # 1=應稅
            "SalesAmount": int(order.total_amount),
            "Print": "0",
            "Donation": "0",
            "CarrierType": "",
            "Items": [
                {
                    "ItemName": item.product.name,
                    "ItemCount": item.quantity,
                    "ItemWord": "份",
                    "ItemPrice": int(item.unit_price),
                    "ItemTaxType": "1",
                    "ItemAmount": int(item.subtotal),
                }
                for item in order.items
            ],
        }
        if buyer_ubn:
            payload["CustomerIdentifier"] = buyer_ubn

        response = httpx.post(
            f"{settings.INVOICE_API_URL}/B2CInvoice/Issue",
            json=payload,
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("RtnCode") != 1:
            raise InvoiceError(f"發票 API 錯誤：{data.get('RtnMsg')}")

        return data["InvoiceNo"], data["RandomNumber"]

    except httpx.HTTPError as e:
        raise InvoiceError(f"發票 API 連線失敗：{e}") from e


def _call_void_api(inv_no: str) -> None:
    """作廢 API 呼叫（開發模式下略過）"""
    if settings.APP_ENV == "development" or not settings.INVOICE_API_KEY:
        logger.debug(f"[DEV] 模擬作廢發票：{inv_no}")
        return
    # 正式環境對接略（依 MIG 4.0 實作）
