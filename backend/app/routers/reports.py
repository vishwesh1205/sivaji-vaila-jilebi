import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import get_current_user, can_see_all

router = APIRouter()


def _scope_cases(db, current):
    stmt = select(models.Case)
    if not can_see_all(current):
        if current.role == models.UserRole.REGIONAL_OFFICER and current.region:
            stmt = stmt.join(models.Institution).where(models.Institution.region == current.region)
        elif current.bureau_id:
            stmt = stmt.where(models.Case.bureau_id == current.bureau_id)
        else:
            return []
    return db.scalars(stmt).all()


@router.get("/{report_type}")
def get_report(report_type: str, format: str = Query(default="json"), db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    cases = _scope_cases(db, current)
    if report_type == "bureau-wise":
        bureaus = db.scalars(select(models.Bureau)).all()
        data = []
        for b in bureaus:
            bc = [c for c in cases if c.bureau_id == b.id]
            data.append({"bureau_code": b.code, "bureau_name": b.name, "total": len(bc), "pending": sum(1 for c in bc if c.status == models.CaseStatus.PENDING), "under_process": sum(1 for c in bc if c.status == models.CaseStatus.UNDER_PROCESS), "disposed": sum(1 for c in bc if c.status == models.CaseStatus.DISPOSED), "escalated": sum(1 for c in bc if c.status == models.CaseStatus.ESCALATED)})
    elif report_type == "region-wise":
        by_region = {}
        for c in cases:
            r = c.institution.region if c.institution else "UNKNOWN"
            by_region.setdefault(r, []).append(c)
        data = [{"region": k, "cases": len(v), "pending": sum(1 for c in v if c.status == models.CaseStatus.PENDING), "disposed": sum(1 for c in v if c.status == models.CaseStatus.DISPOSED)} for k, v in by_region.items()]
    elif report_type == "institution-wise":
        by_inst = {}
        for c in cases:
            if not c.institution:
                continue
            by_inst.setdefault(c.institution.id, {"inst": c.institution, "cases": []})
            by_inst[c.institution.id]["cases"].append(c)
        data = [{"aicte_permanent_id": v["inst"].aicte_permanent_id, "institution": v["inst"].name, "region": v["inst"].region, "cases": len(v["cases"]), "active": sum(1 for c in v["cases"] if c.status in [models.CaseStatus.PENDING, models.CaseStatus.UNDER_PROCESS, models.CaseStatus.ESCALATED])} for v in by_inst.values()]
    elif report_type == "status-wise":
        data = [{"status": s.value, "count": sum(1 for c in cases if c.status == s)} for s in models.CaseStatus]
    elif report_type == "ageing":
        buckets = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
        for c in cases:
            if c.status not in [models.CaseStatus.PENDING, models.CaseStatus.UNDER_PROCESS, models.CaseStatus.ESCALATED]:
                continue
            days = (datetime.utcnow() - c.date_received).days
            if days <= 30:
                buckets["0-30"] += 1
            elif days <= 60:
                buckets["31-60"] += 1
            elif days <= 90:
                buckets["61-90"] += 1
            else:
                buckets["90+"] += 1
        data = [{"bucket": k, "count": v} for k, v in buckets.items()]
    elif report_type == "disposal-rate":
        total = len(cases)
        disposed = sum(1 for c in cases if c.status == models.CaseStatus.DISPOSED)
        data = [{"total": total, "disposed": disposed, "disposal_rate": round((disposed / total * 100), 2) if total else 0.0}]
    elif report_type == "overlaps":
        alerts = db.scalars(select(models.OverlapAlert)).all()
        data = [{"id": a.id, "institution": a.institution.name if a.institution else None, "bureaus_involved": a.bureaus_involved, "case_count": len(a.case_ids), "status": a.status.value, "created_at": a.created_at.isoformat()} for a in alerts]
    elif report_type == "monthly-performance":
        by_month = {}
        for c in cases:
            key = c.date_received.strftime("%Y-%m")
            by_month.setdefault(key, {"received": 0, "disposed": 0})
            by_month[key]["received"] += 1
            if c.status == models.CaseStatus.DISPOSED:
                by_month[key]["disposed"] += 1
        data = [{"month": k, **v, "disposal_rate": round(v["disposed"] / v["received"] * 100, 2) if v["received"] else 0.0} for k, v in sorted(by_month.items())]
    else:
        raise HTTPException(status_code=400, detail="Unknown report type")

    if format == "csv":
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        output.seek(0)
        return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={report_type}.csv"})
    if format == "xlsx":
        try:
            import openpyxl

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = report_type
            if data:
                ws.append(list(data[0].keys()))
                for row in data:
                    ws.append([row.get(k) for k in data[0].keys()])
            bio = io.BytesIO()
            wb.save(bio)
            bio.seek(0)
            return StreamingResponse(iter([bio.getvalue()]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={report_type}.xlsx"})
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    if format == "pdf":
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            bio = io.BytesIO()
            c = canvas.Canvas(bio, pagesize=letter)
            c.setFont("Helvetica", 12)
            c.drawString(50, 750, f"Report: {report_type}")
            y = 720
            if data:
                text = str(data[:50])
                for line in text.split("\n"):
                    c.drawString(50, y, line[:90])
                    y -= 15
                    if y < 50:
                        break
            c.save()
            bio.seek(0)
            return StreamingResponse(iter([bio.getvalue()]), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={report_type}.pdf"})
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {"report_type": report_type, "data": data}
