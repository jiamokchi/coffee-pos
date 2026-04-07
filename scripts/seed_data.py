"""
scripts/seed_data.py
開發用測試資料匯入。執行：python scripts/seed_data.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from decimal import Decimal
from app.database import SessionLocal
from app.models import Ingredient, Product, ProductBOM
from app.services.inventory_service import stock_in


def seed():
    db = SessionLocal()
    try:
        # ── 原料 ────────────────────────────────────────────
        ings = {
            "espresso": Ingredient(name="濃縮咖啡液", unit="ml",  min_stock_level=Decimal("500")),
            "milk":     Ingredient(name="全脂牛奶",   unit="ml",  min_stock_level=Decimal("1000")),
            "oat_milk": Ingredient(name="燕麥奶",     unit="ml",  min_stock_level=Decimal("500")),
            "matcha":   Ingredient(name="抹茶粉",     unit="g",   min_stock_level=Decimal("100")),
            "cocoa":    Ingredient(name="可可粉",     unit="g",   min_stock_level=Decimal("100")),
            "syrup":    Ingredient(name="糖漿",       unit="ml",  min_stock_level=Decimal("200")),
            "croissant":Ingredient(name="可頌麵糰",   unit="個",  min_stock_level=Decimal("5")),
            "cheese_tart":Ingredient(name="乳酪塔麵糰", unit="個", min_stock_level=Decimal("5")),
            "sparkling":Ingredient(name="氣泡水",     unit="ml",  min_stock_level=Decimal("500")),
            "drip_bag": Ingredient(name="濾掛咖啡包", unit="包",  min_stock_level=Decimal("20")),
        }
        for ing in ings.values():
            db.add(ing)
        db.flush()

        # 進貨（順便建立 WAC）
        stock_in(db, ings["espresso"].id, Decimal("5000"), Decimal("0.50"))
        stock_in(db, ings["milk"].id,     Decimal("10000"),Decimal("0.06"))
        stock_in(db, ings["oat_milk"].id, Decimal("5000"), Decimal("0.10"))
        stock_in(db, ings["matcha"].id,   Decimal("500"),  Decimal("1.50"))
        stock_in(db, ings["cocoa"].id,    Decimal("500"),  Decimal("0.80"))
        stock_in(db, ings["syrup"].id,    Decimal("2000"), Decimal("0.08"))
        stock_in(db, ings["croissant"].id,Decimal("30"),   Decimal("25"))
        stock_in(db, ings["cheese_tart"].id,Decimal("20"), Decimal("35"))
        stock_in(db, ings["sparkling"].id,Decimal("10000"),Decimal("0.02"))
        stock_in(db, ings["drip_bag"].id, Decimal("200"),  Decimal("12"))

        # ── 商品 + BOM ───────────────────────────────────────
        menu = [
            {
                "name":"拿鐵","category":"咖啡","price":120,"icon":"☕",
                "bom":[("espresso",30),("milk",200),("syrup",10)],
            },
            {
                "name":"卡布奇諾","category":"咖啡","price":120,"icon":"☕",
                "bom":[("espresso",30),("milk",150)],
            },
            {
                "name":"美式","category":"咖啡","price":90,"icon":"☕",
                "bom":[("espresso",60)],
            },
            {
                "name":"燕麥拿鐵","category":"咖啡","price":140,"icon":"☕",
                "bom":[("espresso",30),("oat_milk",200)],
            },
            {
                "name":"抹茶拿鐵","category":"茶飲","price":130,"icon":"🍵",
                "bom":[("matcha",8),("milk",200),("syrup",15)],
            },
            {
                "name":"可可","category":"飲品","price":115,"icon":"🥛",
                "bom":[("cocoa",15),("milk",200),("syrup",20)],
            },
            {
                "name":"氣泡水","category":"飲品","price":50,"icon":"💧",
                "bom":[("sparkling",350)],
            },
            {
                "name":"可頌","category":"餐點","price":65,"icon":"🥐",
                "bom":[("croissant",1)],
            },
            {
                "name":"乳酪塔","category":"餐點","price":80,"icon":"🧀",
                "bom":[("cheese_tart",1)],
            },
            {
                "name":"濾掛咖啡","category":"熟豆","price":30,"icon":"📦",
                "bom":[("drip_bag",1)],
            },
        ]

        for item in menu:
            p = Product(
                name=item["name"],
                category=item["category"],
                price=Decimal(str(item["price"])),
                tax_type="TAX",
            )
            db.add(p)
            db.flush()
            for ing_key, qty in item["bom"]:
                db.add(ProductBOM(
                    product_id=p.id,
                    ingredient_id=ings[ing_key].id,
                    qty_required=Decimal(str(qty)),
                ))

        db.commit()
        print("✅ 測試資料匯入完成")
        print(f"   原料：{len(ings)} 筆")
        print(f"   商品：{len(menu)} 筆")

    except Exception as e:
        db.rollback()
        print(f"❌ 匯入失敗：{e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
