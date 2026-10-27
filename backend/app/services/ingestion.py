import hashlib
import json
import re
import threading
from datetime import datetime, timedelta
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..connectors import CanonicalTicket, CpgramsConnector, CpgramsPublicStatsConnector, CssConnector, OgdConnector
from ..events import bus
from ..hash_chain import compute_hash
from ..services.overlap import OverlapService
from ..services.resolution import InstitutionResolver


PUBLIC_SOURCE_NAMES = {"ogd", "cpgrams_public_stats"}
_SYNC_LOCK = threading.Lock()


def mask_url(url: str | None) -> str | None:
    if not url:
        return None
    if "?" in url:
        return url.split("?")[0] + "?***"
    return url


def get_connector(name: str):
    if name == "css":
        return CssConnector()
    if name == "cpgrams":
        return CpgramsConnector()
    if name == "ogd":
        return OgdConnector()
    if name == "cpgrams_public_stats":
        return CpgramsPublicStatsConnector()
    raise ValueError(f"Unknown connector: {name}")


def source_definition(name: str) -> dict[str, Any]:
    if name == "css":
        c = CssConnector()
        return {"name": "css", "kind": "ticket_extract", "mode": c.mode, "base_url_masked": mask_url(c.base_url), "interval_seconds": settings.css_sync_interval, "source_type": c.source_type}
    if name == "cpgrams":
        c = CpgramsConnector()
        return {"name": "cpgrams", "kind": "ticket_extract", "mode": c.mode, "base_url_masked": mask_url(c.base_url), "interval_seconds": settings.cpgrams_sync_interval, "source_type": c.source_type}
    if name == "ogd":
        return {"name": "ogd", "kind": "public_stats", "mode": "live", "base_url_masked": mask_url(settings.ogd_base_url), "interval_seconds": settings.public_stats_interval, "source_type": "LIVE_PUBLIC"}
    if name == "cpgrams_public_stats":
        return {"name": "cpgrams_public_stats", "kind": "public_stats", "mode": "live", "base_url_masked": mask_url(settings.cpgrams_public_stats_url) or "bundled snapshot fallback", "interval_seconds": settings.public_stats_interval, "source_type": "LIVE_PUBLIC"}
    if name == "institution_master":
        return {"name": "institution_master", "kind": "institution_master", "mode": "file" if settings.institution_master_url == "" else "live", "base_url_masked": mask_url(settings.institution_master_url) or "file upload", "interval_seconds": settings.institution_master_interval, "source_type": "FILE_UPLOAD"}
    raise ValueError(name)


def ensure_data_sources(db: Session) -> None:
    for name in ["css", "cpgrams", "ogd", "cpgrams_public_stats", "institution_master"]:
        try:
            d = source_definition(name)
        except Exception:
            continue
        ds = db.scalar(select(models.DataSource).where(models.DataSource.name == name))
        if not ds:
            ds = models.DataSource(**d)
            db.add(ds)
        else:
            ds.kind = d["kind"]
            ds.mode = d["mode"]
            ds.base_url_masked = d["base_url_masked"]
            ds.interval_seconds = d["interval_seconds"]
            ds.source_type = d["source_type"]
    db.commit()


def _translate_stub(text: str, language: str) -> str:
    if language.startswith("en") or not settings.enable_translation:
        return text
    return f"[MACHINE TRANSLATION – stub; not authoritative] {text}"


def _similarity(a: str, b: str) -> float:
    try:
        vec = TfidfVectorizer(max_features=1500, stop_words="english")
        X = vec.fit_transform([a, b])
        return float(cosine_similarity(X)[0][1])
    except Exception:
        return 0.0


def detect_cross_channel_duplicates(db: Session, case: models.Case, actor_id: int | None = None) -> list[models.CaseLink]:
    if not case.complainant_hash or not case.institution_id:
        return []
    window_start = case.date_received - timedelta(days=settings.cross_channel_window_days)
    window_end = case.date_received + timedelta(days=settings.cross_channel_window_days)
    others = db.scalars(
        select(models.Case).where(
            models.Case.id != case.id,
            models.Case.complainant_hash == case.complainant_hash,
            models.Case.institution_id == case.institution_id,
            models.Case.date_received >= window_start,
            models.Case.date_received <= window_end,
        )
    ).all()
    created_links = []
    for other in others:
        if other.source_channel == case.source_channel:
            continue
        score = _similarity(case.narrative_translated or case.narrative, other.narrative_translated or other.narrative)
        if score < settings.near_duplicate_threshold:
            continue
        pair = (min(case.id, other.id), max(case.id, other.id))
        exists = db.scalar(
            select(models.CaseLink).where(
                models.CaseLink.case_a_id == pair[0],
                models.CaseLink.case_b_id == pair[1],
                models.CaseLink.link_type == models.LinkType.CROSS_CHANNEL_DUPLICATE,
            )
        )
        if exists:
            continue
        link = models.CaseLink(case_a_id=pair[0], case_b_id=pair[1], link_type=models.LinkType.CROSS_CHANNEL_DUPLICATE, similarity_score=round(score, 4), created_by=actor_id)
        db.add(link)
        created_links.append(link)
        bus.publish("DUPLICATE_DETECTED", {
            "message": f"Possible same complaint via {case.source_channel.value} and {other.source_channel.value}",
            "case_id": case.case_id,
            "other_case_id": other.case_id,
            "similarity": round(score, 3),
            "source_type": case.source_type,
            "source_name": case.source_name,
        })
    if created_links:
        db.commit()
    return created_links


