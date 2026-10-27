from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Iterable

from . import library
from .slots import Slots, indian_amount
from .taxonomy import (
    CATEGORY_SUBTYPES,
    COMPLAINANT_TYPES,
    GRAPHIC_TERMS,
    RESTRICTED_CATEGORIES,
)

SHORT, MEDIUM, LONG, ULTRA = "SHORT", "MEDIUM", "LONG", "ULTRA"

# Target distribution used when reseeding the corpus.
LENGTH_QUOTAS = {SHORT: 0.15, MEDIUM: 0.40, LONG: 0.35, ULTRA: 0.10}

LANGUAGE_MIX = {"en": 0.89, "hi": 0.08, "ta": 0.008, "te": 0.008, "bn": 0.008, "mr": 0.006}

INTERNAL_PERSONAS = {"AICTE_INTERNAL", "REGIONAL_OFFICE_REPORT", "MINISTRY_REFERENCE", "COURT_DIRECTION"}

PERSONA_WEIGHTS: dict[str, dict[str, float]] = {
    "default": {
        "STUDENT": 0.36, "PARENT": 0.18, "FACULTY": 0.09, "NON_TEACHING_STAFF": 0.03,
        "ALUMNUS": 0.05, "ANONYMOUS_WELLWISHER": 0.08, "ADVOCATE_ON_BEHALF": 0.04,
        "STUDENT_ASSOCIATION": 0.04, "MINISTRY_REFERENCE": 0.03, "MP_MLA_REFERENCE": 0.03,
        "COURT_DIRECTION": 0.02, "AICTE_INTERNAL": 0.03, "REGIONAL_OFFICE_REPORT": 0.02,
    },
    "FACULTY": {
        "FACULTY": 0.42, "NON_TEACHING_STAFF": 0.12, "STUDENT": 0.16, "PARENT": 0.06,
        "ALUMNUS": 0.04, "ANONYMOUS_WELLWISHER": 0.06, "STUDENT_ASSOCIATION": 0.03,
        "AICTE_INTERNAL": 0.05, "REGIONAL_OFFICE_REPORT": 0.04, "MINISTRY_REFERENCE": 0.02,
    },
    "GOVERNANCE_MISCONDUCT": {
        "ANONYMOUS_WELLWISHER": 0.18, "ADVOCATE_ON_BEHALF": 0.10, "FACULTY": 0.15,
        "NON_TEACHING_STAFF": 0.08, "STUDENT_ASSOCIATION": 0.08, "ALUMNUS": 0.06,
        "STUDENT": 0.10, "MINISTRY_REFERENCE": 0.06, "MP_MLA_REFERENCE": 0.06,
        "COURT_DIRECTION": 0.05, "AICTE_INTERNAL": 0.06, "REGIONAL_OFFICE_REPORT": 0.02,
    },
    "RAGGING_DISCRIMINATION": {
        "STUDENT": 0.36, "PARENT": 0.18, "ANONYMOUS_WELLWISHER": 0.22,
        "STUDENT_ASSOCIATION": 0.10, "ALUMNUS": 0.04, "ADVOCATE_ON_BEHALF": 0.04,
        "AICTE_INTERNAL": 0.03, "REGIONAL_OFFICE_REPORT": 0.03,
    },
}

