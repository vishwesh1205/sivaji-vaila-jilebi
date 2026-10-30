import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..services.resolution import normalize_name


MAPPING_PATH = Path(__file__).resolve().parents[2] / "config" / "institution_master_mapping.yaml"


class InstitutionMasterImporter:
    def __init__(self, db: Session):
        self.db = db
        self.mapping = yaml.safe_load(MAPPING_PATH.read_text()) if MAPPING_PATH.exists() else {}

    def _field(self, row: dict[str, Any], key: str, default: str = "") -> Any:
        mapped = self.mapping.get(key, key)
        return row.get(mapped, row.get(key, default))

    def import_bytes(self, content: bytes, filename: str, source_type: str = "FILE_UPLOAD") -> dict[str, int]:
        rows = self._parse(content, filename)
        created = 0
        updated = 0
        skipped = 0
        for row in rows:
            aid = str(self._field(row, "aicte_permanent_id")).strip()
            name = str(self._field(row, "name")).strip()
            if not aid or aid.lower() in {"nan", "none"} or not name:
                skipped += 1
                continue
            inst = self.db.scalar(select(models.Institution).where(models.Institution.aicte_permanent_id == aid))
            aliases_raw = str(self._field(row, "aliases") or "")
            aliases = [a.strip() for a in aliases_raw.replace("|", ";").split(";") if a.strip()]
            programmes_raw = str(self._field(row, "programme_mix") or "")
            programmes = [p.strip() for p in programmes_raw.replace("|", ";").split(";") if p.strip()]
            resolution_raw = str(self._field(row, "grc_first_resolution_days") or "").strip()
            try:
                grc_first_resolution_days = int(float(resolution_raw)) if resolution_raw and resolution_raw.lower() not in {"nan", "none", "unknown", "na", "n/a"} else None
                if grc_first_resolution_days is not None and grc_first_resolution_days < 0:
                    grc_first_resolution_days = None
            except (TypeError, ValueError):
                grc_first_resolution_days = None
            values = {
                "name": name,
                "normalized_name": normalize_name(name),
                "address": str(self._field(row, "address") or ""),
                "city": str(self._field(row, "city") or ""),
                "state": str(self._field(row, "state") or ""),
                "region": str(self._field(row, "region") or ""),
                "university_affiliation": str(self._field(row, "university_affiliation") or "") or None,
                "approval_status": str(self._field(row, "approval_status") or "Approved"),
                "programme_mix": programmes,
                "aliases": aliases,
                "grc_first_resolution_days": grc_first_resolution_days,
                "is_synthetic": False,
                "source_type": source_type,
            }
            if inst:
                for k, v in values.items():
                    setattr(inst, k, v)
                updated += 1
            else:
                inst = models.Institution(aicte_permanent_id=aid, **values)
                self.db.add(inst)
                created += 1
            self.db.flush()
            for alias in aliases:
                exists = self.db.scalar(select(models.InstitutionAlias).where(models.InstitutionAlias.institution_id == inst.id, models.InstitutionAlias.alias == alias))
                if not exists:
                    self.db.add(models.InstitutionAlias(institution_id=inst.id, alias=alias, source="import"))
        self.db.commit()
        return {"created": created, "updated": updated, "skipped": skipped, "total": len(rows)}

    def _parse(self, content: bytes, filename: str) -> list[dict[str, Any]]:
        if filename.lower().endswith(".xlsx"):
            import openpyxl

            wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return []
            headers = [str(h) if h is not None else "" for h in rows[0]]
            return [dict(zip(headers, r)) for r in rows[1:]]
        text = content.decode("utf-8-sig", errors="replace")
        return list(csv.DictReader(io.StringIO(text)))

    def import_from_url(self) -> dict[str, int]:
        if not settings.institution_master_url:
            raise ValueError("INSTITUTION_MASTER_URL is not configured")
        with httpx.Client(timeout=settings.connector_timeout_seconds, headers={"User-Agent": "AICTE-Dashboard/1.0 (read-only master import)"}) as client:
            r = client.get(settings.institution_master_url)
            r.raise_for_status()
            filename = settings.institution_master_url.split("?")[0].split("/")[-1] or "master.csv"
            return self.import_bytes(r.content, filename, source_type="LIVE_PUBLIC")
