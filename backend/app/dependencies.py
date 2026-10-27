from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_roles(*roles: models.UserRole):
    def _require(current: Annotated[models.User, Depends(get_current_user)]):
        if current.role not in roles and current.role != models.UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current

    return _require


def can_see_all(current: models.User) -> bool:
    return current.role in {models.UserRole.ADMIN, models.UserRole.MANAGEMENT}


def apply_region_scope(query, current: models.User, case_model: type[models.Case]):
    if can_see_all(current):
        return query
    if current.role == models.UserRole.REGIONAL_OFFICER and current.region:
        from sqlalchemy import select

        return query.join(case_model.institution).where(models.Institution.region == current.region)
    if current.bureau_id:
        return query.where(case_model.bureau_id == current.bureau_id)
    return query.where(False)
