"""Concrete liquid-handling protocol for the Track A demo.

The world model optimizes a one-factor assay. This module turns each abstract
design value into an auditable plate plan with real wells and real volumes.
The portable fallback uses one 96-well plate:

* A1: assay stock
* A2: diluent
* B1 onward: proposed experiments
* H12: accepted product for the follow-up step

At 40 uL per experiment, the expected six-run demo consumes about 130 uL of
stock and 110 uL of diluent. Both sources fit in ordinary plate wells with
headroom, so the fallback can run without a reservoir.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


ROWS = "ABCDEFGH"
COLUMNS = tuple(str(column) for column in range(1, 13))
DESTINATION_WELLS = tuple(
    f"{row}{column}"
    for column in range(1, 13)
    for row in "BCDEFG"
)
MAX_EXPERIMENTS = 47  # two unique tips per run, with H12 reserved for follow-up


def is_well_name(value: str) -> bool:
    """Return whether a string names one position on a standard 96-well plate."""
    if not isinstance(value, str) or len(value) < 2:
        return False
    row, column = value[0].upper(), value[1:]
    return row in ROWS and column in COLUMNS


@dataclass(frozen=True)
class Transfer:
    """One source-to-destination liquid transfer."""

    reagent: str
    source: str
    destination: str
    volume_ul: float
    tip: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class LiquidHandlingPlan:
    """A verified physical plan for one proposed experiment."""

    run_id: int
    phase: str
    design_x: float
    destination: str
    total_volume_ul: float
    stock_ul: float
    diluent_ul: float
    transfers: tuple[Transfer, ...]
    mix_cycles: int = 3
    readout: str = "fluorescence_or_camera"

    def verify(
        self,
        *,
        well_capacity_ul: float = 200.0,
        min_transfer_ul: float = 1.0,
    ) -> dict:
        reasons: list[str] = []
        if not 0.0 <= self.design_x <= 1.0:
            reasons.append("design_x must be within [0, 1]")
        if not is_well_name(self.destination):
            reasons.append("destination is not a valid 96-well position")
        if self.total_volume_ul <= 0:
            reasons.append("planned total volume must be positive")
        if self.stock_ul < 0 or self.diluent_ul < 0:
            reasons.append("component volumes must not be negative")
        if abs(self.stock_ul + self.diluent_ul - self.total_volume_ul) > 0.11:
            reasons.append("component volumes do not sum to the planned total")
        if not self.transfers:
            reasons.append("plan contains no transfers")
        if self.destination in {t.source for t in self.transfers}:
            reasons.append("destination overlaps a source well")
        if self.total_volume_ul > well_capacity_ul:
            reasons.append("destination would exceed the well capacity")
        if abs(sum(t.volume_ul for t in self.transfers) - self.total_volume_ul) > 0.11:
            reasons.append("transfer volumes do not sum to the planned total")
        if len({t.tip for t in self.transfers}) != len(self.transfers):
            reasons.append("each liquid must use a unique tip")
        reagent_volumes: dict[str, float] = {}
        for transfer in self.transfers:
            reagent_volumes[transfer.reagent] = (
                reagent_volumes.get(transfer.reagent, 0.0) + transfer.volume_ul
            )
            if not is_well_name(transfer.source):
                reasons.append(f"{transfer.reagent} source is not a valid well")
            if transfer.destination != self.destination:
                reasons.append(
                    f"{transfer.reagent} destination does not match the plan"
                )
            if not is_well_name(transfer.tip):
                reasons.append(f"{transfer.reagent} tip is not a valid rack position")
            if transfer.volume_ul < min_transfer_ul:
                reasons.append(
                    f"{transfer.reagent} transfer is below {min_transfer_ul:g} uL"
                )
            if transfer.volume_ul > 200.0:
                reasons.append(f"{transfer.reagent} transfer exceeds 200 uL")
        if abs(reagent_volumes.get("assay_stock", 0.0) - self.stock_ul) > 0.11:
            reasons.append("assay stock transfer does not match plan metadata")
        if abs(reagent_volumes.get("diluent", 0.0) - self.diluent_ul) > 0.11:
            reasons.append("diluent transfer does not match plan metadata")
        return {"passed": not reasons, "reasons": reasons}

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["transfers"] = [t.to_dict() for t in self.transfers]
        return payload


@dataclass(frozen=True)
class FollowUpAction:
    """Track A follow-up: promote the accepted well to a product well."""

    source: str
    destination: str
    volume_ul: float
    tip: str
    reason: str

    def verify(self, available_ul: float, product_well: str) -> dict:
        reasons: list[str] = []
        if not is_well_name(self.source) or not is_well_name(self.destination):
            reasons.append("follow-up source or destination is not a valid well")
        if not is_well_name(self.tip):
            reasons.append("follow-up tip is not a valid rack position")
        if self.source == self.destination:
            reasons.append("follow-up source and destination are identical")
        if self.destination != product_well:
            reasons.append("follow-up destination is not the reserved product well")
        if not 0 < self.volume_ul <= available_ul:
            reasons.append("follow-up volume is not available in the accepted well")
        return {"passed": not reasons, "reasons": reasons}

    def to_dict(self) -> dict:
        return asdict(self)


class LiquidHandlingAssay:
    """Map world-model proposals onto a portable single-plate assay."""

    def __init__(
        self,
        *,
        stock_well: str = "A1",
        diluent_well: str = "A2",
        product_well: str = "H12",
        total_volume_ul: float = 40.0,
        follow_up_volume_ul: float = 20.0,
        well_capacity_ul: float = 200.0,
        min_transfer_ul: float = 1.0,
    ):
        self.stock_well = stock_well
        self.diluent_well = diluent_well
        self.product_well = product_well
        self.total_volume_ul = total_volume_ul
        self.follow_up_volume_ul = follow_up_volume_ul
        self.well_capacity_ul = well_capacity_ul
        self.min_transfer_ul = min_transfer_ul

    @staticmethod
    def tip_for(index: int) -> str:
        """Return a unique 96-tip-rack position for a zero-based transfer."""
        if not 0 <= index < 96:
            raise ValueError("tip index exceeds a 96-position rack")
        return f"{ROWS[index % 8]}{index // 8 + 1}"

    def plan(self, run_id: int, phase: str, design_x: float) -> LiquidHandlingPlan:
        if not 1 <= run_id <= MAX_EXPERIMENTS:
            raise ValueError("run_id exceeds the portable plate layout")
        stock = round(self.total_volume_ul * design_x, 2)
        diluent = round(self.total_volume_ul - stock, 2)
        destination = DESTINATION_WELLS[run_id - 1]
        transfers: list[Transfer] = []
        next_tip = (run_id - 1) * 2
        if stock > 0:
            transfers.append(
                Transfer(
                    reagent="assay_stock",
                    source=self.stock_well,
                    destination=destination,
                    volume_ul=stock,
                    tip=self.tip_for(next_tip),
                )
            )
            next_tip += 1
        if diluent > 0:
            transfers.append(
                Transfer(
                    reagent="diluent",
                    source=self.diluent_well,
                    destination=destination,
                    volume_ul=diluent,
                    tip=self.tip_for(next_tip),
                )
            )
        return LiquidHandlingPlan(
            run_id=run_id,
            phase=phase,
            design_x=design_x,
            destination=destination,
            total_volume_ul=self.total_volume_ul,
            stock_ul=stock,
            diluent_ul=diluent,
            transfers=tuple(transfers),
        )

    def verify(self, plan: LiquidHandlingPlan) -> dict:
        return plan.verify(
            well_capacity_ul=self.well_capacity_ul,
            min_transfer_ul=self.min_transfer_ul,
        )

    def follow_up(self, accepted: LiquidHandlingPlan) -> FollowUpAction:
        return FollowUpAction(
            source=accepted.destination,
            destination=self.product_well,
            volume_ul=self.follow_up_volume_ul,
            tip="H12",
            reason="promote the accepted formulation to the downstream product well",
        )
