"""
app/api/ingredients.py
原料 CRUD API
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ingredient
from app.schemas import IngredientCreate, IngredientOut, IngredientUpdate

router = APIRouter(prefix="/ingredients", tags=["Ingredients"])


def _to_out(ing: Ingredient) -> IngredientOut:
    """手動建構回傳物件，避免 lazy loading"""
    return IngredientOut(
        id=ing.id,
        name=ing.name,
        unit=ing.unit,
        min_stock_level=ing.min_stock_level,
        current_stock=ing.current_stock,
        avg_unit_cost=ing.avg_unit_cost,
        last_updated=ing.last_updated,
        is_active=ing.is_active,
        image_url=ing.image_url,
        is_low_stock=ing.current_stock < ing.min_stock_level,
    )


@router.get("", response_model=list[IngredientOut])
def list_ingredients(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    q = db.query(Ingredient)
    if active_only:
        q = q.filter(Ingredient.is_active == True)
    ings = q.order_by(Ingredient.name).all()
    result = [_to_out(i) for i in ings]
    if low_stock_only:
        result = [r for r in result if r.is_low_stock]
    return result


@router.get("/{ingredient_id}", response_model=IngredientOut)
def get_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    ing = db.get(Ingredient, ingredient_id)
    if not ing:
        raise HTTPException(status_code=404, detail=f"原料 {ingredient_id} 不存在")
    return _to_out(ing)


@router.post("", response_model=IngredientOut, status_code=status.HTTP_201_CREATED)
def create_ingredient(payload: IngredientCreate, db: Session = Depends(get_db)):
    ing = Ingredient(
        name=payload.name,
        unit=payload.unit,
        min_stock_level=payload.min_stock_level,
    )
    db.add(ing)
    db.flush()
    db.refresh(ing)
    return _to_out(ing)


@router.patch("/{ingredient_id}", response_model=IngredientOut)
def update_ingredient(
    ingredient_id: int,
    payload: IngredientUpdate,
    db: Session = Depends(get_db),
):
    ing = db.get(Ingredient, ingredient_id)
    if not ing:
        raise HTTPException(status_code=404, detail=f"原料 {ingredient_id} 不存在")
    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(ing, field, val)
    db.flush()
    db.refresh(ing)
    return _to_out(ing)


@router.delete("/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    ing = db.get(Ingredient, ingredient_id)
    if not ing:
        raise HTTPException(status_code=404, detail=f"原料 {ingredient_id} 不存在")
    try:
        db.delete(ing)
        db.flush()
    except Exception:
        raise HTTPException(
            status_code=409,
            detail="此原料已被商品 BOM 引用，請先移除相關配方再刪除"
        )
