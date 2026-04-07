"""
app/api/images.py
圖片上傳 API — 將圖片存為 base64 data URL，不依賴外部儲存。
適合單機 POS 使用場景。
"""
import base64
import io
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ingredient, Product

router = APIRouter(prefix="/images", tags=["Images"])

MAX_SIZE = 2 * 1024 * 1024   # 2 MB
ALLOWED  = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def _to_data_url(file_bytes: bytes, content_type: str) -> str:
    b64 = base64.b64encode(file_bytes).decode()
    return f"data:{content_type};base64,{b64}"


@router.post("/ingredient/{ingredient_id}")
async def upload_ingredient_image(
    ingredient_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ing = db.get(Ingredient, ingredient_id)
    if not ing:
        raise HTTPException(404, f"原料 {ingredient_id} 不存在")
    _validate(file)
    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(413, "圖片超過 2MB 上限")
    ing.image_url = _to_data_url(data, file.content_type)
    db.flush()
    return {"image_url": ing.image_url[:80] + "..."}


@router.post("/product/{product_id}")
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    prod = db.get(Product, product_id)
    if not prod:
        raise HTTPException(404, f"商品 {product_id} 不存在")
    _validate(file)
    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(413, "圖片超過 2MB 上限")
    prod.image_url = _to_data_url(data, file.content_type)
    db.flush()
    return {"image_url": prod.image_url[:80] + "..."}


@router.delete("/ingredient/{ingredient_id}")
def delete_ingredient_image(ingredient_id: int, db: Session = Depends(get_db)):
    ing = db.get(Ingredient, ingredient_id)
    if not ing:
        raise HTTPException(404, "原料不存在")
    ing.image_url = None
    return {"ok": True}


@router.delete("/product/{product_id}")
def delete_product_image(product_id: int, db: Session = Depends(get_db)):
    prod = db.get(Product, product_id)
    if not prod:
        raise HTTPException(404, "商品不存在")
    prod.image_url = None
    return {"ok": True}


def _validate(file: UploadFile):
    if file.content_type not in ALLOWED:
        raise HTTPException(415, f"不支援的圖片格式：{file.content_type}。請使用 JPG/PNG/WebP")
