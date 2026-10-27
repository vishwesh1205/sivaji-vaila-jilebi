import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..config import settings


SOUTHERN_REGIONS = {"Chennai", "Hyderabad", "Bengaluru", "Kerala", "Tamil Nadu", "Telangana", "Karnataka", "Andhra Pradesh"}
REGION_GROUPS = {
    "Chennai": "Southern", "Hyderabad": "Southern", "Bengaluru": "Southern",
    "Mumbai": "Western", "Pune": "Western", "Ahmedabad": "Western",
    "Kolkata": "Eastern", "Guwahati": "North Eastern",
    "Bhopal": "Central", "Kanpur": "Central",
    "Chandigarh": "Northern", "Jaipur": "Northern", "Delhi": "Northern",
}


def detect_spikes(current_count: int, baseline_weekly: list[int], min_count: int | None = None, z_threshold: float | None = None) -> dict[str, Any] | None:
    min_count = settings.emerging_min_count if min_count is None else min_count
    z_threshold = settings.emerging_z_threshold if z_threshold is None else z_threshold
    if current_count < min_count:
        return None
    if not baseline_weekly:
        baseline_weekly = [0]
    mean = sum(baseline_weekly) / len(baseline_weekly)
    variance = sum((x - mean) ** 2 for x in baseline_weekly) / len(baseline_weekly)
    std = math.sqrt(variance) or math.sqrt(max(mean, 1))
    z = (current_count - mean) / std
    if z <= z_threshold:
        return None
    ratio = current_count / mean if mean > 0 else float(current_count)
    return {"z_score": round(z, 2), "baseline_mean": round(mean, 2), "ratio": round(ratio, 2)}


def compute_emerging_issues(db: Session, weeks: int = 8) -> list[dict[str, Any]]:
    now = datetime.utcnow()
    current_start = now - timedelta(days=7)
    baseline_start = current_start - timedelta(weeks=weeks)
    cases = db.scalars(select(models.Case).where(models.Case.date_received >= baseline_start)).all()
    current: dict[tuple[str, str], int] = defaultdict(int)
    baseline: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0] * weeks)
    for c in cases:
        region = c.institution.region if c.institution else "Unknown"
        region_group = REGION_GROUPS.get(region, region)
        key = (c.category.value, region_group)
        if c.date_received >= current_start:
            current[key] += 1
        else:
            idx = min(weeks - 1, int((c.date_received - baseline_start).days / 7))
            baseline[key][idx] += 1
    out = []
    for key, count in current.items():
        spike = detect_spikes(count, baseline[key])
        if not spike:
            continue
        category, region = key
        # weekly sparkline for the last 9 weeks (8 baseline + current)
        spark = baseline[key][-8:] + [count]
        out.append({
            "category": category,
            "region": region,
            "current_week_count": count,
            "baseline_weekly_mean": spike["baseline_mean"],
            "z_score": spike["z_score"],
            "ratio": spike["ratio"],
            "sparkline": spark,
            "message": f"{category.replace('_', ' ').title()} complaints in {region} region up {spike['ratio']:.1f}x vs baseline",
        })
    out.sort(key=lambda r: r["z_score"], reverse=True)
    return out
