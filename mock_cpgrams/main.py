import random
import threading
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Query
from pydantic import BaseModel

app = FastAPI(title="Mock CPGRAMS (SIMULATOR - synthetic data)")
INTERVAL = 20
_lock = threading.RLock()
_counter = 0
tickets: list[dict[str, Any]] = []

NOISY = [
    "St. Xaviers Institute of Technology",
    "National Coll of Engineering",
    "Shri Saraswati Institute of Engineering & Technology",
    "Government College of Engineering",
    "Modern Institute of Management & Technology",
    "Global College of Technology",
]
NARRATIVES = [
    "Complaint regarding excessive fee collection beyond the approved structure for 2025-26.",
    "Persistent faculty shortage in the department of computer science and engineering.",
    "Inadequate laboratory facilities and hostel infrastructure requiring urgent inspection.",
    "Admissions made beyond the approved intake without AICTE approval.",
    "शुल्क निर्धारित संरचना से अधिक लिया जा रहा है और रसीदें नहीं दी जा रही हैं।",
    "கல்லூரியில் ஆசிரியர் பற்றாக்குறை காரணமாக வகுப்புகள் தொடர்ந்து நடைபெறவில்லை.",
]
CATEGORIES = ["Fees", "Faculty", "Infrastructure", "Approval Violation", "Ragging/Discrimination", "Other"]


def make_ticket(institution: str | None = None) -> dict[str, Any]:
    global _counter
    with _lock:
        _counter += 1
        n = _counter
    now = datetime.utcnow()
    return {
        "registration_number": f"CPGRAMS/2026/{400000 + n}",
        "institution_name": institution or random.choice(NOISY),
        "ministry": "Ministry of Education",
        "department": "Public Grievance Redressal Cell",
        "grievance_text": random.choice(NARRATIVES),
        "category": random.choice(CATEGORIES),
        "registration_date": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "current_status": "Received",
        "language": "hi" if "शुल्क" in NARRATIVES[4] else "en",
        "applicant_ref": f"demo-cpgrams-{random.randint(1, 300)}",
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
    grievance_text: str | None = None
    category: str | None = None


@app.on_event("startup")
def startup():
    seed()
    threading.Thread(target=generate_loop, daemon=True).start()


@app.get("/health")
def health():
    return {"status": "ok", "service": "mock-cpgrams", "simulator": True}


@app.get("/tickets")
def list_tickets(since: str | None = Query(default=None)):
    with _lock:
        return {"simulator": True, "source_type": "SIMULATOR", "banner": "SIMULATOR – synthetic data", "tickets": list(tickets)}


@app.post("/admin/inject")
def inject(body: InjectBody):
    t = make_ticket(body.institution_name)
    if body.grievance_text:
        t["grievance_text"] = body.grievance_text
    if body.category:
        t["category"] = body.category
    with _lock:
        tickets.append(t)
    return {"simulator": True, "ticket": t}


@app.post("/admin/scenario")
def scenario():
    now = datetime.utcnow()
    a = {
        "registration_number": f"CPGRAMS/HERO/{random.randint(1000,9999)}",
        "institution_name": "St. Xaviers Institute of Technology",
        "ministry": "Ministry of Education",
        "department": "Public Grievance Redressal Cell",
        "grievance_text": "Student alleges that the institute collected fees in excess of the approved fee structure and did not issue proper receipts.",
        "category": "Fees",
        "registration_date": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "current_status": "Received",
        "language": "en",
        "applicant_ref": f"scenario-pgrcs-{random.randint(1,999)}",
        "simulator": True,
    }
    with _lock:
        tickets.append(a)
    return {"simulator": True, "ticket": a}