SUBJECTS = {
    "FEE": {
        "EXCESS_FEE": "Excess fee collected above the notified fee structure",
        "REFUND_NOT_GIVEN": "Refund not processed after withdrawal from programme",
        "DOCUMENTS_WITHHELD": "Original certificates withheld for disputed dues",
        "HIDDEN_CHARGES": "Hidden charges collected without approved fee head",
        "CASH_WITHOUT_RECEIPT": "Cash fee collection without a valid receipt",
    },
    "FACULTY": {
        "SALARY_UNPAID": "Unpaid / short-paid salary of faculty members",
        "GHOST_FACULTY": "Faculty shown on portal but not attending classes",
        "FORCED_RESIGNATION": "Pressure on faculty members to resign",
        "QUALIFICATION_NOT_AS_PER_NORMS": "Faculty qualifications not as per AICTE norms",
        "FACULTY_STUDENT_RATIO": "Faculty-student ratio below prescribed norm",
    },
    "INFRASTRUCTURE": {
        "LAB_WITHOUT_EQUIPMENT": "Laboratory equipment unavailable for practical classes",
        "LIBRARY_DEFICIENT": "Inadequate library books and journals",
        "HOSTEL_MESS_CONDITIONS": "Unsafe and unhygienic hostel / mess conditions",
        "BUILDING_SAFETY": "Building safety and structural concerns",
        "NO_FIRE_NOC": "Valid fire NOC not available",
        "NO_PLAYGROUND": "Playground converted for other use",
    },
    "APPROVAL_VIOLATION": {
        "BEYOND_INTAKE": "Admissions beyond approved intake",
        "UNAPPROVED_PROGRAMME": "Unapproved programme being advertised and run",
        "FALSE_APPROVAL_CLAIM": "False claim of AICTE approval in advertisements",
        "LAPSED_APPROVAL": "Programme continuing after approval lapsed",
        "SECOND_SHIFT": "Second shift operated without approval",
        "AFFILIATION_ISSUE": "Affiliation / university recognition issue",
    },
    "ACADEMIC_ADMINISTRATION": {
        "EXAM_RESULT_DELAY": "Examination results not declared on time",
        "INTERNAL_MARKS_MISUSE": "Internal assessment marks changed arbitrarily",
        "ATTENDANCE_THREAT": "Attendance shortage threatened despite genuine absence",
        "PLACEMENT_FALSE_CLAIM": "Placement figures falsely advertised",
        "MIGRATION_CERTIFICATE": "Migration / transfer certificate not issued",
    },
    "RAGGING_DISCRIMINATION": {
        "RAGGING_HOSTEL": "Harassment of junior students in the hostel",
        "DISCRIMINATION_CASTE_GENDER": "Discriminatory treatment on campus",
        "HARASSMENT_GENERAL": "Harassment by seniors or staff",
    },
    "GOVERNANCE_MISCONDUCT": {
        "MANAGEMENT_DISPUTE": "Management dispute affecting academic administration",
        "FUND_MISUSE": "Misuse of institutional funds and fee collections",
        "FAKE_DOCUMENTS": "Fabricated documents submitted for approval",
    },
    "OTHER": {
        "TRANSPORT": "Bus fee increase and denial of transport",
        "SCHOLARSHIP": "Scholarship amount not credited to students",
        "GENERAL_GRIEVANCE": "Grievance not addressed by institutional grievance cell",
    },
}

SIGNATURES = {
    "STUDENT": "Yours sincerely,\n{sname}\n{programme}, {institution}",
    "PARENT": "Yours sincerely,\n{sname}\nParent / guardian",
    "FACULTY": "Yours sincerely,\n{sname}\nFaculty member, {department}",
    "NON_TEACHING_STAFF": "Yours sincerely,\n{sname}\nNon-teaching staff, {institution}",
    "ALUMNUS": "Yours sincerely,\n{sname}\nAlumnus, {programme} ({pass_year})",
    "ANONYMOUS_WELLWISHER": "Yours faithfully,\nName and address withheld on request",
    "ADVOCATE_ON_BEHALF": "Yours faithfully,\n{sname}\nAdvocate for the complainants (fictional)",
    "STUDENT_ASSOCIATION": "Yours faithfully,\n{sname}\nGeneral Secretary, Students' Association",
    "MINISTRY_REFERENCE": "Yours faithfully,\n{sname}\nFor Director (Technical Education)",
    "MP_MLA_REFERENCE": "Yours faithfully,\n{sname}\nOffice of the public representative",
    "COURT_DIRECTION": "Yours faithfully,\n{sname}\nDealing Assistant, Legal Cell",
    "AICTE_INTERNAL": "Submitted for kind consideration,\n{sname}\n{sname_designation}",
    "REGIONAL_OFFICE_REPORT": "Yours faithfully,\n{sname}\nRegional Officer (fictional)",
}

OFFICIAL_DESIGNATIONS = {
    "AICTE_INTERNAL": "Section Officer, Approval Bureau",
    "REGIONAL_OFFICE_REPORT": "Regional Officer",
    "MINISTRY_REFERENCE": "Under Secretary, Ministry of Education",
    "COURT_DIRECTION": "Legal Cell",
    "MP_MLA_REFERENCE": "Private Secretary",
}

