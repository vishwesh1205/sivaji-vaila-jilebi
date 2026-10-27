import hashlib
import json
from typing import Any


def compute_hash(prev_hash: str, payload: dict[str, Any]) -> str:
    data = json.dumps({"prev": prev_hash, "payload": payload}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
