from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from .. import models
from ..dependencies import get_current_user
from ..services.matching_benchmark import (
    DEFAULT_DEV_FRACTION,
    DEFAULT_SEED,
    evaluate_matching_benchmark,
)

router = APIRouter()
_CACHE: dict[tuple[int, float], dict] = {}


@router.get("/evaluation")
def matching_evaluation(
    seed: int = Query(default=DEFAULT_SEED),
    development_fraction: float = Query(default=DEFAULT_DEV_FRACTION, gt=0.0, lt=1.0),
    refresh: bool = Query(default=False),
    current: models.User = Depends(get_current_user),
):
    key = (seed, round(development_fraction, 4))
    if refresh or key not in _CACHE:
        _CACHE[key] = evaluate_matching_benchmark(seed=seed, development_fraction=development_fraction)
    return _CACHE[key]
