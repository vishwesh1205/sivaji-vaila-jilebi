import random
import threading
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Query
from pydantic import BaseModel

app = FastAPI(title="Mock CSS (SIMULATOR - synthetic data)")
INTERVAL = 20
_lock = threading.RLock()
_counter = 0
tickets: list[dict[str, Any]] = []

INSTITUTIONS = [
    ("St Xaviers Inst of Tech", "Mumbai", "Maharashtra"),
    ("Natl Coll of Engg", "Bengaluru", "Karnataka"),
    ("Shri Saraswati Inst of Engg & Tech", "Pune", "Maharashtra"),
    ("Govt Coll Engg", "Chennai", "Tamil Nadu"),
    ("Modern Inst of Mgmt and Tech", "Hyderabad", "Telangana"),
    ("Global Coll of Tech", "Jaipur", "Rajasthan"),
]

AMOUNTS = ["18,500", "27,000", "32,500", "45,000", "52,000", "68,000"]
APPROVED = ["15,000", "21,000", "28,000", "36,000", "42,000"]
PROGRAMMES = ["B.Tech Computer Science", "B.Tech Mechanical", "B.Tech Civil", "M.Tech VLSI", "MBA"]
SEMESTERS = ["third", "fourth", "fifth", "sixth"]
MONTHS = ["June", "July", "August", "September"]
BRANCHES = ["computer science", "mechanical", "civil", "electronics and communication"]
DEPARTMENTS = ["Computer Science and Engineering", "Mechanical Engineering", "Civil Engineering"]

TEMPLATES = {
    "FEE": [
        "The institute collected Rs {charged} for the {semester} semester of the {programme} programme against an approved fee of Rs {approved}. No itemised receipt was issued and the excess amount has not been refunded despite a written request.",
        "A mandatory charge of Rs {charged} was added to the {semester} semester fee for {programme}, which is not part of the approved fee structure. The accounts office says it is a 'development fee' but has not provided any circular.",
        "The college is demanding Rs {charged} for examination and laboratory charges in the {programme} course, whereas the fee committee approved only Rs {approved}. Students who have not paid are being denied hall tickets.",
        "Fee receipts for the {semester} semester show Rs {charged} although the approved amount for {programme} is Rs {approved}. The difference was collected in cash and no refund has been processed after {months}.",
    ],
    "FACULTY": [
        "The {department} department has only two regular faculty members for five sections. Classes for {programme} have been combined and practical sessions are being taken by temporary staff without approval.",
        "Faculty vacancies in the {department} department have remained unfilled since {months}. Students in the {semester} semester have lost more than 30 scheduled lectures in {branch}.",
        "A visiting lecturer is handling core {branch} subjects in the {department} department without the required qualifications. Attendance records and lesson plans are not being maintained.",
    ],
    "INFRASTRUCTURE": [
        "The {branch} laboratory has non-functional equipment and only one computer for four students. Practical work for the {semester} semester of {programme} is being demonstrated instead of performed.",
        "Hostel rooms in the {department} block have unsafe wiring, no fire extinguishers and irregular water supply. The warden has not responded to written complaints from residents.",
        "The library has no current journals for {branch}, and the reading room roof leaks during rain. Students preparing for the {semester} semester examination are forced to study in corridors.",
    ],
    "APPROVAL_VIOLATION": [
        "The institute admitted additional students to the {programme} programme beyond the sanctioned intake for {branch}. The admission brochure does not mention AICTE approval for the extra seats.",
        "Classes for an unapproved {branch} section of {programme} are being held in a temporary room. The institute has not disclosed the revised intake or approval status to applicants.",
        "The college is running {programme} in a new building without the required AICTE extension of approval. Laboratories for the {semester} semester are not listed in the approved infrastructure plan.",
    ],
    "RAGGING_DISCRIMINATION": [
        "Senior students in the {department} hostel are forcing first-year students to clean rooms and run errands late at night. An anti-ragging complaint was submitted but no committee inquiry has started.",
        "A student from a reserved category in the {programme} programme was repeatedly assigned menial work by a faculty member and warned not to complain. The internal committee has not recorded the grievance.",
        "A group of final-year students is excluding first-year girls from the {branch} laboratory and making inappropriate remarks. The college has not displayed the anti-ragging helpline in the hostel.",
    ],
    "OTHER": [
        "The institute is withholding the {semester} semester marksheet of a {programme} student despite completion of all requirements. Repeated visits to the examination cell have not produced a written response.",
        "Transfer certificates are being delayed for students who have completed the {programme} programme. The office demands an unspecified clearance fee before releasing documents.",
        "The college bus service for {branch} students was stopped without notice in {months}. No alternative transport or fee adjustment has been offered to affected students.",
    ],
}

