from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class Evaluation:
    model_id: str
    model_revision: str
    taskset_id: str
    taskset_revision: str
    records: tuple[dict[str, Any], ...]
    path: str

    @property
    def scores(self) -> dict[str, float]:
        return {record["id"]: record["score"] for record in self.records}

    @property
    def passed(self) -> dict[str, bool]:
        return {record["id"]: record["score"] >= 1.0 for record in self.records}

    @property
    def mean_score(self) -> float:
        return sum(self.scores.values()) / len(self.records)

    @property
    def pass_rate(self) -> float:
        return sum(self.passed.values()) / len(self.records)


def _score(record: dict[str, Any]) -> float:
    values = [record.get(name) for name in ("score", "reward") if record.get(name) is not None]
    if values:
        value = values[0]
    elif isinstance(record.get("passed"), bool):
        value = float(record["passed"])
    else:
        raise ValueError("Each evaluation record needs score, reward or boolean passed")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Evaluation scores must be finite numbers")
    if not 0.0 <= float(value) <= 1.0:
        raise ValueError("Evaluation scores must be between zero and one")
    return float(value)


def _records(document: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    records = document.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("Evaluation document needs a nonempty records list")
    normalized = []
    ids = set()
    for raw in records:
        if not isinstance(raw, dict) or not isinstance(raw.get("id"), str) or not raw["id"]:
            raise ValueError("Every evaluation record needs a nonempty id")
        if raw["id"] in ids:
            raise ValueError(f"Duplicate evaluation id: {raw['id']}")
        ids.add(raw["id"])
        score = _score(raw)
        normalized.append({"id": raw["id"], "score": score,
                           "source_id": raw.get("source_id"),
                           "metadata": raw.get("metadata", {})})
    return tuple(normalized)


def load(path: Path) -> Evaluation:
    if not path.is_file():
        raise ValueError(f"Evaluation file is missing: {path}")
    document = json.loads(path.read_text())
    if not isinstance(document, dict):
        raise ValueError("Evaluation document must be an object")
    required = ("model_id", "model_revision", "taskset_id", "taskset_revision")
    for key in required:
        if not isinstance(document.get(key), str) or not document[key]:
            raise ValueError(f"Evaluation document requires {key}")
    return Evaluation(document["model_id"], document["model_revision"], document["taskset_id"],
                      document["taskset_revision"], _records(document), str(path))


def validate(evaluation: Evaluation) -> dict[str, Any]:
    return {"passed": True, "model_id": evaluation.model_id,
            "model_revision": evaluation.model_revision, "taskset_id": evaluation.taskset_id,
            "taskset_revision": evaluation.taskset_revision, "records": len(evaluation.records),
            "mean_score": evaluation.mean_score, "pass_rate": evaluation.pass_rate,
            "record_ids_sha256": fingerprint(sorted(evaluation.scores)),
            "source_ids": len({r["source_id"] for r in evaluation.records if r["source_id"] is not None}),
            "scope": "Recomputed per-item evaluation integrity and descriptive metrics; no model execution"}


def compare(baseline: Evaluation, candidate: Evaluation, *, minimum_relative_improvement: float = 0.0) -> dict[str, Any]:
    reasons = []
    if baseline.taskset_id != candidate.taskset_id:
        reasons.append("Taskset IDs differ")
    if baseline.taskset_revision != candidate.taskset_revision:
        reasons.append("Taskset revisions differ")
    if baseline.scores.keys() != candidate.scores.keys():
        reasons.append("Per-item evaluation IDs differ")
    if baseline.model_id == candidate.model_id and baseline.model_revision == candidate.model_revision:
        reasons.append("Baseline and candidate model revisions are identical")
    if isinstance(minimum_relative_improvement, bool) or not math.isfinite(minimum_relative_improvement) or minimum_relative_improvement < 0:
        raise ValueError("Minimum relative improvement must be finite and nonnegative")
    common = sorted(baseline.scores.keys() & candidate.scores.keys())
    deltas = [{"id": key, "baseline": baseline.scores[key], "candidate": candidate.scores[key],
               "delta": candidate.scores[key] - baseline.scores[key]}
              for key in common]
    mean_delta = candidate.mean_score - baseline.mean_score if common else float("nan")
    relative = mean_delta / abs(baseline.mean_score) if common and baseline.mean_score != 0 else None
    regressions = [key for key in common if baseline.passed[key] and not candidate.passed[key]]
    improvements = [key for key in common if not baseline.passed[key] and candidate.passed[key]]
    comparable = not reasons and bool(common)
    meets = comparable and relative is not None and relative >= minimum_relative_improvement
    return {"comparable": comparable, "reasons": reasons, "baseline": validate(baseline),
            "candidate": validate(candidate), "paired_records": len(common), "deltas": deltas,
            "mean_delta": mean_delta if common else None, "relative_improvement": relative,
            "regression_ids": regressions, "improvement_ids": improvements,
            "minimum_relative_improvement": minimum_relative_improvement,
            "meets_declared_threshold": meets,
            "scope": "Paired descriptive comparison under the declared taskset; no significance test or automatic release"}
