from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import get_current_user

router = APIRouter()


@router.get("")
def list_notifications(db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    notifs = db.scalars(select(models.Notification).where(models.Notification.user_id == current.id).order_by(models.Notification.created_at.desc())).all()
    return [{"id": n.id, "type": n.type.value, "payload": n.payload, "is_read": n.is_read, "created_at": n.created_at.isoformat()} for n in notifs]


@router.post("/{id}/read")
def mark_read(id: int, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    n = db.get(models.Notification, id)
    if not n or n.user_id != current.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    db.commit()
    return {"ok": True}
