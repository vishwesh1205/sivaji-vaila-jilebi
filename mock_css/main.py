import random
import threading
from datetime import datetime, timedelta
from typing import Any

from fastapi import FastAPI, Query
from pydantic import BaseModel

app = FastAPI(title="Mock CSS (SIMULATOR - synthetic data)")
INTERVAL = 20
_lock = threading.RLock()
_counter = 0
tickets: list[dict[str, Any]] = []

NOISY = [
    "St Xaviers Inst of Tech",
    "Natl Coll of Engg",
    "Shri Saraswati Inst of Engg & Tech",
    "Govt Coll Engg",
    "Modern Inst of Mgmt and Tech",
    "Global Coll of Tech",
]
NARRATIVES = [
    "Excessive fee charged beyond the approved fee structure for the current academic year.",
    "Faculty shortage in core engineering departments is affecting classes.",
    "Laboratory and hostel infrastructure is inadequate for students.",
    "Unauthorized intake beyond approved seats was observed during admission.",
    "शुल्क निर्धारित संरचना से अधिक लिया जा रहा है।",
    "கல்லூரியில் ஆசிரியர் பற்றாக்குறை காரணமாக வகுப்புகள் நடைபெறவில்லை.",
]
CATEGORIES = ["FEE", "FACULTY", "INFRASTRUCTURE", "APPROVAL_VIOLATION", "RAGGING_DISCRIMINATION", "OTHER"]


def make_ticket(institution: str | None = None) -> dict[str, Any]:
    global _counter
    with _lock:
        _counter += 1
        n = _counter
    now = datetime.utcnow()
    return {
        "ticket_no": f"CSS-{88000 + n}",
        "institution_name": institution or random.choice(NOISY),
        "grievance": random.choice(NARRATIVES),
        "grievance_category": random.choice(CATEGORIES),
        "received_date": now.strftime("%d/%m/%Y"),
        "current_status": "Pending",
        "bureau_code": "RB",
        "language": "hi" if "शुल्क" in NARRATIVES[4] else "en",
        "complainant_ref": f"demo-css-{random.randint(1, 300)}",
        "state": "Maharashtra",
        "simulator": True,
    }


def seed():
    with _lock:
        tickets.append(make_ticket("St. Xavier Institute of Technology"))
        tickets.append(make_ticket())


def generate_loop():
    while True:
        threading.Event().wait(INTERVAL)
        with _lock:
            tickets.append(make_ticket())


class InjectBody(BaseModel):
    institution_name: str | None = None
    grievance: str | None = None
    category: str | None = None


@app.on_event("startup")
def startup():
    seed()
    threading.Thread(target=generate_loop, daemon=True).start()


@app.get("/health")
def health():
    return {"status": "ok", "service": "mock-css", "simulator": True}


@app.get("/tickets")
def list_tickets(since: str | None = Query(default=None)):
    with _lock:
        return {"simulator": True, "source_type": "SIMULATOR", "banner": "SIMULATOR – synthetic data", "tickets": list(tickets)}


@app.post("/admin/inject")
def inject(body: InjectBody):
    t = make_ticket(body.institution_name)
    if body.grievance:
        t["grievance"] = body.grievance
    if body.category:
        t["grievance_category"] = body.category
    with _lock:
        tickets.append(t)
    return {"simulator": True, "ticket": t}


@app.post("/admin/scenario")
def scenario():
    now = datetime.utcnow()
    a = {
        "ticket_no": f"CSS-HERO-{random.randint(1000,9999)}",
        "institution_name": "St Xaviers Inst of Tech",
        "grievance": "Unauthorised intake beyond sanctioned seats in engineering branches; approval conditions appear to be violated.",
        "grievance_category": "APPROVAL_VIOLATION",
        "received_date": now.strftime("%d/%m/%Y"),
        "current_status": "Pending",
        "bureau_code": "RB",
        "language": "en",
        "complainant_ref": f"scenario-css-{random.randint(1,999)}",
        "simulator": True,
    }
    with _lock:
        tickets.append(a)
    return {"simulator": True, "ticket": a}
