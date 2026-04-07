"""
app/services/report_service.py
財務報表服務：
  - 401 申報報表（雙月，含應稅/零稅率/免稅分類）
  - 毛利分析（售價 - BOM 原料成本）
  - 庫存估值（現有庫存 × WAC）
"""
import csv
import io
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Ingredient, Invoice, Order, OrderItem, Product, ProductBOM

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# 401 申報報表
# ══════════════════════════════════════════════════════════════

@dataclass
class Tax401Report:
    period_start: date
    period_end: date
    taxable_sales: Decimal = Decimal("0")       # 應稅銷售額（未稅）
    zero_rate_sales: Decimal = Decimal("0")     # 零稅率銷售額
    exempt_sales: Decimal = Decimal("0")        # 免稅銷售額
    output_tax: Decimal = Decimal("0")          # 銷項稅額（5%）
    invoice_count: int = 0


TAX_RATE = Decimal("0.05")


def generate_401_report(
    db: Session,
    year: int,
    bimonth: int,   # 1=1~2月, 2=3~4月, 3=5~6月, 4=7~8月, 5=9~10月, 6=11~12月
) -> Tax401Report:
    """
    產生台灣 401 報表（雙月申報）。

    Args:
        year:     申報年度
        bimonth:  雙月期別（1~6）
    """
    if not 1 <= bimonth <= 6:
        raise ValueError("bimonth 必須介於 1~6")

    start_month = (bimonth - 1) * 2 + 1
    end_month = start_month + 1
    period_start = date(year, start_month, 1)

    # 計算期末日（避免跨年問題）
    if end_month == 12:
        period_end = date(year, 12, 31)
    else:
        period_end = date(year, end_month + 1, 1).replace(day=1)
        from datetime import timedelta
        period_end = period_end - timedelta(days=1)

    report = Tax401Report(period_start=period_start, period_end=period_end)

    # 查詢區間內已開立的發票
    invoices = (
        db.query(Invoice)
        .join(Order, Invoice.order_id == Order.id)
        .filter(
            Invoice.status == "OPEN",
            Order.status == "COMPLETED",
            Order.completed_at >= datetime.combine(period_start, datetime.min.time()),
            Order.completed_at <= datetime.combine(period_end, datetime.max.time()),
        )
        .all()
    )

    for inv in invoices:
        order: Order = inv.order
        report.invoice_count += 1

        for item in order.items:
            subtotal = item.subtotal
            tax_type = item.product.tax_type  # TAX / ZERO / EXEMPT

            if tax_type == "TAX":
                # 含稅金額拆解：未稅 = 含稅 / 1.05
                untaxed = (subtotal / (1 + TAX_RATE)).quantize(Decimal("1"))
                tax = subtotal - untaxed
                report.taxable_sales += untaxed
                report.output_tax += tax
            elif tax_type == "ZERO":
                report.zero_rate_sales += subtotal
            elif tax_type == "EXEMPT":
                report.exempt_sales += subtotal

    logger.info(
        f"401報表 {year}/{start_month}~{end_month}："
        f"應稅 {report.taxable_sales}，稅額 {report.output_tax}，"
        f"發票 {report.invoice_count} 張"
    )
    return report


def export_401_csv(report: Tax401Report) -> str:
    """將 401 報表匯出為 CSV 字串（可直接回傳為 StreamingResponse）"""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["項目", "金額（元）"])
    writer.writerow(["申報期間", f"{report.period_start} ~ {report.period_end}"])
    writer.writerow(["應稅銷售額（未稅）", str(report.taxable_sales)])
    writer.writerow(["零稅率銷售額", str(report.zero_rate_sales)])
    writer.writerow(["免稅銷售額", str(report.exempt_sales)])
    writer.writerow(["銷項稅額", str(report.output_tax)])
    writer.writerow(["發票張數", str(report.invoice_count)])

    return output.getvalue()


# ══════════════════════════════════════════════════════════════
# 毛利分析
# ══════════════════════════════════════════════════════════════

@dataclass
class ProductGrossProfit:
    product_id: int
    product_name: str
    selling_price: Decimal
    bom_cost: Decimal            # Σ(原料用量 × WAC)
    gross_profit: Decimal        # 售價 - BOM 成本
    gross_margin_pct: Decimal    # 毛利率 %


def calc_gross_profit_by_product(db: Session) -> list[ProductGrossProfit]:
    """
    計算所有上架商品的毛利，使用當下的 WAC 為成本基準。
    """
    products = db.query(Product).filter(Product.is_active == True).all()
    results = []

    for product in products:
        bom_cost = Decimal("0")
        for bom_item in product.bom_items:
            ing: Ingredient = bom_item.ingredient
            bom_cost += bom_item.qty_required * ing.avg_unit_cost

        gross_profit = product.price - bom_cost
        margin = (
            (gross_profit / product.price * 100).quantize(Decimal("0.01"))
            if product.price > 0
            else Decimal("0")
        )

        results.append(ProductGrossProfit(
            product_id=product.id,
            product_name=product.name,
            selling_price=product.price,
            bom_cost=bom_cost.quantize(Decimal("0.01")),
            gross_profit=gross_profit.quantize(Decimal("0.01")),
            gross_margin_pct=margin,
        ))

    return sorted(results, key=lambda x: x.gross_margin_pct, reverse=True)


# ══════════════════════════════════════════════════════════════
# 庫存估值報表
# ══════════════════════════════════════════════════════════════

@dataclass
class InventoryValuationItem:
    ingredient_id: int
    name: str
    unit: str
    current_stock: Decimal
    avg_unit_cost: Decimal
    total_value: Decimal         # 現有庫存量 × WAC
    is_low_stock: bool


def calc_inventory_valuation(db: Session) -> dict:
    """
    庫存估值：計算全部原料的帳面價值。
    回傳總估值與明細清單。
    """
    ingredients = db.query(Ingredient).all()
    items = []
    total_value = Decimal("0")

    for ing in ingredients:
        value = ing.current_stock * ing.avg_unit_cost
        total_value += value
        items.append(InventoryValuationItem(
            ingredient_id=ing.id,
            name=ing.name,
            unit=ing.unit,
            current_stock=ing.current_stock,
            avg_unit_cost=ing.avg_unit_cost,
            total_value=value.quantize(Decimal("0.01")),
            is_low_stock=ing.current_stock < ing.min_stock_level,
        ))

    return {
        "total_value": total_value.quantize(Decimal("0.01")),
        "item_count": len(items),
        "low_stock_count": sum(1 for i in items if i.is_low_stock),
        "items": items,
    }
