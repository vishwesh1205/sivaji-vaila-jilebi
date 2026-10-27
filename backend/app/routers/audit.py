from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import get_current_user

router = APIRouter()


@router.get("/verify-chain/{case_id}")
def verify_chain(case_id: str, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    case = db.scalar(select(models.Case).where(models.Case.case_id == case_id))
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    actions = db.scalars(select(models.CaseAction).where(models.CaseAction.case_id == case.id).order_by(models.CaseAction.created_at.asc())).all()
    ok = True
    prev = "0" * 64
    for i, a in enumerate(actions):
        if a.prev_hash != prev:
            ok = False
            break
        prev = a.hash
    return {"case_id": case_id, "actions": len(actions), "chain_valid": ok}
