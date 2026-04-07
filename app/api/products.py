"""
app/api/products.py
商品 CRUD + BOM 配方管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Ingredient, Product, ProductBOM
from app.schemas import BOMItemOut, ProductCreate, ProductOut, ProductUpdate

router = APIRouter(prefix="/products", tags=["Products"])


def _load_product(db: Session, product_id: int) -> Product | None:
    """重新以 selectinload 載入商品，避免 lazy loading 問題"""
    return (
        db.query(Product)
        .options(selectinload(Product.bom_items).selectinload(ProductBOM.ingredient))
        .filter(Product.id == product_id)
        .first()
    )


def _to_out(p: Product) -> ProductOut:
    out = ProductOut.model_validate(p)
    out.bom_items = [
        BOMItemOut(
            id=b.id,
            ingredient_id=b.ingredient_id,
            ingredient_name=b.ingredient.name if b.ingredient else "",
            unit=b.ingredient.unit if b.ingredient else "",
            qty_required=b.qty_required,
        )
        for b in p.bom_items
    ]
    return out


@router.get("", response_model=list[ProductOut])
def list_products(
    active_only: bool = Query(True),
    category: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Product).options(
        selectinload(Product.bom_items).selectinload(ProductBOM.ingredient)
    )
    if active_only:
        q = q.filter(Product.is_active == True)
    if category:
        q = q.filter(Product.category == category)
    return [_to_out(p) for p in q.order_by(Product.category, Product.name).all()]


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = _load_product(db, product_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"商品 {product_id} 不存在")
    return _to_out(p)


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    if payload.barcode:
        if db.query(Product).filter(Product.barcode == payload.barcode).first():
            raise HTTPException(status_code=409, detail="條碼已被其他商品使用")

    product = Product(
        name=payload.name,
        category=payload.category,
        price=payload.price,
        barcode=payload.barcode if payload.barcode else None,
        tax_type=payload.tax_type,
    )
    db.add(product)
    db.flush()

    for bom_item in payload.bom:
        if not db.get(Ingredient, bom_item.ingredient_id):
            raise HTTPException(status_code=404, detail=f"原料 ID {bom_item.ingredient_id} 不存在")
        db.add(ProductBOM(
            product_id=product.id,
            ingredient_id=bom_item.ingredient_id,
            qty_required=bom_item.qty_required,
        ))

    db.flush()
    # 重新查詢以載入 relationships
    p = _load_product(db, product.id)
    return _to_out(p)


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"商品 {product_id} 不存在")

    for field, val in payload.model_dump(exclude_unset=True, exclude={"bom"}).items():
        setattr(product, field, val)

    if payload.bom is not None:
        db.query(ProductBOM).filter(ProductBOM.product_id == product_id).delete()
        for bom_item in payload.bom:
            db.add(ProductBOM(
                product_id=product_id,
                ingredient_id=bom_item.ingredient_id,
                qty_required=bom_item.qty_required,
            ))

    db.flush()
    p = _load_product(db, product_id)
    return _to_out(p)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """
    實體刪除商品。若已有訂單關聯，則報 409 錯誤建議改用下架。
    """
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"商品 {product_id} 不存在")

    # 檢查是否有訂單關聯 (OrderItem)
    from app.models import OrderItem
    if db.query(OrderItem).filter(OrderItem.product_id == product_id).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="此商品已有歷史訂單紀錄，不可刪除。請改用「下架」功能。"
        )

    db.delete(product)
    db.flush()


@router.patch("/{product_id}/deactivate", response_model=ProductOut)
def deactivate_product_shortcut(product_id: int, db: Session = Depends(get_db)):
    """將商品設為下架的捷徑"""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"商品 {product_id} 不存在")
    product.is_active = False
    db.flush()
    return _to_out(product)
