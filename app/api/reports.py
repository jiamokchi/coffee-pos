"""
app/api/reports.py
財務報表 API：401申報、毛利分析、庫存估值。
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.report_service import (
    calc_gross_profit_by_product,
    calc_inventory_valuation,
    export_401_csv,
    generate_401_report,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/401")
def report_401(
    year: int = Query(..., ge=2020, le=2099, description="申報年度"),
    bimonth: int = Query(..., ge=1, le=6, description="雙月期別（1~6）"),
    db: Session = Depends(get_db),
):
    """取得 401 申報報表（JSON）"""
    report = generate_401_report(db, year=year, bimonth=bimonth)
    return {
        "period": f"{report.period_start} ~ {report.period_end}",
        "taxable_sales": str(report.taxable_sales),
        "zero_rate_sales": str(report.zero_rate_sales),
        "exempt_sales": str(report.exempt_sales),
        "output_tax": str(report.output_tax),
        "invoice_count": report.invoice_count,
    }


@router.get("/401/export-csv")
def export_401(
    year: int = Query(...),
    bimonth: int = Query(..., ge=1, le=6),
    db: Session = Depends(get_db),
):
    """匯出 401 報表為 CSV 檔案"""
    report = generate_401_report(db, year=year, bimonth=bimonth)
    csv_content = export_401_csv(report)
    filename = f"401_{year}_bimonth{bimonth}.csv"
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv; charset=utf-8-sig",   # utf-8-sig 讓 Excel 正確開啟
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/gross-profit")
def report_gross_profit(db: Session = Depends(get_db)):
    """所有商品毛利分析（依毛利率排序）"""
    items = calc_gross_profit_by_product(db)
    return [
        {
            "product_id": i.product_id,
            "product_name": i.product_name,
            "selling_price": str(i.selling_price),
            "bom_cost": str(i.bom_cost),
            "gross_profit": str(i.gross_profit),
            "gross_margin_pct": f"{i.gross_margin_pct}%",
        }
        for i in items
    ]


@router.get("/inventory-valuation")
def report_inventory(db: Session = Depends(get_db)):
    """庫存估值報表（現有庫存 × WAC）"""
    result = calc_inventory_valuation(db)
    result["items"] = [
        {
            "ingredient_id": i.ingredient_id,
            "name": i.name,
            "unit": i.unit,
            "current_stock": str(i.current_stock),
            "avg_unit_cost": str(i.avg_unit_cost),
            "total_value": str(i.total_value),
            "is_low_stock": i.is_low_stock,
        }
        for i in result["items"]
    ]
    return result
