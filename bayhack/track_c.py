"""Track C: verified tube access for autonomous liquid handling.

The controller treats perception as a gate, not decoration. A tube is never
presented for pipetting until an independent observation verifies that its cap
is off. A run is never called complete until another observation verifies that
the cap is seated again.

The guaranteed path is a deterministic simulation. Hardware and camera systems
plug in through the small TubeActuator and CapVerifier protocols.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol


TRACK_NAME = "Track C: Dexterity and Physical Verification"
CAPABILITY = "verified tube access for liquid handling"


class TrackCError(RuntimeError):
    """The verified tube-access workflow cannot continue safely."""


class CapState(str, Enum):
    CAPPED = "capped"
    UNCAPPED = "uncapped"
    AMBIGUOUS = "ambiguous"


class WorkflowState(str, Enum):
    OBSERVE_CAPPED = "observe_capped"
    LOCALIZE = "localize"
    GRASP_CAP = "grasp_cap"
    UNSCREW = "unscrew"
    VERIFY_OPEN = "verify_open"
    PRESENT_FOR_PIPETTING = "present_for_pipetting"
    RECAP = "recap"
    VERIFY_CLOSED = "verify_closed"
    COMPLETE = "complete"
    STOPPED = "stopped"


@dataclass(frozen=True)
class ActionResult:
    passed: bool
    detail: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapObservation:
    checkpoint: str
    state: CapState
    confidence: float
    provenance: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("observation confidence must be between 0 and 1")
        if not self.provenance:
            raise ValueError("observation provenance is required")

    def verifies(self, expected: CapState, min_confidence: float) -> bool:
        return self.state is expected and self.confidence >= min_confidence

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["state"] = self.state.value
        return payload


class TubeActuator(Protocol):
    backend_name: str
    physical_hardware_commands: int

    def localize(self) -> ActionResult: ...
    def grasp_cap(self) -> ActionResult: ...
    def uncap(self) -> ActionResult: ...
    def present_for_pipetting(self) -> ActionResult: ...
    def recap(self) -> ActionResult: ...


class CapVerifier(Protocol):
    def observe(self, checkpoint: str) -> CapObservation: ...


@dataclass(frozen=True)
class TubeAccessConfig:
    tube_id: str = "sample-tube-A1"
    fixture_id: str = "split-collar-tube-nest"
    min_confidence: float = 0.86
    max_retries: int = 2

    def __post_init__(self) -> None:
        if not 0.0 < self.min_confidence <= 1.0:
            raise ValueError("min_confidence must be in (0, 1]")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")


class SimulatedTubeCell:
    """Deterministic motion backend for the stage demo."""

    FAULTS = {
        "none",
        "cap_slip",
        "partial_uncap",
        "rotated_tube",
        "ambiguous_close",
        "persistent_open_ambiguity",
    }

    backend_name = "simulated-tube-cell"
    mode = "simulation"
    execution_kind = "simulated_action"
    execution_provenance = "simulated execution"
    physical_hardware_commands = 0

    def __init__(self, fault: str = "none") -> None:
        if fault not in self.FAULTS:
            raise ValueError(f"unknown fault: {fault}")
        self.fault = fault
        self.actual_state = "capped"
        self.localized = False
        self.cap_grasped = False
        self.simulated_actions: list[dict[str, Any]] = []
        self._attempts = {
            "localize": 0,
            "grasp": 0,
            "uncap": 0,
            "recap": 0,
        }

    def _record(self, action: str, passed: bool, detail: str) -> ActionResult:
        result = ActionResult(
            passed,
            detail,
            {
                "action_index": len(self.simulated_actions) + 1,
                "provenance": "simulated execution",
            },
        )
        self.simulated_actions.append({"action": action, **result.to_dict()})
        return result

    def localize(self) -> ActionResult:
        self._attempts["localize"] += 1
        if self.fault == "rotated_tube" and self._attempts["localize"] == 1:
            self.localized = False
            return self._record(
                "localize",
                False,
                "tube yaw is outside the fixture tolerance",
            )
        self.localized = True
        return self._record(
            "localize",
            True,
            "tube and cap pose localized against the fixture fiducial",
        )

    def grasp_cap(self) -> ActionResult:
        self._attempts["grasp"] += 1
        if not self.localized:
            return self._record("grasp_cap", False, "tube pose is not localized")
        if self.fault == "cap_slip" and self._attempts["grasp"] == 1:
            self.cap_grasped = False
            return self._record(
                "grasp_cap",
                False,
                "gripper force dropped below the cap-grasp threshold",
            )
        self.cap_grasped = True
        return self._record("grasp_cap", True, "cap grasp is stable")

    def uncap(self) -> ActionResult:
        self._attempts["uncap"] += 1
        if not self.cap_grasped:
            return self._record("uncap", False, "cap is not securely grasped")
        if self.fault == "partial_uncap" and self._attempts["uncap"] == 1:
            self.actual_state = "partial"
            self.cap_grasped = False
            return self._record(
                "uncap",
                True,
                "commanded rotation completed but cap separation is uncertain",
            )
        self.actual_state = "uncapped"
        self.cap_grasped = False
        return self._record(
            "uncap",
            True,
            "cap rotated, lifted clear, and moved to the parking nest",
        )

    def present_for_pipetting(self) -> ActionResult:
        if self.actual_state != "uncapped":
            return self._record(
                "present_for_pipetting",
                False,
                "tube opening is not physically clear",
            )
        return self._record(
            "present_for_pipetting",
            True,
            "tube opening presented at the liquid-handler access pose",
        )

    def recap(self) -> ActionResult:
        self._attempts["recap"] += 1
        if self.actual_state == "capped" and self._attempts["recap"] == 1:
            return self._record("recap", True, "cap is already at the tube mouth")
        self.actual_state = "capped"
        return self._record(
            "recap",
            True,
            "cap returned, threads engaged, and closure torque applied",
        )


class SimulatedCapCamera:
    """A sensor model kept separate from the simulated motion backend."""

    def __init__(self, cell: SimulatedTubeCell) -> None:
        self.cell = cell
        self._observations: dict[str, int] = {}

    def observe(self, checkpoint: str) -> CapObservation:
        count = self._observations.get(checkpoint, 0) + 1
        self._observations[checkpoint] = count
        state = CapState.AMBIGUOUS
        confidence = 0.55
        cue = "insufficient visual separation"

        if checkpoint == "initial":
            state = CapState.CAPPED
            confidence = 0.99
            cue = "cap rim aligned with tube neck"
        elif checkpoint == "open":
            if self.cell.fault == "persistent_open_ambiguity":
                state = CapState.AMBIGUOUS
                confidence = 0.58
                cue = "cap and tube contours remain occluded"
            elif self.cell.actual_state == "uncapped":
                state = CapState.UNCAPPED
                confidence = 0.98
                cue = "tube mouth visible and cap detected in parking nest"
            elif self.cell.actual_state == "partial":
                state = CapState.AMBIGUOUS
                confidence = 0.63
                cue = "cap is elevated but threads may still be engaged"
        elif checkpoint == "closed":
            if self.cell.fault == "ambiguous_close" and count == 1:
                state = CapState.AMBIGUOUS
                confidence = 0.68
                cue = "cap is present but seating line is unresolved"
            elif self.cell.actual_state == "capped":
                state = CapState.CAPPED
                confidence = 0.98
                cue = "cap seating line is continuous around the tube"

        return CapObservation(
            checkpoint=checkpoint,
            state=state,
            confidence=confidence,
            provenance="modeled:independent-cap-camera",
            evidence={
                "cue": cue,
                "observation_index": count,
                "fault_injection": self.cell.fault,
            },
        )


class EvidenceFileCapVerifier:
    """Replay ordered camera observations from a JSON evidence file.

    This adapter is useful on site: a camera process owns image analysis and
    writes observations, while the controller consumes only explicit state,
    confidence, provenance, and evidence fields.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        try:
            payload = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise TrackCError(f"cannot load cap evidence: {self.path}") from exc
        rows = payload.get("observations")
        if not isinstance(rows, list) or not rows:
            raise TrackCError("cap evidence must contain an observations list")
        self._rows = list(rows)
        self._cursor = 0

    def observe(self, checkpoint: str) -> CapObservation:
        if self._cursor >= len(self._rows):
            raise TrackCError(f"no cap observation remains for {checkpoint}")
        row = self._rows[self._cursor]
        self._cursor += 1
        if not isinstance(row, dict):
            raise TrackCError("cap observation row must be an object")
        if row.get("checkpoint") != checkpoint:
            raise TrackCError(
                f"expected {checkpoint} evidence, got {row.get('checkpoint')}"
            )
        try:
            state = CapState(str(row["state"]))
            confidence = float(row["confidence"])
            provenance = str(row["provenance"])
        except (KeyError, TypeError, ValueError) as exc:
            raise TrackCError("invalid cap observation row") from exc
        evidence = row.get("evidence", {})
        if not isinstance(evidence, dict):
            raise TrackCError("cap observation evidence must be an object")
        return CapObservation(
            checkpoint,
            state,
            confidence,
            provenance,
            dict(evidence),
        )


