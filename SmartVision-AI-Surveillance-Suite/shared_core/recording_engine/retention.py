"""Retention and storage cleanup policies."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from time import time


@dataclass(slots=True)
class RetentionPolicy:
    root_dir: str = "data/recordings"
    max_age_days: int = 30
    low_priority_max_age_days: int = 7
    low_priority_threshold: float = 0.25
    min_free_gb: float = 5.0


def prune_old_events(policy: RetentionPolicy) -> list[Path]:
    """Delete old low-priority event clips and metadata sidecars."""

    root = Path(policy.root_dir)
    if not root.exists():
        return []
    now = time()
    deleted: list[Path] = []
    for metadata_path in root.rglob("*.json"):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        age_days = (now - float(metadata.get("start_ts", now))) / 86_400
        score = float(metadata.get("score", 1.0))
        max_age = policy.low_priority_max_age_days if score < policy.low_priority_threshold else policy.max_age_days
        if age_days < max_age:
            continue
        clip = Path(metadata.get("clip_path", ""))
        for candidate in (clip, metadata_path):
            if candidate.exists():
                candidate.unlink()
                deleted.append(candidate)
    return deleted
