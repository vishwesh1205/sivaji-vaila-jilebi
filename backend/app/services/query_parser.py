import re
from typing import Any


REGIONS = {
    "southern": ["Chennai", "Hyderabad", "Bengaluru"],
    "south": ["Chennai", "Hyderabad", "Bengaluru"],
    "western": ["Pune", "Mumbai"],
    "eastern": ["Kolkata"],
    "northern": ["Chandigarh", "Jaipur"],
    "central": ["Bhopal", "Kanpur"],
    "north eastern": ["Guwahati"],
}
CATEGORIES = {
    "fee": "FEE", "fees": "FEE", "faculty": "FACULTY", "infrastructure": "INFRASTRUCTURE",
    "approval": "APPROVAL_VIOLATION", "ragging": "RAGGING_DISCRIMINATION", "discrimination": "RAGGING_DISCRIMINATION",
}
STATUSES = {
    "pending": "PENDING", "under process": "UNDER_PROCESS", "disposed": "DISPOSED",
    "transferred": "TRANSFERRED", "escalated": "ESCALATED",
}


def parse_query(text: str) -> dict[str, Any]:
    q = text.lower()
    filters: dict[str, Any] = {}
    chips = []
    bureaus = []
    for b in ["RB", "PGRC", "RO"]:
        if re.search(rf"\b{b.lower()}\b", q):
            bureaus.append(b)
    if bureaus:
        filters["bureaus"] = bureaus
        chips.append({"key": "bureaus", "label": "Bureaus: " + " + ".join(bureaus), "value": bureaus})
    if "overlap" in q:
        filters["overlap_only"] = True
        chips.append({"key": "overlap_only", "label": "Overlap only", "value": True})
    for name, regions in REGIONS.items():
        if name in q:
            filters["regions"] = regions
            chips.append({"key": "regions", "label": f"Region: {name.title()}", "value": regions})
            break
    m = re.search(r"older than (\d+) days?", q)
    if m:
        filters["min_age_days"] = int(m.group(1))
        chips.append({"key": "min_age_days", "label": f"Older than {m.group(1)} days", "value": int(m.group(1))})
    for word, cat in CATEGORIES.items():
        if re.search(rf"\b{word}\b", q):
            filters["category"] = cat
            chips.append({"key": "category", "label": f"Category: {cat.replace('_', ' ').title()}", "value": cat})
            break
    for phrase, status in STATUSES.items():
        if phrase in q:
            filters["status"] = status
            chips.append({"key": "status", "label": f"Status: {status.replace('_', ' ').title()}", "value": status})
            break
    aid = re.search(r"\b(1-\d{6,8})\b", text)
    if aid:
        filters["aicte_id"] = aid.group(1)
        chips.append({"key": "aicte_id", "label": f"AICTE ID: {aid.group(1)}", "value": aid.group(1)})
    cid = re.search(r"\b([A-Z]{2,8}-\d{4}-\d{3,6}|PG-2026-\d+|RB-2026-\d+)\b", text, re.I)
    if cid:
        filters["case_id"] = cid.group(1)
        chips.append({"key": "case_id", "label": f"Case: {cid.group(1)}", "value": cid.group(1)})
    if "institution" in q and not filters:
        chips.append({"key": "target", "label": "Target: Institutions", "value": "institutions"})
    interpreted = "Filter cases"
    if "institution" in q and "overlap" in q:
        interpreted = "Institutions with overlap alerts"
    if not chips:
        filters["q"] = text.strip()
        chips.append({"key": "q", "label": f"Search: {text.strip()}", "value": text.strip()})
        interpreted = f"Keyword search for “{text.strip()}”"
    else:
        interpreted = "Interpreted as: " + " · ".join(c["label"] for c in chips)
    return {
        "query": text,
        "filters": filters,
        "chips": chips,
        "interpreted_as": interpreted,
        "method": "deterministic_keyword_parser",
        "llm_enabled": False,
    }
