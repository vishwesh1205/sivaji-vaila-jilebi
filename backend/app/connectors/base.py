import abc
import csv
import hashlib
import io
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import yaml
from langdetect import detect, LangDetectException

from ..config import settings


BACKEND_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class CanonicalTicket:
    source_name: str
    source_type: str
    source_record_id: str
    institution_text: str
    narrative: str
    category: str
    date_received: datetime
    bureau_code: str = "RB"
    status: str = "PENDING"
    language: str = "en"
    complainant_hash: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def load_mapping(filename: str) -> dict[str, Any]:
    path = BACKEND_ROOT / "config" / filename
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_date(value: Any, formats: list[str]) -> datetime:
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.utcnow()
    text = str(value)
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return datetime.utcnow()


def map_category(value: Any) -> str:
    text = str(value or "OTHER").upper().replace(" ", "_").replace("-", "_")
    synonyms = {
        "FEES": "FEE",
        "FEE_RELATED": "FEE",
        "FACULTY_SHORTAGE": "FACULTY",
        "INFRA": "INFRASTRUCTURE",
        "RAGGING": "RAGGING_DISCRIMINATION",
        "DISCRIMINATION": "RAGGING_DISCRIMINATION",
        "APPROVAL": "APPROVAL_VIOLATION",
        "AFFILIATION": "APPROVAL_VIOLATION",
    }
    text = synonyms.get(text, text)
    valid = {"FEE", "FACULTY", "INFRASTRUCTURE", "APPROVAL_VIOLATION", "RAGGING_DISCRIMINATION", "OTHER"}
    return text if text in valid else "OTHER"


def detect_language(text: str) -> str:
    if not text:
        return "en"
    try:
        return detect(text)
    except LangDetectException:
        return "en"


def hash_identifier(identifier: str | None) -> str | None:
    if not identifier:
        return None
    salted = f"{settings.complainant_hash_salt}:{identifier}".encode("utf-8")
    return hashlib.sha256(salted).hexdigest()


