"""
app/api/invoices.py
電子發票 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import InvoiceCreate, InvoiceOut
from app.services.invoice_service import InvoiceError, issue_invoice, void_invoice

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.post("", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def api_issue_invoice(payload: InvoiceCreate, db: Session = Depends(get_db)):
    """為已完成訂單開立電子發票"""
    try:
        inv = issue_invoice(
            db=db,
            order_id=payload.order_id,
            carrier_type=payload.carrier_type,
            carrier_id=payload.carrier_id,
            buyer_ubn=payload.buyer_ubn,
        )
        return InvoiceOut.model_validate(inv)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvoiceError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{invoice_id}/void", response_model=InvoiceOut)
def api_void_invoice(
    invoice_id: int,
    reason: str = "",
    db: Session = Depends(get_db),
):
    """作廢電子發票（當月限定）"""
    try:
        inv = void_invoice(db=db, invoice_id=invoice_id, reason=reason)
        return InvoiceOut.model_validate(inv)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvoiceError as e:
        raise HTTPException(status_code=409, detail=str(e))
