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

INSTITUTIONS = [
    ("St. Xaviers Institute of Technology", "Mumbai", "Maharashtra"),
    ("National Coll of Engineering", "Bengaluru", "Karnataka"),
    ("Shri Saraswati Institute of Engineering & Technology", "Pune", "Maharashtra"),
    ("Government College of Engineering", "Chennai", "Tamil Nadu"),
    ("Modern Institute of Management & Technology", "Hyderabad", "Telangana"),
    ("Global College of Technology", "Jaipur", "Rajasthan"),
]

AMOUNTS = ["22,500", "31,000", "38,000", "49,500", "57,000", "72,000"]
APPROVED = ["18,000", "24,000", "30,000", "39,000", "46,000"]
PROGRAMMES = ["B.Tech Computer Science", "B.Tech Mechanical", "B.Tech Civil", "M.Tech VLSI", "MBA"]
SEMESTERS = ["third", "fourth", "fifth", "sixth"]
MONTHS = ["June", "July", "August", "September"]
BRANCHES = ["computer science", "mechanical", "civil", "electronics and communication"]
DEPARTMENTS = ["Computer Science and Engineering", "Mechanical Engineering", "Civil Engineering"]

CATEGORY_LABELS = {
    "FEE": "Fees",
    "FACULTY": "Faculty",
    "INFRASTRUCTURE": "Infrastructure",
    "APPROVAL_VIOLATION": "Approval Violation",
    "RAGGING_DISCRIMINATION": "Ragging/Discrimination",
    "OTHER": "Other",
}

TEMPLATES = {
    "FEE": [
        "The institute collected Rs {charged} for the {semester} semester of the {programme} programme although the approved fee is Rs {approved}. The student has not received an itemised receipt and the excess amount remains unrefunded.",
        "A compulsory 'development charge' of Rs {charged} was added to the {programme} fee for the {semester} semester without any approved circular. Students requesting a refund are being asked to withdraw the complaint.",
        "Examination and laboratory fees of Rs {charged} are being demanded for {programme}, while the fee committee approved only Rs {approved}. Hall tickets are withheld from students who have not paid the disputed amount.",
    ],
    "FACULTY": [
        "The {department} department has only two regular faculty members for five sections. Classes for the {semester} semester of {programme} are being merged and practicals are handled by temporary staff.",
        "Several sanctioned teaching posts in the {department} department remain vacant. Students in {branch} have lost more than 30 scheduled lectures since {months}.",
        "A visiting lecturer without the required qualification is teaching core {branch} subjects in the {department} department. Attendance records and lesson plans are not maintained.",
    ],
    "INFRASTRUCTURE": [
        "The {branch} laboratory has non-functional equipment and only one computer for four students. Practical work for the {semester} semester is being demonstrated rather than performed.",
        "Hostel rooms in the {department} block have unsafe wiring, no fire extinguishers and irregular water supply. The warden has not responded to written complaints from residents.",
        "The library has no current journals for {branch}, and the reading room roof leaks during rain. Students preparing for the {semester} semester examination are forced to study in corridors.",
    ],
    "APPROVAL_VIOLATION": [
        "The institute admitted students to the {programme} programme beyond the sanctioned intake for {branch}. The admission brochure does not disclose AICTE approval for the additional seats.",
        "An unapproved {branch} section of {programme} is being run in a temporary room. The institute has not disclosed the revised intake or approval status to applicants.",
        "The college is running {programme} in a new building without the required extension of approval. Laboratories for the {semester} semester are absent from the approved infrastructure plan.",
    ],
    "RAGGING_DISCRIMINATION": [
        "Senior students in the {department} hostel are forcing first-year students to clean rooms and run errands late at night. An anti-ragging complaint was submitted but no committee inquiry has started.",
        "A student from a reserved category in the {programme} programme was repeatedly assigned menial work by a faculty member and warned not to complain. The internal committee has not recorded the grievance.",
        "A group of final-year students is excluding first-year girls from the {branch} laboratory and making inappropriate remarks. The anti-ragging helpline is not displayed in the hostel.",
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
        "registration_number": f"CPGRAMS/2026/{400000 + n}",
        "institution_name": institution_name,
        "ministry": "Ministry of Education",
        "department": "Public Grievance Redressal Cell",
        "grievance_text": narrative,
        "category": CATEGORY_LABELS[category],
        "registration_date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        "current_status": "Received",
        "language": language,
        "applicant_ref": f"demo-cpgrams-{random.randint(1, 300)}",
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
        "institution_name": "St. Xaviers Institute of Technology, Mumbai",
        "ministry": "Ministry of Education",
        "department": "Public Grievance Redressal Cell",
        "grievance_text": "Student alleges that the institute collected fees in excess of the approved fee structure and did not issue proper receipts.",
        "category": "Fees",
        "registration_date": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "current_status": "Received",
        "language": "en",
        "applicant_ref": f"scenario-pgrcs-{random.randint(1,999)}",
        "state": "Maharashtra",
        "district": "Mumbai",
        "simulator": True,
    }
    with _lock:
        tickets.append(a)
    return {"simulator": True, "ticket": a}