class SyncService:
    def __init__(self, db: Session):
        self.db = db

    def sync(self, name: str, triggered_by: str = "scheduler") -> models.SyncRun:
        with _SYNC_LOCK:
            return self._sync_impl(name, triggered_by)

    def _sync_impl(self, name: str, triggered_by: str = "scheduler") -> models.SyncRun:
        ds = self.db.scalar(select(models.DataSource).where(models.DataSource.name == name))
        if not ds:
            raise ValueError("Source not found")
        run = models.SyncRun(source=name, started_at=datetime.utcnow(), status="RUNNING")
        self.db.add(run)
        self.db.commit()
        started = datetime.utcnow()
        try:
            connector = get_connector(name)
            if name in PUBLIC_SOURCE_NAMES:
                rows = connector.fetch()
                for row in rows:
                    is_snapshot = bool(row.pop("__snapshot", False))
                    stat = models.PublicStat(
                        source=name,
                        dataset_key=str(row.get("dataset_key") or "summary"),
                        period=str(row.get("period") or "latest"),
                        dimension=str(row.get("dimension") or "all"),
                        metrics_json=row.get("metrics") or row,
                        is_snapshot=is_snapshot,
                    )
                    self.db.add(stat)
                run.fetched = len(rows)
                run.created = len(rows)
            else:
                since = ds.last_success_at
                raws = connector.fetch(since)
                run.fetched = len(raws)
                resolver = InstitutionResolver(self.db)
                for raw in raws:
                    try:
                        canonical = connector.normalize(raw)
                        self._ingest_one(canonical, run, resolver, triggered_by)
                    except Exception as exc:
                        run.errors_json = list(run.errors_json or []) + [str(exc)[:300]]
                self.db.commit()
                self._refresh_overlap_links()
            latency = (datetime.utcnow() - started).total_seconds() * 1000
            run.latency_ms = round(latency, 1)
            run.status = "PARTIAL" if run.errors_json else "SUCCESS"
            run.finished_at = datetime.utcnow()
            ds.last_status = run.status
            ds.last_success_at = datetime.utcnow()
            ds.last_error = "; ".join(run.errors_json) if run.errors_json else None
            ds.records_total = (ds.records_total or 0) + run.created
            ds.latency_ms_avg = round(((ds.latency_ms_avg or 0) * max(1, (ds.records_total or 0) - run.created) + latency) / max(1, ds.records_total or 1), 1)
            self.db.commit()
            bus.publish("SYNC_COMPLETE", {
                "message": f"{name.upper()} sync complete: {run.created} created, {run.duplicates_skipped} duplicates",
                "source": name,
                "source_type": ds.source_type,
                "source_name": name,
                "run_id": run.id,
                "fetched": run.fetched,
                "created": run.created,
            })
            return run
        except Exception as exc:
            self.db.rollback()
            run = self.db.get(models.SyncRun, run.id)
            if run:
                run.status = "FAILED"
                run.finished_at = datetime.utcnow()
                run.errors_json = [str(exc)[:500]]
            ds = self.db.scalar(select(models.DataSource).where(models.DataSource.name == name))
            if ds:
                ds.last_status = "FAILED"
                ds.last_error = str(exc)[:500]
            self.db.commit()
            bus.publish("SYNC_FAILED", {"message": f"{name.upper()} sync failed", "source": name, "source_type": ds.source_type if ds else "SIMULATOR", "source_name": name})
            return run

    def _ingest_one(self, t: CanonicalTicket, run: models.SyncRun, resolver: InstitutionResolver, triggered_by: str) -> None:
        if not t.source_record_id:
            raise ValueError("Missing source_record_id")
        dupe = self.db.scalar(select(models.Case).where(models.Case.source_name == t.source_name, models.Case.source_record_id == t.source_record_id))
        if dupe:
            run.duplicates_skipped += 1
            return
        idem = f"source:{t.source_name}:{t.source_record_id}"
        if self.db.scalar(select(models.Case).where(models.Case.idempotency_key == idem)):
            run.duplicates_skipped += 1
            return
        payload_hash = hashlib.sha256(json.dumps(t.raw, sort_keys=True, default=str).encode()).hexdigest()
        rp = models.RawPayload(source=t.source_name, source_record_id=t.source_record_id, payload_json=t.raw, payload_sha256=payload_hash, source_type=t.source_type, fetched_at=datetime.utcnow())
        self.db.add(rp)
        self.db.flush()
        translated = _translate_stub(t.narrative, t.language)
        inst, conf, candidates = resolver.resolve(t.institution_text, {})
        resolution_status = models.ResolutionStatus.RESOLVED if inst else models.ResolutionStatus.NEEDS_REVIEW if candidates else models.ResolutionStatus.UNRESOLVED
        if resolution_status == models.ResolutionStatus.RESOLVED and conf >= settings.auto_link_threshold:
            run.auto_linked += 1
        elif resolution_status == models.ResolutionStatus.NEEDS_REVIEW:
            run.sent_to_review += 1
        else:
            run.unresolved += 1
        bureau = self.db.scalar(select(models.Bureau).where(models.Bureau.code == t.bureau_code)) or self.db.scalar(select(models.Bureau))
        digits = re.findall(r"\d+", t.source_record_id)
        suffix = (digits[-1] if digits else re.sub(r"[^A-Za-z0-9]", "", t.source_record_id))[-6:]
        case = models.Case(
            case_id=f"{t.bureau_code}-{datetime.utcnow().strftime('%Y')}-{suffix or '000000'}",
            source_channel=models.SourceChannel(t.raw.get("source_channel") or ("CSS" if t.source_name == "css" else "CPGRAMS")),
            institution_id=inst.id if inst else None,
            raw_institution_text=t.institution_text,
            category=models.CaseCategory(t.category),
            narrative=translated,
            status=models.CaseStatus.PENDING,
            bureau_id=bureau.id if bureau else None,
            date_received=t.date_received,
            last_action_at=datetime.utcnow(),
            last_action_text="Ingested by connector",
            resolution_status=resolution_status,
            match_confidence=conf,
            idempotency_key=idem,
            source_type=t.source_type,
            is_synthetic=t.source_type == "SIMULATOR",
            source_name=t.source_name,
            source_record_id=t.source_record_id,
            raw_payload_id=rp.id,
            complainant_hash=t.complainant_hash,
            language=t.language,
            narrative_original=t.narrative,
            narrative_translated=translated,
        )
        if not case.bureau_id:
            raise ValueError("No bureau configured")
        # ensure unique human-readable case id
        if self.db.scalar(select(models.Case).where(models.Case.case_id == case.case_id)):
            case.case_id = f"{case.case_id}-{self.db.scalar(select(models.Case.id).order_by(models.Case.id.desc())) or 0}"
        self.db.add(case)
        self.db.flush()
        prev = "0" * 64
        action = models.CaseAction(
            case_id=case.id,
            bureau_id=case.bureau_id,
            action_type=models.ActionType.CREATED,
            remarks=f"Ingested from {t.source_name} ({t.source_type})",
            prev_hash=prev,
            hash=compute_hash(prev, {"action": "INGESTED", "source": t.source_name, "record": t.source_record_id, "payload_sha256": payload_hash}),
        )
        self.db.add(action)
        if resolution_status == models.ResolutionStatus.NEEDS_REVIEW and candidates:
            cand_out = [{"institution_id": c.institution.id, "name": c.institution.name, "aicte_permanent_id": c.institution.aicte_permanent_id, "score": c.score, "reasons": c.reasons} for c in candidates]
            self.db.add(models.ReviewQueue(case_id=case.id, candidate_institutions=cand_out, status=models.ReviewStatus.OPEN))
        self.db.commit()
        self.db.refresh(case)
        if inst:
            try:
                OverlapService(self.db).detect_for_case(case, None)
            except Exception:
                pass
        try:
            detect_cross_channel_duplicates(self.db, case)
        except Exception:
            pass
        run.created += 1
        bus.publish("TICKET_INGESTED", {
            "message": f"{t.source_name.upper()} ticket {t.source_record_id} received → {'matched to ' + inst.name if inst else 'needs review'}" + (f" ({conf:.2f}) → linked" if inst else ""),
            "source": t.source_name,
            "source_type": t.source_type,
            "source_name": t.source_name,
            "case_id": case.case_id,
            "database_id": case.id,
            "institution": inst.name if inst else None,
            "confidence": conf,
            "resolution": resolution_status.value,
        })
        if inst:
            active = self.db.scalars(select(models.Case).where(models.Case.institution_id == inst.id, models.Case.status.in_([models.CaseStatus.PENDING, models.CaseStatus.UNDER_PROCESS, models.CaseStatus.ESCALATED]))).all()
            if len({c.bureau_id for c in active}) >= 2:
                bus.publish("OVERLAP_DETECTED", {
                    "message": f"OVERLAP detected for {inst.name}: {' + '.join(sorted({c.bureau.code for c in active if c.bureau}))}",
                    "source_type": t.source_type,
                    "source_name": t.source_name,
                    "institution_id": inst.id,
                    "case_id": case.case_id,
                })

    def _refresh_overlap_links(self):
        # Existing overlap detection is invoked per newly-resolved case. Keep this hook for retries.
        pass
