"""Portable physical-verification adapters for liquid-handling runs.

The simulator supplies modeled Rhodamine and CV gates. These adapters replace
those fixtures with venue data without changing the scientific controller:

* ``CsvVolumeGate`` evaluates a real standard curve and replicated dispenses.
* ``JsonCvCheckpoint`` imports a visual checkpoint with traceable evidence.

Both adapters fail closed on malformed, incomplete, or missing evidence. They
use only the Python standard library.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


class VerificationError(RuntimeError):
    """Physical evidence could not be evaluated safely."""


def file_sha256(path: str | Path) -> str:
    """Return the SHA-256 digest of one source evidence file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _first_field(fields: list[str], choices: tuple[str, ...]) -> str | None:
    normalized = {field.strip().lower(): field for field in fields}
    return next((normalized[name] for name in choices if name in normalized), None)


def _linear_fit(points: list[tuple[float, float]]) -> tuple[float, float, float]:
    if len(points) < 3:
        raise VerificationError("standard curve needs at least three points")
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    sxx = sum((value - mx) ** 2 for value in xs)
    if sxx <= 1e-12:
        raise VerificationError("standard curve needs distinct target volumes")
    slope = sum((x - mx) * (y - my) for x, y in points) / sxx
    if slope <= 0:
        raise VerificationError("standard curve slope must be positive")
    intercept = my - slope * mx
    residual = sum((y - (intercept + slope * x)) ** 2 for x, y in points)
    total = sum((y - my) ** 2 for y in ys)
    if total <= 1e-12:
        raise VerificationError("standard curve signal has zero variance")
    return slope, intercept, 1.0 - residual / total