MULTILINGUAL = {
    "hi": [
        "संस्थान ने {programme} कार्यक्रम के लिए स्वीकृत शुल्क से अधिक राशि ली है। अतिरिक्त शुल्क की रसीद नहीं दी गई और छात्र द्वारा किए गए लिखित अनुरोध के बाद भी धनवापसी नहीं हुई।",
        "{department} विभाग में नियमित शिक्षकों के कई पद खाली हैं। इस सेमेस्टर के विद्यार्थियों की कक्षाएँ लगातार निरस्त हो रही हैं और प्रयोगशाला सत्र नहीं हो रहे हैं।",
    ],
    "ta": [
        "{programme} பாடத்திட்டத்திற்கு அங்கீகரிக்கப்பட்ட கட்டணத்தை விட அதிகமாக வசூலிக்கப்படுகிறது. கூடுதல் தொகைக்கு ரசீது வழங்கப்படவில்லை; திருப்பிச் செலுத்தும் கோரிக்கைக்கு பதிலில்லை.",
        "{department} துறையில் ஆசிரியர் பற்றாக்குறை காரணமாக இந்த பருவ மாணவர்களின் வகுப்புகள் தொடர்ந்து ரத்து செய்யப்படுகின்றன. ஆய்வக பயிற்சிகளும் நடைபெறவில்லை.",
    ],
}


def _narrative(category: str, programme: str, semester: str, department: str, branch: str) -> tuple[str, str]:
    if random.random() < 0.08:
        language = random.choice(["hi", "ta"])
        template = random.choice(MULTILINGUAL[language])
        return template.format(programme=programme, department=department), language
    template = random.choice(TEMPLATES[category])
    text = template.format(
        charged=random.choice(AMOUNTS),
        approved=random.choice(APPROVED),
        programme=programme,
        semester=semester,
        months=random.choice(MONTHS),
        department=department,
        branch=branch,
    )
    return text, "en"


def make_ticket(institution: str | None = None) -> dict[str, Any]:
    global _counter
    with _lock:
        _counter += 1
        n = _counter
    name, city, state = random.choice(INSTITUTIONS)
    category = random.choice(list(TEMPLATES))
    institution_name = institution or f"{name}, {city}"
    programme = random.choice(PROGRAMMES)
    semester = random.choice(SEMESTERS)
    department = random.choice(DEPARTMENTS)
    branch = random.choice(BRANCHES)
    narrative, language = _narrative(category, programme, semester, department, branch)
    return {
        "ticket_no": f"CSS-{88000 + n}",
        "institution_name": institution_name,
        "grievance": narrative,
        "grievance_category": category,
        "received_date": datetime.utcnow().strftime("%d/%m/%Y"),
        "current_status": "Pending",
        "bureau_code": "RB",
        "language": language,
        "complainant_ref": f"demo-css-{random.randint(1, 300)}",
        "state": state,
        "district": city,
        "simulator": True,
    }


def seed():
    with _lock:
        tickets.append(make_ticket("St. Xavier Institute of Technology, Mumbai"))
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
        "institution_name": "St Xaviers Inst of Tech, Mumbai",
        "grievance": "Unauthorised intake beyond sanctioned seats in engineering branches; approval conditions appear to be violated.",
        "grievance_category": "APPROVAL_VIOLATION",
        "received_date": now.strftime("%d/%m/%Y"),
        "current_status": "Pending",
        "bureau_code": "RB",
        "language": "en",
        "complainant_ref": f"scenario-css-{random.randint(1,999)}",
        "state": "Maharashtra",
        "district": "Mumbai",
        "simulator": True,
    }
    with _lock:
        tickets.append(a)
    return {"simulator": True, "ticket": a}
