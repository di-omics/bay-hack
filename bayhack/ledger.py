"""Machine-readable trust receipts for each physical experiment."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .assay import FollowUpAction, LiquidHandlingPlan


@dataclass(frozen=True)
class TrustRecord:
    run_id: int
    phase: str
    plan: dict
    plan_verification: dict
    execution: dict
    measurement: dict
    physical_verification: dict
    decision: str
    world_model: dict

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TrustLedger:
    """Append-only evidence for planning, execution, measurement, and follow-up."""

    schema_version: str = "1.0"
    records: list[TrustRecord] = field(default_factory=list)
    follow_up: dict | None = None

    def append_round(
        self,
        *,
        plan: LiquidHandlingPlan,
        plan_verification: dict,
        backend: str,
        measurement_value: float,
        measurement_provenance: str,
        rhodamine: dict,
        cv: dict,
        verification_provenance: str,
        decision: str,
        best_x: float,
        best_y: float,
        model_updated: bool,
    ) -> None:
        prior_model = next(
            (
                record.world_model
                for record in reversed(self.records)
                if record.world_model.get("updated")
            ),
            None,
        )
        model_state = {
            "updated": model_updated,
            "best_x": best_x if model_updated else (
                prior_model["best_x"] if prior_model else None
            ),
            "best_y": best_y if model_updated else (
                prior_model["best_y"] if prior_model else None
            ),
        }
        self.records.append(
            TrustRecord(
                run_id=plan.run_id,
                phase=plan.phase,
                plan=plan.to_dict(),
                plan_verification=plan_verification,
                execution={"passed": True, "backend": backend},
                measurement={
                    "value": measurement_value,
                    "provenance": measurement_provenance,
                },
                physical_verification={
                    "passed": bool(rhodamine["passed"] and cv["passed"]),
                    "provenance": verification_provenance,
                    "rhodamine": rhodamine,
                    "cv": cv,
                },
                decision=decision,
                world_model=model_state,
            )
        )

    def append_follow_up(
        self,
        action: FollowUpAction,
        verification: dict,
        executed: bool,
        backend: str,
    ) -> None:
        self.follow_up = {
            "action": action.to_dict(),
            "verification": verification,
            "execution": {"passed": executed, "backend": backend},
        }

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "records": [record.to_dict() for record in self.records],
            "follow_up": self.follow_up,
        }

    def save(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
        return destination
