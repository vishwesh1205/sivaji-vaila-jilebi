from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import io
import json
import os
import sqlite3
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.datastructures import UploadFile

from . import dashboard_adapter, db, i18n, repository
from .services import (
    CATEGORIES,
    ORGANISATIONS,
    REGIONS,
    STATUSES,
    event_label,
    format_datetime,
    is_closed,
    status_tone,
    validate_complaint,
    validate_contact,
    validate_feedback,
    validate_reminder,
)

APP_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
SESSION_COOKIE = "cpgrams_demo_session"
FLASH_COOKIE = "cpgrams_demo_flash"
LANG_COOKIE = "cpgrams_lang"
OFFICIAL_URL = "https://pgportal.gov.in"
DISCLAIMER = (
    "EDUCATIONAL DEMO — UNOFFICIAL REPLICA. NOT CONNECTED TO THE GOVERNMENT OF INDIA. "
    "NO REAL GOVERNMENT GRIEVANCE IS FILED."
)
ALLOWED_ATTACHMENTS = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
MAX_ATTACHMENT_BYTES = 2 * 1024 * 1024

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)
env.filters["dt"] = format_datetime
env.filters["status_tone"] = status_tone
env.filters["event_label"] = event_label
env.filters["urlencode"] = lambda value: quote(str(value), safe="")
env.globals.update(
    disclaimer=DISCLAIMER,
    official_url=OFFICIAL_URL,
    categories=CATEGORIES,
    organisations=ORGANISATIONS,
    regions=REGIONS,
    status_values=STATUSES,
    is_closed=is_closed,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_database()
    yield


app = FastAPI(
    title="CPGRAMS Educational Demo Portal",
    description="Unofficial, local-only educational replica. No real grievances are filed.",
    version="1.0.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def get_conn():
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()


def _secret() -> bytes:
    return os.environ.get("CPGRAMS_SESSION_SECRET", "cpgrams-demo-local-secret").encode("utf-8")


def _sign(payload: bytes) -> str:
    return hmac.new(_secret(), payload, hashlib.sha256).hexdigest()


def _encode_signed(data: dict[str, Any]) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    body = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return f"{body}.{_sign(raw)}"


def _decode_signed(value: str | None) -> dict[str, Any] | None:
    if not value or "." not in value:
        return None
    body, signature = value.rsplit(".", 1)
    try:
        padded = body + "=" * (-len(body) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception:
        return None
    if not hmac.compare_digest(_sign(raw), signature):
        return None
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    created = data.get("iat", 0)
    try:
        from datetime import datetime, timezone

        age = datetime.now(timezone.utc).timestamp() - float(created)
    except Exception:
        return None
    if age > 8 * 60 * 60:
        return None
    return data


def read_session(request: Request) -> dict[str, Any] | None:
    return _decode_signed(request.cookies.get(SESSION_COOKIE))


def set_session(response: Response, user: dict[str, Any]) -> None:
    payload = {
        "account_ref": user["account_ref"],
        "display_name": user["display_name"],
        "email": user.get("email") or "",
        "state": user.get("state") or "",
        "iat": __import__("time").time(),
    }
    response.set_cookie(
        SESSION_COOKIE,
        _encode_signed(payload),
        max_age=8 * 60 * 60,
        httponly=True,
        samesite="lax",
        path="/",
    )


def set_flash(response: Response, message: str, kind: str = "success") -> None:
    response.set_cookie(
        FLASH_COOKIE,
        _encode_signed({"message": message, "kind": kind}),
        max_age=120,
        httponly=True,
        samesite="lax",
        path="/",
    )


def pop_flash(request: Request) -> dict[str, str] | None:
    return _decode_signed(request.cookies.get(FLASH_COOKIE))


def redirect(url: str, status_code: int = 303) -> RedirectResponse:
    return RedirectResponse(url, status_code=status_code)


def safe_next(value: str | None, fallback: str = "/") -> str:
    if not value:
        return fallback
    if not value.startswith("/") or value.startswith("//"):
        return fallback
    return value


def add_security_headers(response: Response) -> Response:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        "font-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; "
        "base-uri 'self'; object-src 'none'"
    )
    return response


def render(request: Request, template: str, status_code: int = 200, **context: Any) -> HTMLResponse:
    lang = getattr(request.state, "lang", i18n.DEFAULT_LANGUAGE)
    session = read_session(request)
    flash = pop_flash(request)
    selected_language = i18n.language_info(lang)
    ctx = {
        "request": request,
        "session": session,
        "flash": flash,
        "lang": lang,
        "selected_language": selected_language,
        "languages": i18n.languages(),
        "fallback_active": i18n.fallback_active(lang),
        "t": lambda key: i18n.translate(key, lang),
        "path": request.url.path,
        "query": request.url.query,
        "current_year": db.utcnow().year,
        "disclaimer": DISCLAIMER,
        "official_url": OFFICIAL_URL,
    }
    ctx.update(context)
    html = env.get_template(template).render(**ctx)
    response = HTMLResponse(html, status_code=status_code)
    response.headers["Cache-Control"] = "no-store"
    if flash:
        response.delete_cookie(FLASH_COOKIE, path="/")
    return add_security_headers(response)


@app.middleware("http")
async def language_and_security(request: Request, call_next):
    requested = request.query_params.get("lang") or request.cookies.get(LANG_COOKIE)
    lang = i18n.normalise_language(requested)
    request.state.lang = lang
    response = await call_next(request)
    if request.query_params.get("lang") in i18n.language_codes():
        response.set_cookie(
            LANG_COOKIE, lang, max_age=365 * 24 * 60 * 60, samesite="lax", path="/"
        )
    if not response.headers.get("X-Content-Type-Options"):
        add_security_headers(response)
    return response


@app.get("/language/{code}")
def change_language(code: str, request: Request, next: str | None = None):
    code = i18n.normalise_language(code)
    response = redirect(safe_next(next, request.headers.get("referer") or "/"))
    response.set_cookie(LANG_COOKIE, code, max_age=365 * 24 * 60 * 60, samesite="lax", path="/")
    return response


@app.get("/", response_class=HTMLResponse)
def home(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    recent = repository.list_complaints(conn, limit=3)
    return render(request, "home.html", recent=recent, active="home")


@app.get("/health")
def health(conn: sqlite3.Connection = Depends(get_conn)):
    try:
        count = conn.execute("SELECT COUNT(*) AS c FROM demo_complaints").fetchone()["c"]
        database = "ok"
    except sqlite3.Error:
        count = 0
        database = "error"
    return {
        "status": "ok" if database == "ok" else "degraded",
        "app": "CPGRAMS educational demo",
        "version": "1.0.0",
        "database": database,
        "complaint_records": count,
        "real_government": False,
        "demo": True,
    }


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str | None = None):
    if read_session(request):
        return redirect(safe_next(next, "/"))
    return render(request, "login.html", next=safe_next(next, "/"), active="login")


@app.post("/login")
async def login_submit(request: Request, next: str | None = None):
    form = await request.form()
    target = safe_next(next or str(form.get("next") or ""), "/")
    response = redirect(target)
    set_session(
        response,
        {
            "account_ref": "DEMO-CITIZEN-001",
            "display_name": "Demo Citizen",
            "email": "demo.citizen@example.test",
            "state": "Tamil Nadu",
        },
    )
    set_flash(response, i18n.translate("flash.login", request.state.lang))
    return response


@app.post("/login/demo")
async def login_demo(request: Request, next: str | None = None):
    return await login_submit(request, next=next)


@app.post("/logout")
def logout(request: Request):
    response = redirect("/")
    response.delete_cookie(SESSION_COOKIE, path="/")
    set_flash(response, i18n.translate("flash.logout", request.state.lang), "info")
    return response


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    return render(request, "register.html", values={}, errors={}, active="register")


@app.post("/register", response_class=HTMLResponse)
async def register_submit(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    form = await request.form()
    values = {
        "display_name": str(form.get("display_name") or "").strip(),
        "email": str(form.get("email") or "").strip(),
        "state": str(form.get("state") or "").strip(),
    }
    errors: dict[str, str] = {}
    if len(values["display_name"]) < 2 or len(values["display_name"]) > 80:
        errors["display_name"] = "Enter a fictional display name of 2–80 characters."
    if "@" not in values["email"] or "." not in values["email"].split("@")[-1]:
        errors["email"] = "Enter a valid fictional email address. It is stored only in this demo."
    if values["state"] not in REGIONS:
        errors["state"] = "Choose a demo state or region."
    if errors:
        return render(
            request, "register.html", values=values, errors=errors, active="register", status_code=422
        )
    user = repository.create_demo_user(conn, values["display_name"], values["email"], values["state"])
    response = redirect("/")
    set_session(response, user)
    set_flash(response, i18n.translate("flash.registered", request.state.lang))
    return response


def _require_session(request: Request, next_path: str) -> RedirectResponse | None:
    if not read_session(request):
        return redirect(f"/login?next={quote(next_path)}")
    return None


@app.get("/grievance/new", response_class=HTMLResponse)
def grievance_form(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    auth_redirect = _require_session(request, "/grievance/new")
    if auth_redirect:
        return auth_redirect
    token = repository.create_form_token(conn, "grievance")
    session = read_session(request) or {}
    values = {
        "complainant_ref": session.get("account_ref", "DEMO-CITIZEN-001"),
        "subject": "",
        "category": "",
        "organisation": "",
        "region": session.get("state") or "",
        "description": "",
    }
    return render(
        request,
        "grievance_new.html",
        values=values,
        errors={},
        token=token,
        active="grievance",
    )


def _delete_attachment(stored: str | None) -> None:
    if not stored:
        return
    path = db.upload_dir() / Path(stored).name
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _save_attachment(upload: Any) -> tuple[str | None, str | None, str | None]:
    if upload is None or not getattr(upload, "filename", ""):
        return None, None, None
    original = Path(upload.filename).name[:120]
    suffix = Path(original).suffix.lower()
    if suffix not in ALLOWED_ATTACHMENTS:
        return None, None, "Attachment must be a PDF, TXT, PNG, JPG or JPEG file."
    try:
        data = upload.file.read(MAX_ATTACHMENT_BYTES + 1)
    except Exception:
        return None, None, "The attachment could not be read."
    if len(data) > MAX_ATTACHMENT_BYTES:
        return None, None, "Attachment must be 2 MB or smaller."
    if suffix == ".pdf" and not data.startswith(b"%PDF"):
        return None, None, "The file does not look like a valid PDF."
    if suffix == ".png" and not data.startswith(b"\x89PNG"):
        return None, None, "The file does not look like a valid PNG image."
    if suffix in {".jpg", ".jpeg"} and not data.startswith(b"\xff\xd8"):
        return None, None, "The file does not look like a valid JPEG image."
    stored = f"{uuid.uuid4().hex}{suffix}"
    destination = db.upload_dir() / stored
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return original, stored, None


@app.post("/grievance/new", response_class=HTMLResponse)
async def grievance_submit(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    auth_redirect = _require_session(request, "/grievance/new")
    if auth_redirect:
        return auth_redirect
    form = await request.form()
    data = {key: form.get(key) for key in ("complainant_ref", "subject", "category", "organisation", "region", "description", "declaration")}
    values = {key: str(data.get(key) or "") for key in ("complainant_ref", "subject", "category", "organisation", "region", "description")}
    token = str(form.get("form_token") or "")
    cleaned, errors = validate_complaint(data)

    attachment = form.get("attachment")
    attachment_name = attachment_stored = None
    if isinstance(attachment, UploadFile) and attachment.filename:
        attachment_name, attachment_stored, attachment_error = _save_attachment(attachment)
        if attachment_error:
            errors["attachment"] = attachment_error

    if not token:
        errors["form"] = "This form session is missing. Please reload the form."
    if errors:
        if attachment_stored:
            _delete_attachment(attachment_stored)
        return render(
            request,
            "grievance_new.html",
            values=values,
            errors=errors,
            token=token or repository.create_form_token(conn, "grievance"),
            active="grievance",
            status_code=422,
        )

    try:
        complaint, created = repository.create_complaint(
            conn, cleaned, token, attachment_name, attachment_stored
        )
    except repository.InvalidFormToken:
        if attachment_stored:
            _delete_attachment(attachment_stored)
        return render(
            request,
            "grievance_new.html",
            values=values,
            errors={"form": "This submission form has expired or was already used. Please review the new form and submit again."},
            token=repository.create_form_token(conn, "grievance"),
            active="grievance",
            status_code=409,
        )

    dashboard_adapter.sync_complaint(conn, complaint)
    complaint = repository.get_complaint(conn, complaint["registration_number"]) or complaint
    target = (
        f"/grievance/success?{urlencode({'ref': complaint['registration_number'], 'verification': complaint['complainant_ref']})}"
    )
    response = redirect(target)
    if not created:
        set_flash(response, i18n.translate("flash.complaint_saved", request.state.lang), "info")
    return response


@app.get("/grievance/success", response_class=HTMLResponse)
def grievance_success(
    request: Request,
    ref: str = "",
    verification: str = "",
    conn: sqlite3.Connection = Depends(get_conn),
):
    complaint = repository.get_verified_complaint(conn, ref, verification)
    if not complaint:
        return render(
            request,
            "status_not_found.html",
            reference=ref,
            active="grievance",
            status_code=404,
        )
    events = repository.get_events(conn, complaint["id"])
    return render(
        request,
        "grievance_success.html",
        complaint=complaint,
        events=events,
        active="grievance",
    )


@app.get("/grievance/pension", response_class=HTMLResponse)
def pension_page(request: Request):
    return render(request, "pension.html", active="grievance")


@app.get("/grievance/process", response_class=HTMLResponse)
def process_page(request: Request):
    return render(request, "process.html", active="process")


@app.get("/status", response_class=HTMLResponse)
def status_page(request: Request, ref: str = "", verification: str = ""):
    return render(
        request,
        "status.html",
        values={"registration": ref, "verification": verification},
        errors={},
        active="status",
    )


@app.post("/status", response_class=HTMLResponse)
async def status_submit(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    form = await request.form()
    reference = str(form.get("registration") or "").strip().upper()
    verification = str(form.get("verification") or "").strip().upper()
    errors: dict[str, str] = {}
    if not reference:
        errors["registration"] = "Enter the demo registration number."
    if not verification:
        errors["verification"] = "Enter the demo verification code."
    if errors:
        return render(
            request,
            "status.html",
            values={"registration": reference, "verification": verification},
            errors=errors,
            active="status",
            status_code=422,
        )
    complaint = repository.get_verified_complaint(conn, reference, verification)
    if not complaint:
        errors["form"] = (
            "No demo grievance matched those details. Check the reference and verification code, "
            "or try the seeded example shown below."
        )
        return render(
            request,
            "status.html",
            values={"registration": reference, "verification": verification},
            errors=errors,
            active="status",
        )
    return redirect(
        f"/status/view?{urlencode({'ref': complaint['registration_number'], 'verification': complaint['complainant_ref']})}"
    )


@app.get("/status/view", response_class=HTMLResponse)
def status_view(
    request: Request,
    ref: str = "",
    verification: str = "",
    conn: sqlite3.Connection = Depends(get_conn),
):
    complaint = repository.get_complaint_full(conn, ref, verification)
    if not complaint:
        return render(
            request,
            "status_not_found.html",
            reference=ref,
            active="status",
            status_code=404,
        )
    return render(
        request,
        "status_result.html",
        complaint=complaint,
        events=complaint["events"],
        feedback=complaint["feedback"],
        active="status",
    )


@app.get("/reminder", response_class=HTMLResponse)
def reminder_page(
    request: Request,
    ref: str = "",
    verification: str = "",
    conn: sqlite3.Connection = Depends(get_conn),
):
    values = {"reference": ref, "verification": verification, "message": ""}
    complaint = None
    if ref and verification:
        complaint = repository.get_verified_complaint(conn, ref, verification)
    return render(
        request,
        "reminder.html",
        values=values,
        errors={},
        complaint=complaint,
        active="reminder",
    )


@app.post("/reminder", response_class=HTMLResponse)
async def reminder_submit(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    form = await request.form()
    data = {
        "reference": form.get("reference"),
        "verification": form.get("verification"),
        "message": form.get("message"),
    }
    cleaned, errors = validate_reminder(data)
    next_url = safe_next(str(form.get("next") or ""), "")
    complaint = None
    if not errors:
        complaint = repository.get_verified_complaint(conn, cleaned["reference"], cleaned["verification"])
        if not complaint:
            errors["form"] = (
                "No demo grievance matched those details. Nothing was recorded. "
                "Check the reference and verification code."
            )
    if errors:
        values = {
            "reference": cleaned["reference"],
            "verification": cleaned["verification"],
            "message": cleaned["message"],
        }
        return render(
            request,
            "reminder.html",
            values=values,
            errors=errors,
            complaint=complaint,
            active="reminder",
            status_code=422,
        )
    new_status = repository.add_reminder(conn, complaint, cleaned["message"])
    response = redirect(
        next_url
        or f"/status/view?{urlencode({'ref': complaint['registration_number'], 'verification': complaint['complainant_ref']})}"
    )
    set_flash(response, i18n.translate("flash.reminder_saved", request.state.lang))
    return response


@app.get("/feedback", response_class=HTMLResponse)
def feedback_page(
    request: Request,
    ref: str = "",
    verification: str = "",
    conn: sqlite3.Connection = Depends(get_conn),
):
    complaint = None
    errors: dict[str, str] = {}
    if ref and verification:
        complaint = repository.get_complaint_full(conn, ref, verification)
        if not complaint:
            errors["form"] = "No demo grievance matched those details. Check the reference and verification code."
        elif not is_closed(complaint["status"]):
            errors["form"] = "Only a closed demo grievance can be rated. This record is still open."
    return render(
        request,
        "feedback.html",
        values={"reference": ref, "verification": verification, "rating": "", "feedback_text": ""},
        errors=errors,
        complaint=complaint,
        active="feedback",
    )


@app.post("/feedback", response_class=HTMLResponse)
async def feedback_submit(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    form = await request.form()
    data = {
        "reference": form.get("reference"),
        "verification": form.get("verification"),
        "rating": form.get("rating"),
        "feedback_text": form.get("feedback_text"),
    }
    cleaned, errors = validate_feedback(data)
    complaint = None
    if not errors:
        complaint = repository.get_complaint_full(conn, cleaned["reference"], cleaned["verification"])
        if not complaint:
            errors["form"] = "No demo grievance matched those details. Nothing was saved."
        elif not is_closed(complaint["status"]):
            errors["form"] = "Only a closed demo grievance can be rated. Nothing was saved."
    if errors:
        values = {
            "reference": cleaned["reference"],
            "verification": cleaned["verification"],
            "rating": str(cleaned["rating"] or ""),
            "feedback_text": cleaned["feedback_text"],
        }
        return render(
            request,
            "feedback.html",
            values=values,
            errors=errors,
            complaint=complaint,
            active="feedback",
            status_code=422,
        )
    repository.save_feedback(conn, complaint, cleaned["rating"], cleaned["feedback_text"])
    response = redirect(
        f"/status/view?{urlencode({'ref': complaint['registration_number'], 'verification': complaint['complainant_ref']})}"
    )
    set_flash(response, i18n.translate("flash.feedback_saved", request.state.lang))
    return response


@app.get("/about", response_class=HTMLResponse)
def about_page(request: Request):
    return render(request, "about.html", active="about")


@app.get("/contact", response_class=HTMLResponse)
def contact_page(request: Request):
    return render(request, "contact.html", values={}, errors={}, active="contact")


@app.post("/contact", response_class=HTMLResponse)
async def contact_submit(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    form = await request.form()
    values = {
        "name": str(form.get("name") or "").strip(),
        "email": str(form.get("email") or "").strip(),
        "subject": str(form.get("subject") or "").strip(),
        "message": str(form.get("message") or "").strip(),
    }
    cleaned, errors = validate_contact(values)
    if errors:
        return render(request, "contact.html", values=values, errors=errors, active="contact", status_code=422)
    repository.save_contact_message(conn, cleaned)
    response = redirect("/contact")
    set_flash(response, i18n.translate("flash.contact_saved", request.state.lang))
    return response


@app.get("/faq", response_class=HTMLResponse)
def faq_page(request: Request):
    return render(request, "faq.html", active="faq")


@app.get("/sitemap", response_class=HTMLResponse)
def sitemap_page(request: Request):
    return render(request, "sitemap.html", active="sitemap")


@app.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request):
    return render(request, "privacy.html", active="privacy")


@app.get("/disclaimer", response_class=HTMLResponse)
def disclaimer_page(request: Request):
    return render(request, "privacy.html", active="privacy")


@app.get("/api/complaints")
def api_complaints(conn: sqlite3.Connection = Depends(get_conn)):
    records = [repository.complaint_export_row(c) for c in repository.list_complaints(conn)]
    return JSONResponse(
        {
            "demo": True,
            "source": "CPGRAMS Simulator",
            "disclaimer": DISCLAIMER,
            "count": len(records),
            "items": records,
        },
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/complaints/{reference}")
def api_complaint(reference: str, verification: str = "", conn: sqlite3.Connection = Depends(get_conn)):
    if not verification:
        raise HTTPException(status_code=400, detail="A demo verification code is required.")
    complaint = repository.get_complaint_full(conn, reference, verification)
    if not complaint:
        raise HTTPException(status_code=404, detail="Demo grievance not found.")
    payload = repository.complaint_export_row(complaint)
    payload["events"] = complaint["events"]
    payload["feedback"] = complaint["feedback"]
    return JSONResponse(
        {"demo": True, "source": "CPGRAMS Simulator", "item": payload},
        headers={"Cache-Control": "no-store"},
    )


@app.get("/export/complaints.json")
def export_json(conn: sqlite3.Connection = Depends(get_conn)):
    records = [repository.complaint_export_row(c) for c in repository.list_complaints(conn)]
    content = json.dumps(
        {"demo": True, "source": "CPGRAMS Simulator", "disclaimer": DISCLAIMER, "items": records},
        indent=2,
        ensure_ascii=False,
    )
    return Response(
        content,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="cpgrams-demo-complaints.json"'},
    )


@app.get("/export/complaints.csv")
def export_csv(conn: sqlite3.Connection = Depends(get_conn)):
    rows = [repository.complaint_export_row(c) for c in repository.list_complaints(conn)]
    buffer = io.StringIO()
    fieldnames = [
        "registration_number",
        "subject",
        "category",
        "organisation",
        "region",
        "description",
        "status",
        "created_at",
        "updated_at",
        "is_seeded",
        "source",
        "is_synthetic",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="cpgrams-demo-complaints.csv"'},
    )


@app.get("/demo/reset")
def demo_reset_disabled():
    return JSONResponse(
        status_code=404,
        content={
            "detail": "The reset action is disabled. Run `python -m app.seed --reset` locally "
            "or set CPGRAMS_ALLOW_RESET=1 to enable POST /demo/reset."
        },
    )


@app.post("/demo/reset")
async def demo_reset(request: Request):
    if os.environ.get("CPGRAMS_ALLOW_RESET") != "1":
        raise HTTPException(status_code=404, detail="Reset is disabled.")
    try:
        payload = await request.json()
    except Exception:
        payload = None
    if not isinstance(payload, dict) or payload.get("confirm") != "RESET-DEMO-DATA":
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Send JSON with {\"confirm\": \"RESET-DEMO-DATA\"} to this endpoint, "
                "or run `python -m app.seed --reset`."
            },
        )
    seeded = db.reset_database(seed=True)
    return JSONResponse(
        {
            "status": "reset",
            "seeded": seeded,
            "detail": "Demo data was reset locally. No records were sent anywhere.",
        }
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return render(
        request,
        "not_found.html",
        status_code=404,
        active="",
        requested_path=request.url.path,
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc: Exception):
    return render(
        request,
        "error.html",
        status_code=500,
        active="",
    )
