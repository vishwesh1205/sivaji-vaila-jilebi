from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import get_current_user, can_see_all
from ..services.provenance import case_lineage

router = APIRouter()


def _scope(user: models.User, case: models.Case):
    if can_see_all(user):
        return True
    if user.role == models.UserRole.REGIONAL_OFFICER and user.region:
        return bool(case.institution and case.institution.region == user.region)
    if user.bureau_id:
        return case.bureau_id == user.bureau_id
    return False


@router.get("/case/{id}")
def provenance_case(id: int, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    case = db.get(models.Case, id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not _scope(current, case):
        raise HTTPException(status_code=403, detail="Scope violation")
    lineage = case_lineage(db, case)
    if case.category == models.CaseCategory.RAGGING_DISCRIMINATION and not can_see_all(current) and current.bureau_id != case.bureau_id:
        lineage["stage_2_normalized"]["narrative"] = "[RESTRICTED – sensitive narrative masked for non-owning bureau]"
        if lineage["stage_1_raw_payload"].get("payload"):
            masked = dict(lineage["stage_1_raw_payload"]["payload"])
            for k in list(masked.keys()):
                if any(tok in k.lower() for tok in ["narrative", "grievance", "description", "text"]):
                    masked[k] = "[RESTRICTED]"
            lineage["stage_1_raw_payload"]["payload"] = masked
    if case.category == models.CaseCategory.RAGGING_DISCRIMINATION:
        db.add(models.AuditAccessLog(user_id=current.id, resource_type="case_provenance_sensitive", resource_id=str(case.id), reason="Sensitive narrative provenance access"))
        db.commit()
    return lineage