class VerifiedTubeAccessController:
    """Execute tube access with independent open and closed verification."""

    def __init__(
        self,
        actuator: TubeActuator,
        verifier: CapVerifier,
        config: TubeAccessConfig | None = None,
    ) -> None:
        self.actuator = actuator
        self.verifier = verifier
        self.config = config or TubeAccessConfig()
        self.events: list[dict[str, Any]] = []
        self.recoveries = 0
        self.open_observation: CapObservation | None = None
        self.closed_observation: CapObservation | None = None

    def _event(
        self,
        state: WorkflowState,
        kind: str,
        passed: bool,
        detail: str,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        self.events.append({
            "sequence": len(self.events) + 1,
            "state": state.value,
            "kind": kind,
            "passed": passed,
            "detail": detail,
            "evidence": dict(evidence or {}),
        })

    def _observe(
        self,
        state: WorkflowState,
        checkpoint: str,
        expected: CapState,
    ) -> tuple[bool, CapObservation]:
        try:
            observation = self.verifier.observe(checkpoint)
            if not isinstance(observation, CapObservation):
                raise TypeError("observer did not return CapObservation")
        except Exception as exc:
            observation = CapObservation(
                checkpoint=checkpoint,
                state=CapState.AMBIGUOUS,
                confidence=0.0,
                provenance="system:observer-error",
                evidence={
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
        passed = observation.verifies(expected, self.config.min_confidence)
        self._event(
            state,
            "physical_verification",
            passed,
            (
                f"observed {observation.state.value} at "
                f"{observation.confidence:.2f} confidence; expected "
                f"{expected.value} at {self.config.min_confidence:.2f} or above"
            ),
            observation.to_dict(),
        )
        return passed, observation

    def _act(self, state: WorkflowState, action: str) -> ActionResult:
        try:
            result = getattr(self.actuator, action)()
            if not isinstance(result, ActionResult):
                raise TypeError("actuator did not return ActionResult")
        except Exception as exc:
            result = ActionResult(
                False,
                f"{action} failed with {type(exc).__name__}: {exc}",
                {"provenance": "system:actuator-error"},
            )
        self._event(
            state,
            getattr(self.actuator, "execution_kind", "action"),
            result.passed,
            result.detail,
            result.evidence,
        )
        return result

    def _recover(self, state: WorkflowState, detail: str) -> None:
        self.recoveries += 1
        self._event(
            state,
            "recovery",
            True,
            detail,
            {"recovery_index": self.recoveries},
        )

    def _retry_action(
        self,
        state: WorkflowState,
        action: str,
        recovery_detail: str,
    ) -> bool:
        for attempt in range(self.config.max_retries + 1):
            result = self._act(state, action)
            if result.passed:
                return True
            if attempt < self.config.max_retries:
                self._recover(state, recovery_detail)
                if action == "grasp_cap":
                    self._act(WorkflowState.LOCALIZE, "localize")
        return False

    def _receipt(
        self,
        *,
        status: str,
        terminal_state: WorkflowState,
        reason: str,
        pipetting_allowed: bool,
        open_verified: bool,
        closed_verified: bool,
    ) -> dict[str, Any]:
        simulated_actions = getattr(self.actuator, "simulated_actions", [])
        payload = {
            "schema_version": "1.0",
            "track": TRACK_NAME,
            "capability": CAPABILITY,
            "mode": getattr(self.actuator, "mode", "unknown"),
            "status": status,
            "terminal_state": terminal_state.value,
            "reason": reason,
            "tube": {
                "tube_id": self.config.tube_id,
                "fixture_id": self.config.fixture_id,
            },
            "policy": {
                "min_confidence": self.config.min_confidence,
                "max_retries": self.config.max_retries,
                "open_before_pipetting": True,
                "closed_before_complete": True,
            },
            "gates": {
                "open_verified": open_verified,
                "pipetting_allowed": pipetting_allowed,
                "closed_verified": closed_verified,
            },
            "verification": {
                "open": (
                    self.open_observation.to_dict()
                    if self.open_observation else None
                ),
                "closed": (
                    self.closed_observation.to_dict()
                    if self.closed_observation else None
                ),
            },
            "execution": {
                "backend": self.actuator.backend_name,
                "provenance": getattr(
                    self.actuator,
                    "execution_provenance",
                    "unknown",
                ),
                "simulated_motion_actions": len(simulated_actions),
                "physical_hardware_commands": (
                    self.actuator.physical_hardware_commands
                ),
                "fault_injection": getattr(self.actuator, "fault", "unknown"),
            },
            "recoveries": self.recoveries,
            "events": self.events,
        }
        return seal_track_c_receipt(payload)

    def _stop(
        self,
        reason: str,
        *,
        open_verified: bool = False,
        pipetting_allowed: bool = False,
    ) -> dict[str, Any]:
        self._event(WorkflowState.STOPPED, "decision", False, reason)
        return self._receipt(
            status="STOPPED_SAFE",
            terminal_state=WorkflowState.STOPPED,
            reason=reason,
            pipetting_allowed=pipetting_allowed,
            open_verified=open_verified,
            closed_verified=False,
        )

    def run(self) -> dict[str, Any]:
        initial_ok, _ = self._observe(
            WorkflowState.OBSERVE_CAPPED,
            "initial",
            CapState.CAPPED,
        )
        if not initial_ok:
            return self._stop("initial capped state was not verified")

        if not self._retry_action(
            WorkflowState.LOCALIZE,
            "localize",
            "re-localize from the fixture fiducial before moving",
        ):
            return self._stop("tube localization failed after retry limit")

        if not self._retry_action(
            WorkflowState.GRASP_CAP,
            "grasp_cap",
            "open the gripper, re-localize, and retry the cap grasp",
        ):
            return self._stop("cap grasp failed after retry limit")

        open_verified = False
        for attempt in range(self.config.max_retries + 1):
            motion = self._act(WorkflowState.UNSCREW, "uncap")
            if motion.passed:
                open_verified, observation = self._observe(
                    WorkflowState.VERIFY_OPEN,
                    "open",
                    CapState.UNCAPPED,
                )
                self.open_observation = observation
                if open_verified:
                    break
            if attempt < self.config.max_retries:
                self._recover(
                    WorkflowState.VERIFY_OPEN,
                    "open state is not verified; re-localize, regrasp, and retry",
                )
                self._act(WorkflowState.LOCALIZE, "localize")
                self._act(WorkflowState.GRASP_CAP, "grasp_cap")
        if not open_verified:
            return self._stop("cap-off verification failed after retry limit")

        handoff = self._act(
            WorkflowState.PRESENT_FOR_PIPETTING,
            "present_for_pipetting",
        )
        if not handoff.passed:
            return self._stop(
                "liquid-handler presentation failed",
                open_verified=True,
            )
        self._event(
            WorkflowState.PRESENT_FOR_PIPETTING,
            "decision",
            True,
            "verified tube opening unlocked the liquid-handling handoff",
            {"pipetting_allowed": True},
        )

        closed_verified = False
        for attempt in range(self.config.max_retries + 1):
            motion = self._act(WorkflowState.RECAP, "recap")
            if motion.passed:
                closed_verified, observation = self._observe(
                    WorkflowState.VERIFY_CLOSED,
                    "closed",
                    CapState.CAPPED,
                )
                self.closed_observation = observation
                if closed_verified:
                    break
            if attempt < self.config.max_retries:
                self._recover(
                    WorkflowState.VERIFY_CLOSED,
                    "closure is ambiguous; re-seat the cap and verify again",
                )
        if not closed_verified:
            return self._stop(
                "cap-closed verification failed after retry limit",
                open_verified=True,
                pipetting_allowed=True,
            )

        self._event(
            WorkflowState.COMPLETE,
            "decision",
            True,
            "tube access and closure are both independently verified",
        )
        return self._receipt(
            status="VERIFIED_COMPLETE",
            terminal_state=WorkflowState.COMPLETE,
            reason="verified open, liquid-handling handoff, verified closed",
            pipetting_allowed=True,
            open_verified=True,
            closed_verified=True,
        )


def track_c_receipt_sha256(receipt: dict[str, Any]) -> str:
    payload = dict(receipt)
    payload.pop("integrity", None)
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def seal_track_c_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(receipt)
    sealed["integrity"] = {
        "algorithm": "sha256",
        "digest": track_c_receipt_sha256(sealed),
    }
    return sealed


def verify_track_c_receipt(receipt: dict[str, Any]) -> bool:
    try:
        integrity = receipt.get("integrity", {})
        digest_ok = (
            integrity.get("algorithm") == "sha256"
            and integrity.get("digest") == track_c_receipt_sha256(receipt)
        )
        gates = receipt.get("gates", {})
        invariants_ok = not (
            gates.get("pipetting_allowed") and not gates.get("open_verified")
        )
        if receipt.get("status") == "VERIFIED_COMPLETE":
            invariants_ok = invariants_ok and bool(
                gates.get("open_verified") and gates.get("closed_verified")
            )
        events = receipt.get("events", [])
        sequence_ok = isinstance(events, list) and all(
            isinstance(event, dict) and event.get("sequence") == index
            for index, event in enumerate(events, start=1)
        )
        return bool(digest_ok and invariants_ok and sequence_ok)
    except (AttributeError, TypeError, ValueError, OverflowError):
        return False


def run_simulated_tube_access(
    fault: str = "none",
    config: TubeAccessConfig | None = None,
) -> dict[str, Any]:
    cell = SimulatedTubeCell(fault=fault)
    camera = SimulatedCapCamera(cell)
    controller = VerifiedTubeAccessController(cell, camera, config)
    return controller.run()


def save_track_c_receipt(receipt: dict[str, Any], path: str | Path) -> Path:
    if not verify_track_c_receipt(receipt):
        raise TrackCError("refusing to save a Track C receipt with invalid integrity")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(receipt, indent=2) + "\n")
    return destination
