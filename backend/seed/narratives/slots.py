from __future__ import annotations

import random
from datetime import datetime, timedelta

PROGRAMMES = [
    "B.Tech Computer Science and Engineering",
    "B.Tech Electronics and Communication Engineering",
    "B.Tech Mechanical Engineering",
    "B.Tech Civil Engineering",
    "B.Tech Information Technology",
    "Diploma in Mechanical Engineering",
    "Diploma in Civil Engineering",
    "MBA",
    "MCA",
    "PGDM",
    "B.Pharm",
    "M.Pharm",
    "B.Arch",
]

DEPARTMENTS = [
    "Computer Science and Engineering",
    "Electronics and Communication Engineering",
    "Mechanical Engineering",
    "Civil Engineering",
    "Information Technology",
    "Management Studies",
    "Applied Sciences",
    "Pharmacy",
]

SEMESTERS = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth"]

LABS = ["Computer", "Electronics", "Mechanical", "Civil", "Chemistry", "Physics", "Pharmacy"]

BUILDINGS = ["A", "B", "C", "D", "Main Academic", "Science", "Engineering"]

LOCALITIES = {
    "Chennai": ["Anna Nagar", "Porur", "Tambaram", "Guindy", "Chromepet"],
    "Bhopal": ["Arera Colony", "Kolar Road", "Bairagarh", "MP Nagar", "Ayodhya Bypass"],
    "Kolkata": ["Salt Lake", "Behala", "Dum Dum", "Garia", "Barasat"],
    "Chandigarh": ["Sector 22", "Sector 34", "Mohali Phase 5", "Panchkula", "Zirakpur"],
    "Kanpur": ["Kalyanpur", "Govind Nagar", "Swaroop Nagar", "Kidwai Nagar", "Panki"],
    "Pune": ["Kothrud", "Hadapsar", "Wakad", "Baner", "Pimpri"],
    "Hyderabad": ["Kukatpally", "Gachibowli", "Secunderabad", "Dilsukhnagar", "Miyapur"],
    "Guwahati": ["Beltola", "Six Mile", "Zoo Road", "Maligaon", "Jalukbari"],
    "Jaipur": ["Malviya Nagar", "Vaishali Nagar", "Jagatpura", "Mansarovar", "Sitapura"],
    "Bengaluru": ["Whitefield", "Jayanagar", "Yelahanka", "Electronic City", "Rajajinagar"],
}

# All names are fictional. Initials-plus-surname style avoids accidental
# resemblance to serving officials.
FICTIONAL_PEOPLE = [
    "Dr. R. K. Menon",
    "Mr. S. Iyer",
    "Ms. A. Banerjee",
    "Dr. P. V. Deshpande",
    "Mr. M. J. Qureshi",
    "Ms. N. Krishnan",
    "Dr. T. Chatterjee",
    "Mr. V. S. Rathore",
    "Mrs. L. D. Fernandes",
    "Dr. K. Subramaniam",
    "Mr. H. P. Yadav",
    "Ms. R. Bhattacharya",
    "Dr. G. N. Rao",
    "Mr. C. P. Shetty",
    "Ms. F. A. Khan",
    "Dr. B. K. Mishra",
    "Mr. D. R. Patil",
    "Ms. J. M. Thomas",
    "Dr. A. S. Kulkarni",
    "Mr. P. K. Nair",
]

FICTIONAL_STAFF = [
    "Dr. R. K. Menon",
    "Ms. A. Banerjee",
    "Mr. S. Iyer",
    "Dr. P. V. Deshpande",
    "Ms. N. Krishnan",
    "Mr. M. J. Qureshi",
    "Dr. T. Chatterjee",
    "Mrs. L. D. Fernandes",
]

PLACEMENT_PCTS = ["92", "95", "100", "98", "90"]

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def indian_amount(value: int) -> str:
    """Format an integer as Indian digit grouping, without a currency symbol."""
    s = str(int(value))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


