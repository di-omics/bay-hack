"""Track A scientific loop for a two-round TEM-1 inhibitor search.

The event-specific workflow is intentionally separate from the generic fallback
in ``bayhack.loop``. It provides the pieces the announced challenge requires:

* a compound library with optional numeric features,
* balanced controls and replicated candidate wells,
* kinetic plate-reader analysis,
* assay-quality gating with Z-prime,
* observed inhibition with replicate uncertainty,
* a model-driven round-2 confirmation plan.

No venue reagent, wavelength, concentration, volume, timing, or Zeon API is
guessed. Those fields remain explicit in ``TEM1AssaySpec`` and physical execution
is refused until the organizer-supplied protocol is confirmed.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .assay import ROWS, is_well_name


TRACK_NAME = "Track A: Close the Loop"
TARGET_NAME = "TEM-1 beta-lactamase"
CONTROL_WELLS = {
    "activity_control": ("A1", "A12", "H1"),
    "inhibition_control": ("A2", "A11", "H2"),
    "blank": ("A3", "A10", "H3"),
}
ALL_WELLS = tuple(
    f"{row}{column}"
    for column in range(1, 13)
    for row in ROWS
)


class TEM1Error(RuntimeError):
    """A TEM-1 plan or evidence file failed closed."""


class AssayQCError(TEM1Error):
    """Control separation was not good enough to update the model."""


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class TEM1AssaySpec:
    """Scientific criteria plus organizer-supplied physical protocol fields."""

    target: str = TARGET_NAME
    readout_mode: str = "kinetic_plate_reader"
    expression_confirmation_method: str | None = None
    expression_min_fold_over_background: float | None = None
    expression_max_cv_pct: float = 20.0
    substrate_name: str | None = None
    read_wavelength_nm: float | None = None
    reaction_volume_ul: float | None = None
    assay_mix_volume_ul: float | None = None
    compound_volume_ul: float | None = None
    substrate_volume_ul: float | None = None
    preincubation_s: float | None = None
    protocol_confirmed_by_organizer: bool = False
    candidate_replicates: int = 2
    control_replicates: int = 3
    z_prime_min: float = 0.50
    hit_threshold_pct: float = 30.0
    max_replicate_sd_pct: float = 20.0
    round2_dose_factors: tuple[float, ...] = (0.25, 0.5, 1.0, 2.0)

    def verify(self) -> dict[str, Any]:
        reasons: list[str] = []
        if self.candidate_replicates < 2:
            reasons.append("candidate_replicates must be at least two")
        if self.control_replicates < 2:
            reasons.append("control_replicates must be at least two")
        if not -10.0 <= self.z_prime_min <= 1.0:
            reasons.append("z_prime_min must be within [-10, 1]")
        if not 0.0 <= self.hit_threshold_pct <= 100.0:
            reasons.append("hit_threshold_pct must be within [0, 100]")
        if self.max_replicate_sd_pct < 0:
            reasons.append("max_replicate_sd_pct must be non-negative")
        if self.expression_max_cv_pct < 0:
            reasons.append("expression_max_cv_pct must be non-negative")
        if self.expression_min_fold_over_background is not None and (
            not math.isfinite(self.expression_min_fold_over_background)
            or self.expression_min_fold_over_background <= 1.0
        ):
            reasons.append("expression fold threshold must be finite and above one")
        if not self.round2_dose_factors or any(
            not math.isfinite(value) or value <= 0
            for value in self.round2_dose_factors
        ):
            reasons.append("round2 dose factors must be finite and positive")
        volumes = (
            self.reaction_volume_ul,
            self.assay_mix_volume_ul,
            self.compound_volume_ul,
            self.substrate_volume_ul,
        )
        known_volumes = [value for value in volumes if value is not None]
        if any(not math.isfinite(value) or value <= 0 for value in known_volumes):
            reasons.append("confirmed protocol volumes must be finite and positive")
        if all(value is not None for value in volumes):
            component_total = (
                float(self.assay_mix_volume_ul)
                + float(self.compound_volume_ul)
                + float(self.substrate_volume_ul)
            )
            if abs(component_total - float(self.reaction_volume_ul)) > 0.11:
                reasons.append("protocol component volumes do not sum to reaction volume")
        return {"passed": not reasons, "reasons": reasons}

    def physical_missing(self) -> list[str]:
        required = {
            "expression_confirmation_method": self.expression_confirmation_method,
            "expression_min_fold_over_background": (
                self.expression_min_fold_over_background
            ),
            "substrate_name": self.substrate_name,
            "read_wavelength_nm": self.read_wavelength_nm,
            "reaction_volume_ul": self.reaction_volume_ul,
            "assay_mix_volume_ul": self.assay_mix_volume_ul,
            "compound_volume_ul": self.compound_volume_ul,
            "substrate_volume_ul": self.substrate_volume_ul,
            "preincubation_s": self.preincubation_s,
        }
        missing = [name for name, value in required.items() if value is None]
        if not self.protocol_confirmed_by_organizer:
            missing.append("protocol_confirmed_by_organizer")
        return missing

    @property
    def physical_ready(self) -> bool:
        return self.verify()["passed"] and not self.physical_missing()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["round2_dose_factors"] = list(self.round2_dose_factors)
        payload["physical_ready"] = self.physical_ready
        payload["physical_missing"] = self.physical_missing()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TEM1AssaySpec":
        values = dict(payload)
        values.pop("physical_ready", None)
        values.pop("physical_missing", None)
        if "round2_dose_factors" in values:
            values["round2_dose_factors"] = tuple(values["round2_dose_factors"])
        spec = cls(**values)
        verdict = spec.verify()
        if not verdict["passed"]:
            raise TEM1Error("; ".join(verdict["reasons"]))
        return spec

    @classmethod
    def load(cls, path: str | Path) -> "TEM1AssaySpec":
        try:
            return cls.from_dict(json.loads(Path(path).read_text()))
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise TEM1Error(f"cannot load TEM-1 assay spec: {path}") from exc

    def save(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
        return destination


@dataclass(frozen=True)
class Compound:
    compound_id: str
    name: str
    source_well: str | None = None
    screen_concentration: float | None = None
    concentration_unit: str = "organizer_defined"
    features: tuple[float, ...] = ()

    def verify(self) -> dict[str, Any]:
        reasons: list[str] = []
        if not self.compound_id.strip():
            reasons.append("compound_id must not be empty")
        if self.source_well is not None and not is_well_name(self.source_well):
            reasons.append("source_well must be a valid 96-well position")
        if self.screen_concentration is not None and (
            not math.isfinite(self.screen_concentration)
            or self.screen_concentration <= 0
        ):
            reasons.append("screen concentration must be finite and positive")
        if any(not math.isfinite(value) for value in self.features):
            reasons.append("compound features must be finite")
        return {"passed": not reasons, "reasons": reasons}

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["features"] = list(self.features)
        return payload


def load_compounds(path: str | Path) -> list[Compound]:
    source = Path(path)
    if not source.exists():
        raise TEM1Error(f"compound library does not exist: {source}")
    with source.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if "compound_id" not in fields:
            raise TEM1Error("compound CSV needs a compound_id column")
        feature_fields = [field for field in fields if field.startswith("feature_")]
        compounds: list[Compound] = []
        for line_number, row in enumerate(reader, start=2):
            compound_id = str(row.get("compound_id", "")).strip()
            name = str(row.get("name", compound_id)).strip() or compound_id
            source_well = str(row.get("source_well", "")).strip().upper() or None
            raw_concentration = str(row.get("screen_concentration", "")).strip()
            try:
                concentration = float(raw_concentration) if raw_concentration else None
                features = tuple(float(row[field]) for field in feature_fields)
            except (TypeError, ValueError) as exc:
                raise TEM1Error(
                    f"compound CSV line {line_number} has a non-numeric value"
                ) from exc
            compound = Compound(
                compound_id=compound_id,
                name=name,
                source_well=source_well,
                screen_concentration=concentration,
                concentration_unit=(
                    str(row.get("concentration_unit", "")).strip()
                    or "organizer_defined"
                ),
                features=features,
            )
            verdict = compound.verify()
            if not verdict["passed"]:
                raise TEM1Error(
                    f"compound CSV line {line_number}: "
                    + "; ".join(verdict["reasons"])
                )
            compounds.append(compound)
    if not compounds:
        raise TEM1Error("compound library is empty")
    identifiers = [compound.compound_id for compound in compounds]
    if len(set(identifiers)) != len(identifiers):
        raise TEM1Error("compound IDs must be unique")
    return compounds


def save_compounds(compounds: Iterable[Compound], path: str | Path) -> Path:
    compounds = list(compounds)
    max_features = max((len(compound.features) for compound in compounds), default=0)
    fields = [
        "compound_id",
        "name",
        "source_well",
        "screen_concentration",
        "concentration_unit",
        *[f"feature_{index + 1}" for index in range(max_features)],
    ]
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for compound in compounds:
            row = {
                "compound_id": compound.compound_id,
                "name": compound.name,
                "source_well": compound.source_well or "",
                "screen_concentration": (
                    compound.screen_concentration
                    if compound.screen_concentration is not None else ""
                ),
                "concentration_unit": compound.concentration_unit,
            }
            row.update({
                f"feature_{index + 1}": value
                for index, value in enumerate(compound.features)
            })
            writer.writerow(row)
    return destination


@dataclass(frozen=True)
class PlateAssignment:
    well: str
    role: str
    compound_id: str | None = None
    concentration_factor: float | None = None
    concentration_value: float | None = None
    concentration_unit: str | None = None
    replicate: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TEM1RoundPlan:
    round_id: int
    assignments: tuple[PlateAssignment, ...]
    selection_rationale: dict[str, Any]
    measurement_schema: str = "well,time_s,value"

    def verify(
        self,
        compounds: Iterable[Compound],
        spec: TEM1AssaySpec,
    ) -> dict[str, Any]:
        reasons: list[str] = []
        compounds_by_id = {compound.compound_id: compound for compound in compounds}
        wells = [assignment.well for assignment in self.assignments]
        if self.round_id not in {1, 2}:
            reasons.append("round_id must be 1 or 2")
        if not self.assignments:
            reasons.append("round plan has no assignments")
        if len(wells) != len(set(wells)):
            reasons.append("round plan assigns a well more than once")
        if any(not is_well_name(well) for well in wells):
            reasons.append("round plan contains an invalid 96-well position")
        roles = {assignment.role for assignment in self.assignments}
        for control in CONTROL_WELLS:
            count = sum(
                assignment.role == control for assignment in self.assignments
            )
            if count < spec.control_replicates:
                reasons.append(
                    f"{control} needs {spec.control_replicates} replicates"
                )
        candidate_groups: dict[tuple[str, float], int] = {}
        for assignment in self.assignments:
            if assignment.role != "candidate":
                continue
            if assignment.compound_id not in compounds_by_id:
                reasons.append(
                    f"unknown candidate compound: {assignment.compound_id}"
                )
                continue
            if assignment.concentration_factor is None or (
                not math.isfinite(assignment.concentration_factor)
                or assignment.concentration_factor <= 0
            ):
                reasons.append("candidate concentration factor must be positive")
                continue
            key = (assignment.compound_id, assignment.concentration_factor)
            candidate_groups[key] = candidate_groups.get(key, 0) + 1
        if "candidate" not in roles:
            reasons.append("round plan contains no candidate wells")
        for (compound_id, factor), count in candidate_groups.items():
            if count < spec.candidate_replicates:
                reasons.append(
                    f"{compound_id} at {factor:g}x needs "
                    f"{spec.candidate_replicates} replicates"
                )
        spec_verdict = spec.verify()
        reasons.extend(spec_verdict["reasons"])
        physical_missing = spec.physical_missing()
        missing_sources = sorted({
            assignment.compound_id
            for assignment in self.assignments
            if assignment.role == "candidate"
            and assignment.compound_id in compounds_by_id
            and compounds_by_id[assignment.compound_id].source_well is None
        })
        physical_missing.extend(
            f"source_well:{compound_id}" for compound_id in missing_sources
        )
        passed = not reasons
        return {
            "passed": passed,
            "reasons": reasons,
            "physical_ready": passed and not physical_missing,
            "physical_missing": physical_missing,
            "execution_allowed": passed and not physical_missing,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_id": self.round_id,
            "assignments": [assignment.to_dict() for assignment in self.assignments],
            "selection_rationale": self.selection_rationale,
            "measurement_schema": self.measurement_schema,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TEM1RoundPlan":
        return cls(
            round_id=int(payload["round_id"]),
            assignments=tuple(
                PlateAssignment(**assignment)
                for assignment in payload["assignments"]
            ),
            selection_rationale=dict(payload.get("selection_rationale", {})),
            measurement_schema=str(
                payload.get("measurement_schema", "well,time_s,value")
            ),
        )

    @classmethod
    def load(cls, path: str | Path) -> "TEM1RoundPlan":
        try:
            return cls.from_dict(json.loads(Path(path).read_text()))
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise TEM1Error(f"cannot load TEM-1 round plan: {path}") from exc

    def save(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
        return destination


def _standardized_features(compounds: list[Compound]) -> list[tuple[float, ...]]:
    width = max((len(compound.features) for compound in compounds), default=0)
    if width == 0 or any(len(compound.features) != width for compound in compounds):
        return []
    columns = list(zip(*(compound.features for compound in compounds)))
    means = [sum(column) / len(column) for column in columns]
    scales = [statistics.pstdev(column) or 1.0 for column in columns]
    return [
        tuple((value - mean) / scale for value, mean, scale in zip(
            compound.features, means, scales
        ))
        for compound in compounds
    ]


def select_initial_compounds(
    compounds: Iterable[Compound],
    n_select: int,
) -> tuple[list[Compound], dict[str, Any]]:
    """Select a feature-diverse first round without inventing chemical claims."""
    compounds = list(compounds)
    if not 1 <= n_select <= len(compounds):
        raise TEM1Error("round-1 selection size is outside the compound library")
    features = _standardized_features(compounds)
    if not features:
        if n_select == 1:
            indices = [0]
        else:
            indices = sorted({
                round(index * (len(compounds) - 1) / (n_select - 1))
                for index in range(n_select)
            })
            for index in range(len(compounds)):
                if len(indices) >= n_select:
                    break
                if index not in indices:
                    indices.append(index)
        selected = [compounds[index] for index in indices[:n_select]]
        method = "deterministic library coverage; no numeric features supplied"
    else:
        selected_indices = [0]
        while len(selected_indices) < n_select:
            remaining = [
                index for index in range(len(compounds))
                if index not in selected_indices
            ]
            next_index = max(
                remaining,
                key=lambda index: min(
                    math.dist(features[index], features[chosen])
                    for chosen in selected_indices
                ),
            )
            selected_indices.append(next_index)
        selected = [compounds[index] for index in selected_indices]
        method = "greedy farthest-point diversity in organizer-supplied features"
    return selected, {
        "method": method,
        "library_size": len(compounds),
        "selected": [compound.compound_id for compound in selected],
        "measurement_used": False,
    }


def _candidate_wells() -> list[str]:
    reserved = {
        well for control_wells in CONTROL_WELLS.values() for well in control_wells
    }
    return [well for well in ALL_WELLS if well not in reserved]


def _control_assignments(spec: TEM1AssaySpec) -> list[PlateAssignment]:
    assignments: list[PlateAssignment] = []
    for role, wells in CONTROL_WELLS.items():
        if spec.control_replicates > len(wells):
            raise TEM1Error(
                f"portable layout supports at most {len(wells)} {role} replicates"
            )
        assignments.extend(
            PlateAssignment(well=well, role=role, replicate=index + 1)
            for index, well in enumerate(wells[:spec.control_replicates])
        )
    return assignments


def build_round1_plan(
    compounds: Iterable[Compound],
    spec: TEM1AssaySpec,
    *,
    n_select: int | None = None,
) -> TEM1RoundPlan:
    compounds = list(compounds)
    selected, rationale = select_initial_compounds(
        compounds, n_select or len(compounds)
    )
    wells = _candidate_wells()
    required = len(selected) * spec.candidate_replicates
    if required > len(wells):
        raise TEM1Error("round-1 candidates do not fit on one 96-well plate")
    assignments = _control_assignments(spec)
    for replicate in range(spec.candidate_replicates):
        offset = replicate * len(selected)
        order = selected if replicate % 2 == 0 else list(reversed(selected))
        for index, compound in enumerate(order):
            assignments.append(PlateAssignment(
                well=wells[offset + index],
                role="candidate",
                compound_id=compound.compound_id,
                concentration_factor=1.0,
                concentration_value=compound.screen_concentration,
                concentration_unit=compound.concentration_unit,
                replicate=replicate + 1,
            ))
    return TEM1RoundPlan(1, tuple(assignments), rationale)


class KineticPlate:
    """Kinetic values indexed by well with source-specific provenance."""

    def __init__(
        self,
        values: dict[str, list[tuple[float, float]]],
        *,
        provenance: str,
        evidence: dict[str, Any] | None = None,
    ):
        self.values = {
            str(well).upper(): sorted(points)
            for well, points in values.items()
        }
        self.provenance = provenance
        self.evidence = dict(evidence or {})
        self._verify()

    def _verify(self) -> None:
        if not self.values:
            raise TEM1Error("kinetic dataset is empty")
        for well, points in self.values.items():
            if not is_well_name(well):
                raise TEM1Error(f"kinetic dataset has invalid well: {well}")
            if len(points) < 3:
                raise TEM1Error(f"well {well} needs at least three time points")
            times = [time for time, _ in points]
            if len(times) != len(set(times)):
                raise TEM1Error(f"well {well} contains duplicate time points")
            if any(
                not math.isfinite(time) or not math.isfinite(value)
                for time, value in points
            ):
                raise TEM1Error(f"well {well} contains a non-finite value")

    @classmethod
    def from_csv(cls, path: str | Path) -> "KineticPlate":
        source = Path(path)
        if not source.exists():
            raise TEM1Error(f"kinetic reader CSV does not exist: {source}")
        values: dict[str, list[tuple[float, float]]] = {}
        with source.open(newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames or []
            if "well" not in fields or "time_s" not in fields:
                raise TEM1Error("kinetic CSV needs well and time_s columns")
            value_field = next(
                (field for field in ("value", "absorbance", "signal") if field in fields),
                None,
            )
            if value_field is None:
                raise TEM1Error("kinetic CSV needs value, absorbance, or signal")
            for line_number, row in enumerate(reader, start=2):
                well = str(row.get("well", "")).strip().upper()
                try:
                    time_s = float(row["time_s"])
                    value = float(row[value_field])
                except (KeyError, TypeError, ValueError) as exc:
                    raise TEM1Error(
                        f"kinetic CSV line {line_number} is not numeric"
                    ) from exc
                values.setdefault(well, []).append((time_s, value))
        return cls(
            values,
            provenance="measured:kinetic-reader-csv",
            evidence={"path": str(source), "sha256": file_sha256(source)},
        )

    def slope(self, well: str) -> float:
        normalized = str(well).upper()
        if normalized not in self.values:
            raise TEM1Error(f"kinetic dataset has no values for {normalized}")
        points = self.values[normalized]
        mean_time = sum(time for time, _ in points) / len(points)
        mean_value = sum(value for _, value in points) / len(points)
        denominator = sum((time - mean_time) ** 2 for time, _ in points)
        if denominator <= 1e-12:
            raise TEM1Error(f"well {normalized} time axis has zero span")
        return sum(
            (time - mean_time) * (value - mean_value)
            for time, value in points
        ) / denominator


class ExpressionEvidence:
    """Replicated TEM-1 expression and no-template control measurements."""

    def __init__(
        self,
        values: dict[str, list[float]],
        *,
        provenance: str,
        evidence: dict[str, Any] | None = None,
    ):
        self.values = {
            str(role).strip().lower(): [float(value) for value in measurements]
            for role, measurements in values.items()
        }
        self.provenance = provenance
        self.evidence = dict(evidence or {})
        for role in ("tem1_expression", "no_template_control"):
            measurements = self.values.get(role, [])
            if len(measurements) < 2:
                raise TEM1Error(f"{role} needs at least two replicates")
            if any(not math.isfinite(value) for value in measurements):
                raise TEM1Error(f"{role} contains a non-finite value")

    @classmethod
    def from_csv(cls, path: str | Path) -> "ExpressionEvidence":
        source = Path(path)
        if not source.exists():
            raise TEM1Error(f"expression evidence CSV does not exist: {source}")
        values: dict[str, list[float]] = {}
        with source.open(newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames or []
            if "role" not in fields or "value" not in fields:
                raise TEM1Error("expression CSV needs role and value columns")
            for line_number, row in enumerate(reader, start=2):
                role = str(row.get("role", "")).strip().lower()
                try:
                    value = float(row["value"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise TEM1Error(
                        f"expression CSV line {line_number} is not numeric"
                    ) from exc
                values.setdefault(role, []).append(value)
        return cls(
            values,
            provenance="measured:expression-csv",
            evidence={"path": str(source), "sha256": file_sha256(source)},
        )


def confirm_expression(
    expression: ExpressionEvidence,
    spec: TEM1AssaySpec,
) -> dict[str, Any]:
    """Gate inhibitor screening on provenance-labeled TEM-1 evidence."""
    if spec.expression_confirmation_method is None:
        raise TEM1Error("organizer expression confirmation method is not configured")
    if spec.expression_min_fold_over_background is None:
        raise TEM1Error("organizer expression fold threshold is not configured")
    expressed = expression.values["tem1_expression"]
    negative = expression.values["no_template_control"]
    expressed_mean, expressed_sd = _mean_sd(expressed)
    negative_mean, negative_sd = _mean_sd(negative)
    fold = expressed_mean / negative_mean if negative_mean > 0 else math.inf
    expressed_cv = (
        expressed_sd / expressed_mean * 100.0 if expressed_mean > 0 else math.inf
    )
    reasons: list[str] = []
    if expressed_mean <= negative_mean:
        reasons.append("TEM-1 expression signal is not above no-template control")
    if fold < spec.expression_min_fold_over_background:
        reasons.append(
            f"expression fold {fold:.3f} is below "
            f"{spec.expression_min_fold_over_background:.3f}"
        )
    if expressed_cv > spec.expression_max_cv_pct:
        reasons.append(
            f"expression CV {expressed_cv:.2f}% exceeds "
            f"{spec.expression_max_cv_pct:.2f}%"
        )
    return {
        "passed": not reasons,
        "method": spec.expression_confirmation_method,
        "provenance": expression.provenance,
        "fold_over_background": round(fold, 5) if math.isfinite(fold) else None,
        "expression_cv_pct": (
            round(expressed_cv, 5) if math.isfinite(expressed_cv) else None
        ),
        "tem1_expression": {
            "mean": round(expressed_mean, 8),
            "sd": round(expressed_sd, 8),
            "replicates": len(expressed),
        },
        "no_template_control": {
            "mean": round(negative_mean, 8),
            "sd": round(negative_sd, 8),
            "replicates": len(negative),
        },
        "criteria": {
            "minimum_fold_over_background": (
                spec.expression_min_fold_over_background
            ),
            "maximum_cv_pct": spec.expression_max_cv_pct,
        },
        "reasons": reasons,
        "evidence": expression.evidence,
    }


def _mean_sd(values: list[float]) -> tuple[float, float]:
    if not values:
        raise TEM1Error("cannot summarize an empty replicate group")
    return (
        sum(values) / len(values),
        statistics.stdev(values) if len(values) >= 2 else 0.0,
    )


def analyze_round(
    plan: TEM1RoundPlan,
    compounds: Iterable[Compound],
    spec: TEM1AssaySpec,
    plate: KineticPlate,
) -> dict[str, Any]:
    compounds = list(compounds)
    plan_verification = plan.verify(compounds, spec)
    if not plan_verification["passed"]:
        raise TEM1Error("; ".join(plan_verification["reasons"]))
    missing = sorted({
        assignment.well
        for assignment in plan.assignments
        if assignment.well not in plate.values
    })
    if missing:
        raise TEM1Error("kinetic evidence is missing wells: " + ", ".join(missing))

    slopes = {
        assignment.well: plate.slope(assignment.well)
        for assignment in plan.assignments
    }
    control_values = {
        role: [
            slopes[assignment.well]
            for assignment in plan.assignments
            if assignment.role == role
        ]
        for role in CONTROL_WELLS
    }
    control_stats = {
        role: dict(zip(("mean_slope", "sd_slope"), _mean_sd(values)))
        for role, values in control_values.items()
    }
    activity_mean = control_stats["activity_control"]["mean_slope"]
    activity_sd = control_stats["activity_control"]["sd_slope"]
    inhibited_mean = control_stats["inhibition_control"]["mean_slope"]
    inhibited_sd = control_stats["inhibition_control"]["sd_slope"]
    blank_mean = control_stats["blank"]["mean_slope"]
    dynamic_range = activity_mean - blank_mean
    control_separation = abs(activity_mean - inhibited_mean)
    z_prime = (
        1.0 - 3.0 * (activity_sd + inhibited_sd) / control_separation
        if control_separation > 1e-12 else -math.inf
    )
    qc_reasons: list[str] = []
    if dynamic_range <= 0:
        qc_reasons.append("activity control is not above the blank")
    if not math.isfinite(z_prime) or z_prime < spec.z_prime_min:
        qc_reasons.append(
            f"Z-prime {z_prime:.3f} is below {spec.z_prime_min:.3f}"
        )
    qc_passed = not qc_reasons

    candidate_groups: dict[tuple[str, float], list[PlateAssignment]] = {}
    for assignment in plan.assignments:
        if assignment.role == "candidate":
            key = (assignment.compound_id or "", assignment.concentration_factor or 0.0)
            candidate_groups.setdefault(key, []).append(assignment)
    candidate_results: list[dict[str, Any]] = []
    for (compound_id, factor), assignments in candidate_groups.items():
        inhibition_values = [
            100.0 * (1.0 - (slopes[assignment.well] - blank_mean) / dynamic_range)
            if dynamic_range > 0 else math.nan
            for assignment in assignments
        ]
        mean_inhibition, sd_inhibition = _mean_sd(inhibition_values)
        standard_error = sd_inhibition / math.sqrt(len(inhibition_values))
        reasons: list[str] = []
        if mean_inhibition < spec.hit_threshold_pct:
            reasons.append(
                f"mean inhibition {mean_inhibition:.2f}% is below "
                f"{spec.hit_threshold_pct:.2f}%"
            )
        if sd_inhibition > spec.max_replicate_sd_pct:
            reasons.append(
                f"replicate SD {sd_inhibition:.2f}% exceeds "
                f"{spec.max_replicate_sd_pct:.2f}%"
            )
        if not qc_passed:
            reasons.append("assay QC failed")
        candidate_results.append({
            "compound_id": compound_id,
            "concentration_factor": factor,
            "concentration_value": assignments[0].concentration_value,
            "concentration_unit": assignments[0].concentration_unit,
            "wells": [assignment.well for assignment in assignments],
            "replicate_inhibition_pct": [
                round(value, 4) for value in inhibition_values
            ],
            "mean_inhibition_pct": round(mean_inhibition, 4),
            "sd_inhibition_pct": round(sd_inhibition, 4),
            "standard_error_pct": round(standard_error, 4),
            "lower_confidence_score": round(mean_inhibition - standard_error, 4),
            "hit": not reasons,
            "reasons": reasons,
        })
    candidate_results.sort(
        key=lambda result: result["lower_confidence_score"], reverse=True
    )
    analysis = {
        "schema_version": "1.0",
        "track": TRACK_NAME,
        "target": spec.target,
        "round_id": plan.round_id,
        "plan": plan.to_dict(),
        "plan_verification": plan_verification,
        "measurement": {
            "provenance": plate.provenance,
            "evidence": plate.evidence,
            "well_slopes": {well: round(value, 8) for well, value in slopes.items()},
        },
        "assay_qc": {
            "passed": qc_passed,
            "z_prime": round(z_prime, 5) if math.isfinite(z_prime) else None,
            "minimum_z_prime": spec.z_prime_min,
            "dynamic_range": round(dynamic_range, 8),
            "controls": control_stats,
            "reasons": qc_reasons,
        },
        "candidates": candidate_results,
        "world_model": {
            "updated": qc_passed,
            "reason": (
                "observed inhibition and uncertainty accepted"
                if qc_passed else "control QC failed; measurements quarantined"
            ),
        },
    }
    if plan.round_id == 2 and qc_passed:
        analysis["dose_response"] = summarize_dose_response(analysis)
    return analysis


def build_round2_plan(
    round1_analysis: dict[str, Any],
    compounds: Iterable[Compound],
    spec: TEM1AssaySpec,
    *,
    top_k: int = 3,
) -> TEM1RoundPlan:
    if top_k < 1:
        raise TEM1Error("round-2 selection needs at least one compound")
    if not round1_analysis.get("assay_qc", {}).get("passed"):
        raise AssayQCError("round 1 failed assay QC; refusing to design round 2")
    compounds = list(compounds)
    compounds_by_id = {compound.compound_id: compound for compound in compounds}
    ranked = list(round1_analysis.get("candidates", []))
    if not ranked:
        raise TEM1Error("round-1 analysis contains no candidates")
    selected_rows = ranked[:min(top_k, len(ranked))]
    unknown = sorted({
        str(row.get("compound_id"))
        for row in selected_rows
        if row.get("compound_id") not in compounds_by_id
    })
    if unknown:
        raise TEM1Error(
            "round-1 analysis contains unknown compounds: " + ", ".join(unknown)
        )
    selected = [compounds_by_id[row["compound_id"]] for row in selected_rows]
    conditions = [
        (compound, factor)
        for compound in selected
        for factor in spec.round2_dose_factors
    ]
    wells = _candidate_wells()
    required = len(conditions) * spec.candidate_replicates
    if required > len(wells):
        raise TEM1Error("round-2 confirmation conditions do not fit on one plate")
    assignments = _control_assignments(spec)
    for replicate in range(spec.candidate_replicates):
        offset = replicate * len(conditions)
        order = conditions if replicate % 2 == 0 else list(reversed(conditions))
        for index, (compound, factor) in enumerate(order):
            concentration = (
                compound.screen_concentration * factor
                if compound.screen_concentration is not None else None
            )
            assignments.append(PlateAssignment(
                well=wells[offset + index],
                role="candidate",
                compound_id=compound.compound_id,
                concentration_factor=factor,
                concentration_value=concentration,
                concentration_unit=compound.concentration_unit,
                replicate=replicate + 1,
            ))
    rationale = {
        "method": "observed inhibition minus one standard error",
        "measurement_used": True,
        "round1_qc_passed": True,
        "selected": [
            {
                "compound_id": row["compound_id"],
                "mean_inhibition_pct": row["mean_inhibition_pct"],
                "standard_error_pct": row["standard_error_pct"],
                "selection_score": row["lower_confidence_score"],
            }
            for row in selected_rows
        ],
        "dose_factors": list(spec.round2_dose_factors),
    }
    return TEM1RoundPlan(2, tuple(assignments), rationale)


def summarize_dose_response(round2_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """Summarize four-point confirmation curves without overfitting them.

    The event protocol defines the real concentrations. Until those values are
    supplied, the estimate remains a relative dose factor. Monotonicity is
    evaluated with one-standard-error tolerance so tiny replicate noise does
    not manufacture a curve failure.
    """
    if round2_analysis.get("round_id") != 2:
        raise TEM1Error("dose-response summary requires round-2 analysis")
    if not round2_analysis.get("assay_qc", {}).get("passed"):
        raise AssayQCError("round 2 failed assay QC; refusing dose-response claims")

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in round2_analysis.get("candidates", []):
        grouped.setdefault(str(row["compound_id"]), []).append(row)
    if not grouped:
        raise TEM1Error("round-2 analysis contains no candidate conditions")

    summaries: list[dict[str, Any]] = []
    for compound_id, rows in grouped.items():
        rows.sort(key=lambda row: float(row["concentration_factor"]))
        violations: list[dict[str, float]] = []
        for lower, higher in zip(rows, rows[1:]):
            lower_bound = (
                float(lower["mean_inhibition_pct"])
                - float(lower["standard_error_pct"])
            )
            higher_bound = (
                float(higher["mean_inhibition_pct"])
                + float(higher["standard_error_pct"])
            )
            if higher_bound < lower_bound:
                violations.append({
                    "lower_factor": float(lower["concentration_factor"]),
                    "higher_factor": float(higher["concentration_factor"]),
                })

        first = rows[0]
        last = rows[-1]
        first_inhibition = float(first["mean_inhibition_pct"])
        last_inhibition = float(last["mean_inhibition_pct"])
        crossing: float | None = None
        crossing_status = "interpolated"
        if first_inhibition >= 50.0:
            crossing = float(first["concentration_factor"])
            crossing_status = "at_or_below_lowest_tested_factor"
        elif last_inhibition < 50.0:
            crossing = float(last["concentration_factor"])
            crossing_status = "above_highest_tested_factor"
        else:
            for lower, higher in zip(rows, rows[1:]):
                y0 = float(lower["mean_inhibition_pct"])
                y1 = float(higher["mean_inhibition_pct"])
                if y0 <= 50.0 <= y1 and y1 > y0:
                    x0 = math.log(float(lower["concentration_factor"]))
                    x1 = math.log(float(higher["concentration_factor"]))
                    fraction = (50.0 - y0) / (y1 - y0)
                    crossing = math.exp(x0 + fraction * (x1 - x0))
                    break
        if crossing is None:
            crossing_status = "not_estimable_from_nonmonotonic_points"

        best = max(rows, key=lambda row: float(row["lower_confidence_score"]))
        summaries.append({
            "compound_id": compound_id,
            "points": [
                {
                    "concentration_factor": row["concentration_factor"],
                    "mean_inhibition_pct": row["mean_inhibition_pct"],
                    "standard_error_pct": row["standard_error_pct"],
                    "lower_confidence_score": row["lower_confidence_score"],
                }
                for row in rows
            ],
            "monotonic_with_uncertainty": not violations,
            "monotonicity_violations": violations,
            "inhibition_50_factor_estimate": (
                round(crossing, 5) if crossing is not None else None
            ),
            "inhibition_50_status": crossing_status,
            "best_factor": best["concentration_factor"],
            "best_mean_inhibition_pct": best["mean_inhibition_pct"],
            "best_lower_confidence_score": best["lower_confidence_score"],
            "confirmation_passed": (
                not violations
                and bool(best["hit"])
            ),
        })
    summaries.sort(
        key=lambda row: float(row["best_lower_confidence_score"]),
        reverse=True,
    )
    return summaries


def receipt_sha256(receipt: dict[str, Any]) -> str:
    """Hash the canonical receipt payload, excluding its integrity envelope."""
    payload = dict(receipt)
    payload.pop("integrity", None)
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def seal_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(receipt)
    sealed["integrity"] = {
        "algorithm": "sha256",
        "digest": receipt_sha256(sealed),
    }
    return sealed


def verify_receipt_integrity(receipt: dict[str, Any]) -> bool:
    integrity = receipt.get("integrity", {})
    return (
        integrity.get("algorithm") == "sha256"
        and integrity.get("digest") == receipt_sha256(receipt)
    )


def save_analysis(analysis: dict[str, Any], path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(analysis, indent=2) + "\n")
    return destination


def simulation_compounds() -> list[Compound]:
    """Generic identifiers only. These are not claims about event compounds."""
    return [
        Compound(
            compound_id=f"CMPD-{index:02d}",
            name=f"simulated candidate {index:02d}",
            source_well=f"{ROWS[(index - 1) % 8]}{(index - 1) // 8 + 1}",
            screen_concentration=1.0,
            concentration_unit="relative_simulation_unit",
            features=(
                round(math.sin(index), 4),
                round(math.cos(index), 4),
                round((index % 4) / 3.0, 4),
            ),
        )
        for index in range(1, 11)
    ]


SIMULATED_MAX_INHIBITION = {
    "CMPD-01": 0.12,
    "CMPD-02": 0.28,
    "CMPD-03": 0.83,
    "CMPD-04": 0.18,
    "CMPD-05": 0.54,
    "CMPD-06": 0.09,
    "CMPD-07": 0.91,
    "CMPD-08": 0.35,
    "CMPD-09": 0.65,
    "CMPD-10": 0.22,
}


def simulate_kinetic_plate(
    plan: TEM1RoundPlan,
    *,
    seed: int,
) -> KineticPlate:
    """Generate deterministic modeled kinetics for the guaranteed fallback."""
    rng = random.Random(seed)
    values: dict[str, list[tuple[float, float]]] = {}
    for assignment in plan.assignments:
        if assignment.role == "blank":
            slope = 0.015
        elif assignment.role == "activity_control":
            slope = 0.82
        elif assignment.role == "inhibition_control":
            slope = 0.065
        else:
            maximum = SIMULATED_MAX_INHIBITION.get(assignment.compound_id or "", 0.0)
            factor = assignment.concentration_factor or 1.0
            inhibition = maximum * factor / (0.45 + factor)
            slope = 0.015 + (0.82 - 0.015) * (1.0 - inhibition)
        slope *= 1.0 + rng.uniform(-0.018, 0.018)
        baseline = 0.10 + rng.uniform(-0.006, 0.006)
        values[assignment.well] = [
            (float(time_s), baseline + slope * (time_s / 60.0)
             + rng.uniform(-0.002, 0.002))
            for time_s in (0, 30, 60, 90, 120)
        ]
    return KineticPlate(
        values,
        provenance="modeled:tem1-kinetics",
        evidence={"seed": seed, "fixture": "TEM-1 two-round simulator"},
    )


def simulate_expression_evidence(seed: int = 17) -> ExpressionEvidence:
    rng = random.Random(seed)
    return ExpressionEvidence(
        {
            "tem1_expression": [
                9.8 * (1.0 + rng.uniform(-0.025, 0.025)) for _ in range(3)
            ],
            "no_template_control": [
                1.0 * (1.0 + rng.uniform(-0.025, 0.025)) for _ in range(3)
            ],
        },
        provenance="modeled:tem1-expression",
        evidence={"seed": seed, "fixture": "cell-free expression simulation"},
    )


def run_simulated_closed_loop(seed: int = 17) -> dict[str, Any]:
    spec = TEM1AssaySpec(
        expression_confirmation_method="modeled activity proxy",
        expression_min_fold_over_background=2.0,
    )
    compounds = simulation_compounds()
    expression = confirm_expression(simulate_expression_evidence(seed), spec)
    if not expression["passed"]:
        raise AssayQCError("simulated TEM-1 expression failed confirmation")
    round1_plan = build_round1_plan(compounds, spec, n_select=8)
    round1_plate = simulate_kinetic_plate(round1_plan, seed=seed)
    round1 = analyze_round(round1_plan, compounds, spec, round1_plate)
    round2_plan = build_round2_plan(round1, compounds, spec, top_k=3)
    round2_plate = simulate_kinetic_plate(round2_plan, seed=seed + 1)
    round2 = analyze_round(round2_plan, compounds, spec, round2_plate)
    if not round2["assay_qc"]["passed"]:
        raise AssayQCError("round 2 failed assay QC; refusing final nomination")
    dose_response = round2["dose_response"]
    eligible = [row for row in dose_response if row["confirmation_passed"]]
    if not eligible:
        raise AssayQCError(
            "no round-2 candidate passed the inhibition and dose-response gates"
        )
    best_curve = eligible[0]
    best = next(
        row for row in round2["candidates"]
        if row["compound_id"] == best_curve["compound_id"]
        and row["concentration_factor"] == best_curve["best_factor"]
    )
    receipt = {
        "schema_version": "2.0",
        "track": TRACK_NAME,
        "target": TARGET_NAME,
        "mode": "simulation",
        "assay_spec": spec.to_dict(),
        "protein_synthesis": {
            "stage": "cell-free TEM-1 production",
            "confirmation": expression,
            "screening_allowed": expression["passed"],
        },
        "rounds": [round1, round2],
        "follow_up": {
            "action": "nominate confirmed inhibitor condition for downstream characterization",
            "compound_id": best["compound_id"],
            "concentration_factor": best["concentration_factor"],
            "mean_inhibition_pct": best["mean_inhibition_pct"],
            "inhibition_50_factor_estimate": (
                best_curve["inhibition_50_factor_estimate"]
            ),
            "inhibition_50_status": best_curve["inhibition_50_status"],
            "dose_response_monotonic": (
                best_curve["monotonic_with_uncertainty"]
            ),
            "executed": True,
            "provenance": "modeled",
        },
    }
    return seal_receipt(receipt)


def save_closed_loop(receipt: dict[str, Any], path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if "integrity" in receipt and not verify_receipt_integrity(receipt):
        raise TEM1Error("refusing to save a TEM-1 receipt with invalid integrity")
    sealed = receipt if verify_receipt_integrity(receipt) else seal_receipt(receipt)
    destination.write_text(json.dumps(sealed, indent=2) + "\n")
    return destination