REMARKS_POOL = {
    "CREATED": [
        "Complaint received through {channel_label} and registered on the grievance portal.",
        "Representation diarised and forwarded to the dealing section for examination.",
        "Case registered; complaint and attachments placed on the case file.",
        "Grievance entered in the monitoring system and acknowledgement generated.",
    ],
    "INSTITUTION_RESOLVED": [
        "Institution identified as {institution} (AICTE ID {aicte_id}); linked to the master record.",
        "Reference matched with {institution} using the institution master data.",
        "The institution was resolved from the complaint text and linked for further action.",
    ],
    "DOCUMENT_ADDED": [
        "Copy of the fee receipt and bank statement placed on record.",
        "Representation submitted to the institution along with postal acknowledgement uploaded.",
        "Photographs of the laboratory and the attendance register uploaded for verification.",
        "Institution's reply received and scanned on to the file.",
        "Copy of the approval letter and admission brochure uploaded.",
    ],
    "STATUS_CHANGED": [
        "Case taken up with the institution; status changed to under process.",
        "Factual report sought from the institution within fifteen days.",
        "Institution asked to furnish the relevant records and a para-wise reply.",
        "Interim reply received; further clarification sought from the institution.",
        "Matter examined with the approval records and placed for supervisory review.",
    ],
    "REMARK": [
        "Institution's reply is silent on the specific amount collected; a fresh query has been issued.",
        "The documents prima facie show a discrepancy between the notified fee and the amount collected.",
        "Regional office asked to verify the position during the next scheduled visit.",
        "Complainant contacted for a copy of the original receipt; response awaited.",
        "The institution has been advised to display the approved fee structure on its website.",
        "File put up for approval of the competent authority.",
        "No response received within the stipulated period; reminder issued.",
    ],
    "TRANSFERRED": [
        "Case transferred to the Regional Office for a local enquiry and factual report.",
        "Matter forwarded to the Approval Bureau for verification of approval conditions.",
        "Transferred to the Regulation Bureau in view of the regulatory issues involved.",
    ],
    "ESCALATED": [
        "Case escalated to the competent authority for want of a satisfactory institutional response.",
        "Escalated for consideration of regulatory action in view of repeated non-compliance.",
        "Matter placed before the higher authority because the reply was incomplete.",
    ],
    "OUTCOME_TAGGED": [
        "Institution's response examined and deficiency recorded on the file.",
        "Verification completed; final outcome recorded and communicated to the complainant.",
        "Inquiry report considered and the case disposed with the recorded outcome.",
    ],
    "OVERLAP_ACK": [
        "Acknowledged the overlapping case from another bureau and coordinated the response.",
        "Overlap with a parallel case noted; a common factual report will be obtained.",
    ],
}

NEXT_ACTIONS = {
    "PENDING": ["Await institution reply", "Assign to dealing officer", "Seek documents from complainant", "Register and acknowledge"],
    "UNDER_PROCESS": ["Examine institution reply", "Seek factual report from RO", "Place file for supervisory review", "Issue reminder to institution"],
    "DISPOSED": ["Close case file", "Communicate outcome to complainant"],
    "TRANSFERRED": ["Await action report from transferred bureau", "Track in receiving bureau"],
    "ESCALATED": ["Place before competent authority", "Await decision on regulatory action"],
}

CHANNEL_LABELS = {
    "CSS": "the Centralised Public Grievance Redress and Monitoring System",
    "CPGRAMS": "CPGRAMS",
    "EMAIL": "email",
    "PHYSICAL": "a physical representation",
    "DIRECT": "the AICTE internal receipt",
    "REGIONAL": "the Regional Office",
}

BANNED_PII = [
    r"(?<!\d)(?:\+?91[-\s]?)?[6-9]\d{9}(?!\d)",
    r"\b\d{12}\b",
    r"\b[A-Z]{5}\d{4}[A-Z]\b",
    r"\b\d{4}\s?\d{4}\s?\d{4}\b",
]

NON_MASKED_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


@dataclass
class GeneratedNarrative:
    subject: str
    narrative: str
    narrative_original: str
    language: str
    complainant_type: str
    length_bucket: str
    unique_ref: str
    restricted: bool = False
    metadata: dict = field(default_factory=dict)