class BaseConnector(abc.ABC):
    name: str
    source_type: str
    mode: str

    @abc.abstractmethod
    def healthcheck(self) -> dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    def fetch(self, since: datetime | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abc.abstractmethod
    def normalize(self, raw: dict[str, Any]) -> CanonicalTicket:
        raise NotImplementedError

    def source_meta(self) -> dict[str, Any]:
        return {"name": self.name, "source_type": self.source_type, "mode": self.mode}


class MappedHttpConnector(BaseConnector):
    mapping_file = ""

    def __init__(self) -> None:
        self.mapping = load_mapping(self.mapping_file)
        self.date_formats = self.mapping.get("date_formats") or ["%Y-%m-%d"]

    @property
    def base_url(self) -> str:
        raise NotImplementedError

    def _snapshot(self) -> list[dict[str, Any]]:
        path = BACKEND_ROOT / "app" / "connectors" / "snapshots" / f"{self.name}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("tickets", data) if isinstance(data, dict) else data
        return []

    def fetch(self, since: datetime | None = None) -> list[dict[str, Any]]:
        if self.mode == "file":
            return self._fetch_file()
        if self.mode == "live":
            try:
                with httpx.Client(timeout=settings.connector_timeout_seconds) as client:
                    params = {"since": since.isoformat()} if since else {}
                    response = client.get(f"{self.base_url.rstrip('/')}/tickets", params=params)
                    response.raise_for_status()
                    data = response.json()
                    raw = data.get("tickets", data) if isinstance(data, dict) else data
                    return list(raw)
            except Exception:
                return self._snapshot()
        # simulator mode
        with httpx.Client(timeout=settings.connector_timeout_seconds) as client:
            params = {"since": since.isoformat()} if since else {}
            response = client.get(f"{self.base_url.rstrip('/')}/tickets", params=params)
            response.raise_for_status()
            data = response.json()
            return list(data.get("tickets", data) if isinstance(data, dict) else data)

    def _fetch_file(self) -> list[dict[str, Any]]:
        configured = settings.css_file_path if self.name == "css" else settings.cpgrams_file_path
        path = Path(configured)
        if not path.is_absolute():
            candidates = [
                BACKEND_ROOT.parent / path,
                BACKEND_ROOT / path,
                BACKEND_ROOT / Path(str(path).removeprefix("backend/")),
                Path.cwd() / path,
            ]
            path = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
        if not path.exists():
            return []
        if path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8-sig") as f:
                return list(csv.DictReader(f))
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("tickets", data) if isinstance(data, dict) else data

    def normalize(self, raw: dict[str, Any]) -> CanonicalTicket:
        def field(key: str, default: Any = None) -> Any:
            mapped = self.mapping.get(key, key)
            return raw.get(mapped, raw.get(key, default))

        record_id = str(field("record_id") or field("source_record_id") or raw.get("id") or "")
        institution_text = str(field("institution_name") or raw.get("institution") or "")
        narrative = str(field("narrative") or raw.get("description") or institution_text)
        category = map_category(field("category"))
        date_received = parse_date(field("date_received"), self.date_formats)
        language = str(field("language") or detect_language(narrative))
        bureau = str(field("bureau") or "").upper()
        code_map = {
            "RB": "RB", "PGRC": "PGRC", "RO": "RO",
            "REGULATION": "RB", "GRIEVANCE": "PGRC",
            "APPROVAL": "APPROVAL", "EVC": "EVC",
            "DEPARTMENT OF HIGHER EDUCATION": "PGRC",
            "MINISTRY OF EDUCATION": "PGRC",
            "PUBLIC GRIEVANCE REDRESSAL CELL": "PGRC",
            "PGRC": "PGRC",
        }
        bureau_code = code_map.get(bureau, "RB")
        if self.name.startswith("cpgrams") and bureau_code not in {"PGRC", "RB"}:
            bureau_code = "PGRC"
        return CanonicalTicket(
            source_name=self.name,
            source_type=self.source_type,
            source_record_id=record_id,
            institution_text=institution_text,
            narrative=narrative,
            category=category,
            date_received=date_received,
            bureau_code=bureau_code,
            status="PENDING",
            language=language,
            complainant_hash=hash_identifier(str(field("complainant_identifier") or "") or None),
            raw=raw,
        )

    def healthcheck(self) -> dict[str, Any]:
        if self.mode == "file":
            return {"ok": True, "message": "File adapter ready", "source_type": self.source_type}
        try:
            with httpx.Client(timeout=3) as client:
                r = client.get(f"{self.base_url.rstrip('/')}/health")
                return {"ok": r.status_code < 500, "message": r.text[:200], "source_type": self.source_type}
        except Exception as e:
            ok = self.mode == "live" and bool(self._snapshot())
            return {"ok": ok, "message": f"Unreachable; {'snapshot available' if ok else str(e)}", "source_type": self.source_type}


class CssConnector(MappedHttpConnector):
    name = "css"
    mapping_file = "css_mapping.yaml"

    def __init__(self) -> None:
        super().__init__()
        self.mode = settings.source_mode_css
        self.source_type = "SIMULATOR" if self.mode == "simulator" else "LIVE_PUBLIC" if self.mode == "live" else "FILE_UPLOAD"

    @property
    def base_url(self) -> str:
        return settings.css_base_url


class CpgramsConnector(MappedHttpConnector):
    name = "cpgrams"
    mapping_file = "cpgrams_mapping.yaml"

    def __init__(self) -> None:
        super().__init__()
        self.mode = settings.source_mode_cpgrams
        self.source_type = "SIMULATOR" if self.mode == "simulator" else "LIVE_PUBLIC" if self.mode == "live" else "FILE_UPLOAD"

    @property
    def base_url(self) -> str:
        return settings.cpgrams_base_url


class CpgramsPublicStatsConnector(BaseConnector):
    name = "cpgrams_public_stats"
    source_type = "LIVE_PUBLIC"
    mode = "live"

    def fetch(self, since: datetime | None = None) -> list[dict[str, Any]]:
        if settings.cpgrams_public_stats_url:
            try:
                with httpx.Client(timeout=settings.connector_timeout_seconds, headers={"User-Agent": "AICTE-Dashboard/1.0 (read-only public stats)"}) as client:
                    r = client.get(settings.cpgrams_public_stats_url)
                    r.raise_for_status()
                    data = r.json()
                    return self._parse(data, snapshot=False)
            except Exception:
                pass
        return self._snapshot()

    def _snapshot(self) -> list[dict[str, Any]]:
        path = BACKEND_ROOT / "app" / "connectors" / "snapshots" / "cpgrams_public_stats.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return self._parse(data, snapshot=True)

    def _parse(self, data: Any, snapshot: bool) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if isinstance(data, dict):
            source = data.get("data", data.get("stats", [data]))
        else:
            source = data
        if not isinstance(source, list):
            source = [source]
        for i, item in enumerate(source):
            if not isinstance(item, dict):
                continue
            for key in ["department_wise", "state_wise", "stats"]:
                if key in item and isinstance(item[key], list):
                    for inner in item[key]:
                        if isinstance(inner, dict):
                            rows.append({
                                "dataset_key": key,
                                "period": inner.get("period") or item.get("period") or "latest",
                                "dimension": inner.get("department") or inner.get("state") or inner.get("dimension") or f"row-{i}",
                                "metrics": {k: v for k, v in inner.items() if k not in {"department", "state", "dimension"}},
                            })
                    break
            else:
                rows.append({
                    "dataset_key": item.get("dataset_key") or "summary",
                    "period": item.get("period") or "latest",
                    "dimension": item.get("dimension") or "all",
                    "metrics": item.get("metrics") or {k: v for k, v in item.items() if k not in {"dataset_key", "period", "dimension"}},
                })
        return [{"__snapshot": snapshot, **row} for row in rows]

    def normalize(self, raw: dict[str, Any]) -> CanonicalTicket:
        raise NotImplementedError("Public statistics are not complaint tickets")

    def healthcheck(self) -> dict[str, Any]:
        return {"ok": True, "message": "Public stats connector ready (snapshot fallback available)", "source_type": self.source_type}


class OgdConnector(BaseConnector):
    name = "ogd"
    source_type = "LIVE_PUBLIC"
    mode = "live"

    def fetch(self, since: datetime | None = None) -> list[dict[str, Any]]:
        if settings.ogd_ids and settings.ogd_api_key:
            rows = []
            try:
                for resource_id in settings.ogd_ids:
                    with httpx.Client(timeout=settings.connector_timeout_seconds, headers={"User-Agent": "AICTE-Dashboard/1.0 (read-only OGD)"}) as client:
                        r = client.get(f"{settings.ogd_base_url.rstrip('/')}/{resource_id}", params={"api-key": settings.ogd_api_key, "format": "json", "limit": 50})
                        r.raise_for_status()
                        data = r.json()
                        for rec in data.get("records", [])[:50]:
                            rows.append({"dataset_key": resource_id, "period": str(rec.get("year") or rec.get("period") or "latest"), "dimension": str(rec.get("state") or rec.get("dimension") or "all"), "metrics": rec, "__snapshot": False})
                    return rows
            except Exception:
                pass
        return self._snapshot()

    def _snapshot(self) -> list[dict[str, Any]]:
        path = BACKEND_ROOT / "app" / "connectors" / "snapshots" / "ogd_aicte.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return [{"__snapshot": True, **row} for row in data.get("records", data)]

    def normalize(self, raw: dict[str, Any]) -> CanonicalTicket:
        raise NotImplementedError("OGD datasets are aggregate statistics, not tickets")

    def healthcheck(self) -> dict[str, Any]:
        return {"ok": True, "message": f"OGD connector ready ({len(settings.ogd_ids)} configured resources; API key {'set' if settings.ogd_api_key else 'not set'})", "source_type": self.source_type}