class CsvVolumeGate:
    """Validate real replicated dispenses against a real standard curve.

    The CSV needs ``kind``, ``target_ul``, and ``rfu`` columns. ``kind`` is
    either ``standard`` for independently prepared standards or ``test`` for
    robot dispenses. At least three distinct standard volumes and three test
    replicates per tested volume are required by default.
    """

    provenance = "measured:volume-csv"

    def __init__(
        self,
        path: str | Path,
        *,
        min_r2: float = 0.995,
        max_accuracy_error_pct: float = 10.0,
        max_cv_pct: float = 10.0,
        min_replicates: int = 3,
    ):
        self.path = Path(path)
        self.min_r2 = float(min_r2)
        self.max_accuracy_error_pct = float(max_accuracy_error_pct)
        self.max_cv_pct = float(max_cv_pct)
        self.min_replicates = int(min_replicates)
        self.last_evidence: dict[str, Any] = {}
        if not 0.0 < self.min_r2 <= 1.0:
            raise VerificationError("min_r2 must be in (0, 1]")
        if self.max_accuracy_error_pct < 0 or self.max_cv_pct < 0:
            raise VerificationError("accuracy and CV limits must be non-negative")
        if self.min_replicates < 2:
            raise VerificationError("min_replicates must be at least two")

    def _rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            raise VerificationError(f"volume CSV does not exist: {self.path}")
        with self.path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames or []
            kind_field = _first_field(fields, ("kind", "type"))
            volume_field = _first_field(
                fields, ("target_ul", "commanded_ul", "volume_ul")
            )
            signal_field = _first_field(fields, ("rfu", "signal", "value"))
            well_field = _first_field(fields, ("well", "position"))
            if not kind_field or not volume_field or not signal_field:
                raise VerificationError(
                    "volume CSV needs kind, target_ul, and rfu columns"
                )
            rows: list[dict[str, Any]] = []
            for line_number, row in enumerate(reader, start=2):
                kind = str(row.get(kind_field, "")).strip().lower()
                if kind not in {"standard", "test"}:
                    raise VerificationError(
                        f"line {line_number}: kind must be standard or test"
                    )
                try:
                    target_ul = float(row[volume_field])
                    rfu = float(row[signal_field])
                except (KeyError, TypeError, ValueError) as exc:
                    raise VerificationError(
                        f"line {line_number}: target_ul and rfu must be numeric"
                    ) from exc
                if not math.isfinite(target_ul) or target_ul <= 0:
                    raise VerificationError(
                        f"line {line_number}: target_ul must be finite and positive"
                    )
                if not math.isfinite(rfu) or rfu < 0:
                    raise VerificationError(
                        f"line {line_number}: rfu must be finite and non-negative"
                    )
                rows.append({
                    "kind": kind,
                    "target_ul": target_ul,
                    "rfu": rfu,
                    "well": str(row.get(well_field, "")).strip().upper()
                    if well_field else "",
                })
        if not rows:
            raise VerificationError("volume CSV has no data rows")
        return rows

    def evaluate(self) -> dict[str, Any]:
        rows = self._rows()
        standards = [
            (row["target_ul"], row["rfu"])
            for row in rows if row["kind"] == "standard"
        ]
        if len({volume for volume, _ in standards}) < 3:
            raise VerificationError(
                "volume CSV needs at least three distinct standard volumes"
            )
        slope, intercept, r2 = _linear_fit(standards)

        grouped: dict[float, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            if row["kind"] == "test":
                grouped[row["target_ul"]].append(row)
        if not grouped:
            raise VerificationError("volume CSV needs replicated test dispenses")

        reasons: list[str] = []
        if r2 < self.min_r2:
            reasons.append(f"standard curve R2 {r2:.5f} is below {self.min_r2:.5f}")
        groups: list[dict[str, Any]] = []
        for target_ul in sorted(grouped):
            rows_for_target = grouped[target_ul]
            inferred = [(row["rfu"] - intercept) / slope for row in rows_for_target]
            n = len(inferred)
            mean_ul = sum(inferred) / n
            cv_pct: float | None = (
                statistics.stdev(inferred) / mean_ul * 100.0
                if n >= 2 and mean_ul > 0
                else None
            )
            accuracy_error_pct = (
                abs(mean_ul - target_ul) / target_ul * 100.0
                if target_ul > 0 else math.inf
            )
            group_reasons: list[str] = []
            if n < self.min_replicates:
                group_reasons.append(
                    f"needs {self.min_replicates} replicates, found {n}"
                )
            if mean_ul <= 0:
                group_reasons.append("inferred mean volume is not positive")
            if accuracy_error_pct > self.max_accuracy_error_pct:
                group_reasons.append(
                    f"accuracy error {accuracy_error_pct:.2f}% exceeds "
                    f"{self.max_accuracy_error_pct:.2f}%"
                )
            if cv_pct is None:
                group_reasons.append("CV is unavailable")
            elif cv_pct > self.max_cv_pct:
                group_reasons.append(
                    f"CV {cv_pct:.2f}% exceeds {self.max_cv_pct:.2f}%"
                )
            reasons.extend(f"{target_ul:g} uL: {reason}" for reason in group_reasons)
            groups.append({
                "target_ul": target_ul,
                "replicates": n,
                "mean_inferred_ul": round(mean_ul, 5),
                "accuracy_error_pct": round(accuracy_error_pct, 4),
                "cv_pct": round(cv_pct, 4) if cv_pct is not None else None,
                "passed": not group_reasons,
                "wells": [row["well"] for row in rows_for_target if row["well"]],
            })

        passed = not reasons
        self.last_evidence = {
            "path": str(self.path),
            "sha256": file_sha256(self.path),
            "standard_points": len(standards),
            "test_points": sum(len(values) for values in grouped.values()),
            "criteria": {
                "min_r2": self.min_r2,
                "max_accuracy_error_pct": self.max_accuracy_error_pct,
                "max_cv_pct": self.max_cv_pct,
                "min_replicates": self.min_replicates,
            },
        }
        return {
            "passed": passed,
            "r2": r2,
            "slope": slope,
            "intercept": intercept,
            "tier": "liquid_tested" if passed else "failed",
            "provenance": self.provenance,
            "groups": groups,
            "reasons": reasons,
            "evidence": self.last_evidence,
        }

    def __call__(self, _series=None, *, plan=None) -> dict[str, Any]:
        verdict = self.evaluate()
        if plan is not None:
            verdict["evidence"] = {
                **verdict["evidence"],
                "run_id": plan.run_id,
                "destination": plan.destination,
            }
        return verdict


class JsonCvCheckpoint:
    """Import a visual checkpoint produced by a camera, CV tool, or operator.

    Paths may contain ``{run_id}`` and ``{well}``, which the loop fills from the
    verified plan. Each JSON file must name the checkpoint, inspector, verdict,
    and note. It must also include either an image path or a trace ID.
    """

    provenance = "measured:cv-json"

    def __init__(
        self,
        path_pattern: str | Path,
        *,
        min_confidence: float = 0.80,
        require_evidence: bool = True,
    ):
        self.path_pattern = str(path_pattern)
        self.min_confidence = float(min_confidence)
        self.require_evidence = bool(require_evidence)
        self.last_evidence: dict[str, Any] = {}
        if not 0.0 <= self.min_confidence <= 1.0:
            raise VerificationError("min_confidence must be in [0, 1]")

    def path_for(self, plan=None) -> Path:
        needs_context = "{run_id}" in self.path_pattern or "{well}" in self.path_pattern
        if needs_context and plan is None:
            raise VerificationError(
                "CV checkpoint path pattern needs a liquid-handling plan"
            )
        return Path(self.path_pattern.format(
            run_id=plan.run_id if plan is not None else 0,
            well=plan.destination if plan is not None else "",
        ))

    def evaluate(self, plan=None) -> dict[str, Any]:
        path = self.path_for(plan)
        if not path.exists():
            raise VerificationError(f"CV checkpoint does not exist: {path}")
        try:
            payload = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise VerificationError(f"CV checkpoint is not valid JSON: {path}") from exc
        if not isinstance(payload, dict):
            raise VerificationError("CV checkpoint must be a JSON object")

        checkpoint = str(payload.get("checkpoint", "")).strip()
        inspector = str(payload.get("inspector", "")).strip()
        note = str(payload.get("note", "")).strip()
        passed_value = payload.get("passed")
        if not checkpoint or not inspector or not note:
            raise VerificationError(
                "CV checkpoint needs checkpoint, inspector, and note fields"
            )
        if not isinstance(passed_value, bool):
            raise VerificationError("CV checkpoint passed field must be boolean")

        confidence_value = payload.get("confidence")
        confidence: float | None = None
        if confidence_value is not None:
            try:
                confidence = float(confidence_value)
            except (TypeError, ValueError) as exc:
                raise VerificationError("CV checkpoint confidence must be numeric") from exc
            if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
                raise VerificationError("CV checkpoint confidence must be in [0, 1]")

        image_value = str(payload.get("image", "")).strip()
        trace_id = str(payload.get("trace_id", "")).strip()
        resolved_image: Path | None = None
        if image_value:
            image_path = Path(image_value)
            resolved_image = image_path if image_path.is_absolute() else path.parent / image_path
            if not resolved_image.exists():
                raise VerificationError(
                    f"CV checkpoint image does not exist: {resolved_image}"
                )
        if self.require_evidence and resolved_image is None and not trace_id:
            raise VerificationError(
                "CV checkpoint needs an existing image or a trace_id"
            )

        raw_reasons = payload.get("reasons", [])
        if not isinstance(raw_reasons, list) or not all(
            isinstance(reason, str) for reason in raw_reasons
        ):
            raise VerificationError("CV checkpoint reasons must be a list of strings")
        reasons = list(raw_reasons)
        if not passed_value:
            reasons.append("external checkpoint reported failure")
        if confidence is not None and confidence < self.min_confidence:
            reasons.append(
                f"confidence {confidence:.3f} is below {self.min_confidence:.3f}"
            )
        passed = passed_value and not reasons
        self.last_evidence = {
            "path": str(path),
            "sha256": file_sha256(path),
            "image": str(resolved_image) if resolved_image else None,
            "image_sha256": (
                file_sha256(resolved_image) if resolved_image else None
            ),
            "trace_id": trace_id or None,
            "inspector": inspector,
        }
        return {
            "passed": passed,
            "note": note,
            "checkpoint": checkpoint,
            "inspector": inspector,
            "confidence": confidence,
            "provenance": self.provenance,
            "reasons": reasons,
            "evidence": self.last_evidence,
        }

    def __call__(self, fault: bool = False, *, plan=None) -> dict[str, Any]:
        if fault:
            return {
                "passed": False,
                "note": "fault requested",
                "checkpoint": "fault-injection",
                "provenance": self.provenance,
                "reasons": ["fault requested"],
                "evidence": {},
            }
        return self.evaluate(plan=plan)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="evaluate bay-hack physical volume and CV evidence"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    volume = subparsers.add_parser(
        "volume-csv", help="evaluate standards and replicated robot dispenses"
    )
    volume.add_argument("path")
    volume.add_argument("--min-r2", type=float, default=0.995)
    volume.add_argument("--max-accuracy-error-pct", type=float, default=10.0)
    volume.add_argument("--max-cv-pct", type=float, default=10.0)
    volume.add_argument("--min-replicates", type=int, default=3)

    visual = subparsers.add_parser(
        "cv-json", help="evaluate one external visual checkpoint"
    )
    visual.add_argument("path")
    visual.add_argument("--min-confidence", type=float, default=0.80)
    visual.add_argument("--allow-no-evidence", action="store_true")

    args = parser.parse_args()
    try:
        if args.command == "volume-csv":
            verdict = CsvVolumeGate(
                args.path,
                min_r2=args.min_r2,
                max_accuracy_error_pct=args.max_accuracy_error_pct,
                max_cv_pct=args.max_cv_pct,
                min_replicates=args.min_replicates,
            ).evaluate()
        else:
            verdict = JsonCvCheckpoint(
                args.path,
                min_confidence=args.min_confidence,
                require_evidence=not args.allow_no_evidence,
            ).evaluate()
    except VerificationError as exc:
        parser.exit(2, f"verification failed closed: {exc}\n")
    print(json.dumps(verdict, indent=2))
    if not verdict["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