def weighted_choice(rng: random.Random, weights: dict[str, float]) -> str:
    total = sum(weights.values())
    pick = rng.random() * total
    upto = 0.0
    for key, weight in weights.items():
        upto += weight
        if pick <= upto:
            return key
    return next(reversed(weights))


def length_buckets(count: int, rng: random.Random) -> list[str]:
    quotas = {
        SHORT: round(count * LENGTH_QUOTAS[SHORT]),
        MEDIUM: round(count * LENGTH_QUOTAS[MEDIUM]),
        LONG: round(count * LENGTH_QUOTAS[LONG]),
    }
    quotas[ULTRA] = count - sum(quotas.values())
    buckets = [b for b, n in quotas.items() for _ in range(n)]
    rng.shuffle(buckets)
    return buckets


def pick_language(rng: random.Random) -> str:
    pick = rng.random()
    upto = 0.0
    for code, weight in LANGUAGE_MIX.items():
        upto += weight
        if pick <= upto:
            return code
    return "en"


def short_institution(name: str) -> str:
    name = re.sub(r"\s+(Institute|College|School) of .*$", "", name)
    return name if len(name) <= 55 else name[:52].rstrip() + "..."


def noisify_institution_reference(rng: random.Random, inst, style: str) -> str:
    name = inst.name
    if style == "abbrev":
        return (
            name.replace("Institute", "Inst").replace("College", "Coll")
            .replace("Technology", "Tech").replace("Engineering", "Engg")
        )
    if style == "nickname":
        words = name.split()
        return " ".join(words[: min(3, len(words))]) + f", {inst.city}"
    if style == "typo":
        text = name
        if len(text) > 12:
            pos = rng.randint(4, len(text) - 3)
            op = rng.choice(["drop", "swap", "double"])
            if op == "drop":
                text = text[:pos] + text[pos + 1 :]
            elif op == "swap" and text[pos] != text[pos + 1]:
                text = text[:pos] + text[pos + 1] + text[pos] + text[pos + 2 :]
            else:
                text = text[:pos] + text[pos] + text[pos:]
        return f"{text}, {inst.city}"
    if style == "city_type":
        return f"the engineering college in {inst.city} where the complainant is studying"
    if style == "wrong_district":
        other = rng.choice(["Delhi", "Lucknow", "Nagpur", "Indore", "Patna", "Bhopal", "Surat"])
        return f"{name}, {other}"
    if style == "missing":
        return f"my college in {inst.city}"
    return name


def filler(values: dict[str, str], template: str) -> str:
    return template.format_map(values)