class Slots:
    def __init__(self, rng: random.Random, *, year: int | None = None):
        self.rng = rng
        self.year = year or datetime.utcnow().year

    def amount(self, lo: int = 4000, hi: int = 180000) -> str:
        raw = self.rng.randint(lo // 100, hi // 100) * 100
        return indian_amount(raw)

    def amount_value(self, lo: int = 4000, hi: int = 180000) -> int:
        return self.rng.randint(lo // 100, hi // 100) * 100

    def academic_year(self) -> str:
        start = self.rng.randint(self.year - 2, self.year)
        return f"{start}-{str(start + 1)[-2:]}"

    def join_year(self) -> str:
        return str(self.rng.randint(self.year - 14, self.year - 2))

    def pass_year(self) -> str:
        return str(self.rng.randint(self.year - 8, self.year))

    def date(self) -> str:
        dt = datetime.utcnow() - timedelta(days=self.rng.randint(2, 420))
        style = self.rng.choice(["dmy", "dmy", "dmy_text", "iso", "month"])
        if style == "iso":
            return dt.strftime("%Y-%m-%d")
        if style == "month":
            return f"{self.rng.choice(['last', 'early', 'mid'])} {MONTH_NAMES[dt.month - 1]}"
        if style == "dmy_text":
            return f"{dt.day}{'st' if dt.day % 10 == 1 and dt.day != 11 else 'nd' if dt.day % 10 == 2 and dt.day != 12 else 'rd' if dt.day % 10 == 3 and dt.day != 13 else 'th'} {MONTH_NAMES[dt.month - 1]} {dt.year}"
        return f"{dt.day:02d}/{dt.month:02d}/{dt.year}"

    def date2(self) -> str:
        return self.date()

    def month(self) -> str:
        return self.rng.choice(MONTH_NAMES)

    def receipt(self) -> str:
        return str(self.rng.randint(1000, 999999))

    def utr(self) -> str:
        return f"UTR{self.rng.randint(100000000, 999999999)}"

    def letter_no(self) -> str:
        return f"AICTE/{self.rng.choice(['PGRC', 'RB', 'RO', 'EVC'])}/{self.year}/{self.rng.randint(100, 9999)}"

    def ref(self, case_id: str) -> str:
        tail = "".join(ch for ch in case_id if ch.isdigit())[-6:] or str(self.rng.randint(100000, 999999))
        return f"{self.rng.choice(['GRV', 'CMP', 'REF'])}/{self.year}/{tail}"

    def contact(self) -> str:
        return self.rng.choice(["98XXXXXX21", "87XXXXXX04", "r***@gmail.com", "s***@yahoo.com"])

    def programme(self) -> str:
        return self.rng.choice(PROGRAMMES)

    def department(self) -> str:
        return self.rng.choice(DEPARTMENTS)

    def semester(self) -> str:
        return self.rng.choice(SEMESTERS)

    def lab(self) -> str:
        return self.rng.choice(LABS)

    def building(self) -> str:
        return self.rng.choice(BUILDINGS)

    def locality(self, city: str | None = None) -> str:
        return self.rng.choice(LOCALITIES.get(city or "", ["Main Road", "Station Road", "College Road"]))

    def person(self) -> str:
        return self.rng.choice(FICTIONAL_PEOPLE)

    def staff(self) -> str:
        return self.rng.choice(FICTIONAL_STAFF)

    def placement_pct(self) -> str:
        return self.rng.choice(PLACEMENT_PCTS)

    def values(self, case_id: str, *, institution: str, city: str | None = None) -> dict[str, str]:
        amt = self.amount_value(8000, 240000)
        return {
            "institution": institution,
            "city": city or "the city",
            "locality": self.locality(city),
            "programme": self.programme(),
            "department": self.department(),
            "sem": self.semester(),
            "year": self.academic_year(),
            "join_year": self.join_year(),
            "pass_year": self.pass_year(),
            "date": self.date(),
            "date2": self.date2(),
            "month": self.month(),
            "amount": indian_amount(amt),
            "amount2": indian_amount(max(1000, amt - self.rng.randint(500, 4000))),
            "receipt": self.receipt(),
            "utr": self.utr(),
            "letter_no": self.letter_no(),
            "ref": self.ref(case_id),
            "case_id": case_id,
            "staff": self.staff(),
            "official": self.person(),
            "building": self.building(),
            "lab": self.lab(),
            "days": str(self.rng.randint(7, 120)),
            "years": str(self.rng.randint(2, 16)),
            "phone": self.contact(),
            "masked_email": self.rng.choice(["r***@gmail.com", "s***@yahoo.com", "student.***@example.invalid"]),
            "placement_pct": self.placement_pct(),
            "intake": str(self.rng.choice([60, 90, 120, 180])),
            "actual_intake": str(self.rng.choice([150, 180, 240, 300])),
            "faculty_count": str(self.rng.choice([24, 30, 36, 42])),
            "district": city or "the district",
        }