class NarrativeEngine:
    """Offline template/slot engine. Deterministic for a given seed and case id.

    The engine deliberately mixes registers, lengths, languages and noise so the
    corpus does not look like a single sentence repeated with an ID appended.
    """

    def __init__(self, seed: int = 20261025):
        self.seed = seed

    def rng_for(self, case_id: str, salt: str = "") -> random.Random:
        return random.Random(f"{self.seed}:{case_id}:{salt}")

    def pick_persona(self, rng: random.Random, category: str) -> str:
        return weighted_choice(rng, PERSONA_WEIGHTS.get(category, PERSONA_WEIGHTS["default"]))

    def pick_channel(self, rng: random.Random, persona: str, weights: dict[str, float]) -> str:
        if persona == "AICTE_INTERNAL":
            return "DIRECT"
        if persona == "REGIONAL_OFFICE_REPORT":
            return "REGIONAL"
        if persona == "MINISTRY_REFERENCE":
            return rng.choice(["EMAIL", "PHYSICAL"])
        if persona == "COURT_DIRECTION":
            return rng.choice(["EMAIL", "PHYSICAL"])
        return weighted_choice(rng, weights)

    def build(
        self,
        *,
        case_id: str,
        institution,
        category: str,
        subtype: str,
        persona: str | None = None,
        channel: str | None = None,
        bucket: str | None = None,
        channel_weights: dict[str, float] | None = None,
        shared_values: dict[str, str] | None = None,
        force_language: str | None = None,
        ref_style: str | None = None,
    ) -> GeneratedNarrative:
        rng = self.rng_for(case_id, "narrative")
        category = category if category in CATEGORY_SUBTYPES else "OTHER"
        if subtype not in CATEGORY_SUBTYPES.get(category, {}):
            subtype = next(iter(CATEGORY_SUBTYPES[category]))
        persona = persona or self.pick_persona(rng, category)
        if persona not in COMPLAINANT_TYPES:
            persona = "STUDENT"
        channel = channel or self.pick_channel(rng, persona, channel_weights or {"CSS": 0.3, "CPGRAMS": 0.3, "EMAIL": 0.15, "PHYSICAL": 0.1, "DIRECT": 0.05, "REGIONAL": 0.1})
        bucket = bucket or weighted_choice(rng, LENGTH_QUOTAS)

        city = getattr(institution, "city", None)
        inst_name = getattr(institution, "name", "the institution")
        slots = Slots(rng)
        values = slots.values(case_id, institution=inst_name, city=city)
        if shared_values:
            values.update(shared_values)
        values.update(
            {
                "institution": inst_name,
                "sname": slots.person(),
                "sname_designation": OFFICIAL_DESIGNATIONS.get(persona, "Dealing Officer"),
                "channel_label": CHANNEL_LABELS.get(channel, channel),
            }
        )
        subject = filler(values, self._subject(category, subtype, persona, institution))
        body = self._compose(rng, persona, category, subtype, bucket, values)
        body = self._fit_body(body, bucket)
        narrative = self._wrap(rng, persona, channel, subject, body, values, bucket)
        narrative = self._apply_noise(rng, narrative, persona, bucket)
        narrative = re.sub(r"[ \t]+\n", "\n", narrative).strip()

        language = force_language or pick_language(rng)
        if language == "en":
            original = narrative
        else:
            original = self._indic_original(rng, language, category, subtype, values, persona)

        unique_ref = values["ref"]
        return GeneratedNarrative(
            subject=subject,
            narrative=narrative,
            narrative_original=original,
            language=language,
            complainant_type=persona,
            length_bucket=self.length_bucket(narrative),
            unique_ref=unique_ref,
            restricted=category in RESTRICTED_CATEGORIES,
            metadata={"channel": channel, "values": values, "ref_style": ref_style},
        )

    def _subject(self, category: str, subtype: str, persona: str, institution) -> str:
        base = SUBJECTS[category][subtype]
        if persona in {"AICTE_INTERNAL", "REGIONAL_OFFICE_REPORT"}:
            return f"Factual report / verification: {base}"
        if persona in {"MINISTRY_REFERENCE", "MP_MLA_REFERENCE"}:
            return f"Reference for action: {base}"
        if persona == "COURT_DIRECTION":
            return f"Compliance report sought: {base}"
        return f"{base} - {short_institution(getattr(institution, 'name', 'institution'))}"

    @staticmethod
    def _fit_body(body: str, bucket: str) -> str:
        limits = {SHORT: 42, MEDIUM: 88, LONG: 192, ULTRA: 340}
        limit = limits[bucket]
        words = body.split()
        if len(words) <= limit:
            return body
        sentences = re.split(r"(?<=[.!?])\s+", body)
        kept: list[str] = []
        used = 0
        for sentence in sentences:
            n = len(sentence.split())
            if kept and used + n > limit:
                break
            kept.append(sentence)
            used += n
        text = " ".join(kept).strip()
        if not text:
            text = " ".join(words[:limit]) + "."
        return text

    def _compose(self, rng: random.Random, persona: str, category: str, subtype: str, bucket: str, values: dict[str, str]) -> str:
        opener = filler(values, rng.choice(library.PERSONA_OPENERS[persona]))
        core_pool = library.CORE_TEMPLATES[category][subtype]
        core = filler(values, rng.choice(core_pool))
        short = filler(values, rng.choice(library.SHORT_TEMPLATES[category]))
        tried = filler(values, rng.choice(library.TRY_LINES))
        fear = filler(values, rng.choice(library.FEAR_LINES))
        ask = filler(values, rng.choice(library.ASK_LINES.get(category, library.ASK_LINES["OTHER"])))
        legal = rng.choice(library.LEGAL_BOILERPLATE)
        trailing = rng.choice(library.TRAILING_LINES)

        if bucket == SHORT:
            parts = [opener, short] if rng.random() < 0.35 else [short]
            if rng.random() < 0.5:
                parts.append(trailing)
            return " ".join(parts)

        if bucket == MEDIUM:
            parts = [opener, short if len(short.split()) < 42 and rng.random() < 0.35 else core]
            if len(" ".join(parts).split()) < 70:
                parts.append(ask)
            return " ".join(parts)

        if bucket == LONG:
            parts = [opener, core]
            if rng.random() < 0.75:
                parts.append(tried)
            if persona == "ANONYMOUS_WELLWISHER" or rng.random() < 0.35:
                parts.append(fear)
            parts.append(ask)
            if rng.random() < 0.55:
                parts.append(legal)
            return " ".join(parts)

        # ULTRA: an exasperated, repetitive representation with enclosures.
        second = filler(values, rng.choice(core_pool))
        parts = [opener, core, tried]
        if persona == "ANONYMOUS_WELLWISHER" or rng.random() < 0.6:
            parts.append(fear)
        parts.extend([ask, second, legal, rng.choice(library.LEGAL_BOILERPLATE)])
        if rng.random() < 0.5:
            parts.append("The complainant has previously approached the institution on more than one occasion and the file contains the acknowledgements.")
        parts.append(trailing)
        return " ".join(parts)

    def _wrap(self, rng: random.Random, persona: str, channel: str, subject: str, body: str, values: dict[str, str], bucket: str = LONG) -> str:
        signature = filler(values, SIGNATURES[persona])
        ref = values["ref"]
        if bucket in {SHORT, MEDIUM}:
            if channel == "CSS":
                return f"{subject}\n{body} Ref: {ref}"
            if channel == "CPGRAMS":
                return f"CPGRAMS complaint: {body} Reg. no. {ref}"
            if channel == "EMAIL":
                return f"Email to grievance cell: {body} Ref: {ref}"
            if channel == "PHYSICAL":
                return f"Physical representation: {body} Diary no. {ref}"
            if channel == "DIRECT":
                return f"Internal note (File {values['letter_no']}): {body}"
            if channel == "REGIONAL":
                return f"Regional Office note (File {values['letter_no']}): {body}"
            return f"{body} Reference: {ref}"
        if channel == "CSS":
            return f"Subject: {subject}\n\n{body}\n\nComplainant reference: {ref}\n{signature}"
        if channel == "CPGRAMS":
            return f"Respected Sir/Madam,\n\nSubject: {subject}\n\n{body}\n\nRegistration no. {ref}\n{signature}"
        if channel == "EMAIL":
            return f"To: grievance cell\nSubject: {subject}\n\nDear Sir/Madam,\n\n{body}\n\nReference: {ref}\n{signature}\nContact: {values['phone']}"
        if channel == "PHYSICAL":
            return f"Representation received at the AICTE receipt counter\nDiary no. {ref}\nSubject: {subject}\n\n{body}\n\n{signature}\nContact: {values['phone']}"
        if channel == "DIRECT":
            return f"INTERNAL NOTE\nFile No. {values['letter_no']}\nSubject: {subject}\n\n{body}\n\n{signature}"
        if channel == "REGIONAL":
            return f"REGIONAL OFFICE NOTE\nFile No. {values['letter_no']}\nReceived on {values['date']} at {values['locality']} office\nSubject: {subject}\n\n{body}\n\n{signature}\nContact: {values['masked_email']}"
        return f"{body}\n\nReference: {ref}"

    def _apply_noise(self, rng: random.Random, text: str, persona: str, bucket: str = LONG) -> str:
        if rng.random() < 0.20:
            letters = list(text)
            positions = [i for i, ch in enumerate(letters) if ch.isalpha() and i > 20]
            if positions:
                pos = rng.choice(positions)
                if letters[pos].lower() != "a":
                    letters[pos] = rng.choice("aeiours")
                text = "".join(letters)
        if rng.random() < 0.06:
            sentences = re.split(r"(?<=[.!?])\s+", text)
            if len(sentences) > 2:
                idx = rng.randrange(1, len(sentences))
                sentences[idx] = rng.choice(library.NOISE_CAPS)
                text = " ".join(sentences)
        if rng.random() < 0.10:
            text = text.rstrip(".")
        if bucket != SHORT and rng.random() < 0.07:
            text += "\n" + rng.choice(library.HINGLISH_LINES)
        if bucket != SHORT and rng.random() < 0.04:
            sentences = re.split(r"(?<=[.!?])\s+", text)
            if len(sentences) > 2:
                text = text.rstrip() + " " + sentences[-2]
        if rng.random() < 0.03:
            text = text.replace("the institution", "the college").replace("The institution", "The college")
        return text

    def _indic_original(self, rng: random.Random, language: str, category: str, subtype: str, values: dict[str, str], persona: str) -> str:
        templates = library.INDIC_TEMPLATES.get(language, library.INDIC_TEMPLATES["hi"])
        template = templates.get(category, templates["OTHER"])
        text = template.format_map(values)
        if persona in {"AICTE_INTERNAL", "REGIONAL_OFFICE_REPORT"} and language == "hi":
            text = "आंतरिक टिप्पणी: " + text
        return text

    @staticmethod
    def length_bucket(text: str) -> str:
        words = len(text.split())
        if words <= 55:
            return SHORT
        if words <= 100:
            return MEDIUM
        if words <= 205:
            return LONG
        return ULTRA

    @staticmethod
    def word_count(text: str) -> int:
        return len(text.split())


def validate_text(text: str, *, restricted: bool = False) -> list[str]:
    issues: list[str] = []
    for pattern in BANNED_PII:
        if re.search(pattern, text):
            issues.append(f"unmasked identifier: {pattern}")
    for match in NON_MASKED_EMAIL.finditer(text):
        if "*" not in match.group(0) and not match.group(0).endswith(".invalid"):
            issues.append(f"unmasked email: {match.group(0)}")
    lowered = text.lower()
    for term in GRAPHIC_TERMS:
        if term in lowered:
            issues.append(f"graphic/restricted term: {term}")
    if restricted and any(word in lowered for word in ("naked", "explicit", "graphic detail")):
        issues.append("restricted complaint contains graphic description")
    return issues


def validate_corpus(records: Iterable[dict], *, expect_length_mix: bool = True) -> dict:
    """Validate generated records and return summary counts.

    Records may be dictionaries or objects with the same attribute names.
    """
    records = list(records)
    if not records:
        raise AssertionError("empty corpus")
    lengths: dict[str, int] = {SHORT: 0, MEDIUM: 0, LONG: 0, ULTRA: 0}
    languages: dict[str, int] = {}
    personas: dict[str, int] = {}
    categories: dict[str, int] = {}
    for record in records:
        get = record.get if isinstance(record, dict) else lambda k, r=record: getattr(r, k)
        narrative = get("narrative") or ""
        if not narrative.strip():
            raise AssertionError(f"empty narrative for {get('case_id')}")
        issues = validate_text(narrative, restricted=get("category") in RESTRICTED_CATEGORIES)
        if issues:
            raise AssertionError(f"{get('case_id')}: {issues}")
        bucket = get("length_bucket") or NarrativeEngine.length_bucket(narrative)
        lengths[bucket] = lengths.get(bucket, 0) + 1
        lang = get("language") or "en"
        languages[lang] = languages.get(lang, 0) + 1
        persona = get("complainant_type") or "UNKNOWN"
        personas[persona] = personas.get(persona, 0) + 1
        category = get("category") or "UNKNOWN"
        categories[category] = categories.get(category, 0) + 1
    n = len(records)
    if expect_length_mix and n >= 40:
        short_share = lengths[SHORT] / n
        medium_share = lengths[MEDIUM] / n
        long_share = lengths[LONG] / n
        ultra_share = lengths[ULTRA] / n
        if not (0.08 <= short_share <= 0.25):
            raise AssertionError(f"short share out of range: {short_share:.2%}")
        if not (0.28 <= medium_share <= 0.52):
            raise AssertionError(f"medium share out of range: {medium_share:.2%}")
        if not (0.25 <= long_share <= 0.46):
            raise AssertionError(f"long share out of range: {long_share:.2%}")
        if not (0.04 <= ultra_share <= 0.18):
            raise AssertionError(f"ultra share out of range: {ultra_share:.2%}")
    return {
        "count": n,
        "lengths": lengths,
        "languages": languages,
        "personas": personas,
        "categories": categories,
    }
