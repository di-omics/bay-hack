"""Venue-neutral measurement adapters for plate readers and plate images.

The closed loop accepts any callable with the shape ``measurement(plan, readout)``.
This module supplies two portable adapters:

* ``CsvWellMeasurement`` reads normalized values or calibrated raw RFU by well.
* ``CameraWellMeasurement`` reads one plate image using A2 as the low reference
  and A1 as the high reference by default.

Image support imports Pillow lazily. The core simulator remains standard-library
only and never labels its synthetic response as measured.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .assay import ROWS, LiquidHandlingPlan, is_well_name


class MeasurementError(RuntimeError):
    """A physical measurement could not be parsed or calibrated safely."""


def file_sha256(path: str | Path) -> str:
    """Return the SHA-256 digest of one source evidence file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_well(well: str) -> tuple[int, int]:
    """Return zero-based row and column indexes for a 96-well position."""
    value = str(well).upper()
    if not is_well_name(value):
        raise MeasurementError(f"invalid 96-well position: {well!r}")
    return ROWS.index(value[0]), int(value[1:]) - 1


@dataclass(frozen=True)
class LinearSignalCalibration:
    """Map a raw reader value onto the scientific model's 0 to 1 scale."""

    raw_low: float
    raw_high: float
    clamp: bool = True

    def normalize(self, raw_value: float) -> float:
        value = float(raw_value)
        if not math.isfinite(value):
            raise MeasurementError("measurement is not finite")
        span = self.raw_high - self.raw_low
        if abs(span) < 1e-12:
            raise MeasurementError("reader calibration has zero span")
        normalized = (value - self.raw_low) / span
        if self.clamp:
            return max(0.0, min(1.0, normalized))
        if not 0.0 <= normalized <= 1.0:
            raise MeasurementError("calibrated measurement is outside [0, 1]")
        return normalized


@dataclass(frozen=True)
class PlateCalibration:
    """Plate bounding box and in-frame reference wells for camera colorimetry."""

    left: float
    top: float
    right: float
    bottom: float
    low_well: str = "A2"
    high_well: str = "A1"
    sample_radius_fraction: float = 0.24

    def verify(self) -> dict:
        reasons: list[str] = []
        if self.right <= self.left or self.bottom <= self.top:
            reasons.append("plate box must have positive width and height")
        if not is_well_name(self.low_well) or not is_well_name(self.high_well):
            reasons.append("reference wells must be valid 96-well positions")
        if self.low_well == self.high_well:
            reasons.append("low and high reference wells must differ")
        if not 0.05 <= self.sample_radius_fraction <= 0.45:
            reasons.append("sample radius fraction must be between 0.05 and 0.45")
        return {"passed": not reasons, "reasons": reasons}

    def well_center(self, well: str) -> tuple[float, float]:
        verdict = self.verify()
        if not verdict["passed"]:
            raise MeasurementError("; ".join(verdict["reasons"]))
        row, column = parse_well(well)
        cell_width = (self.right - self.left) / 12.0
        cell_height = (self.bottom - self.top) / 8.0
        return (
            self.left + (column + 0.5) * cell_width,
            self.top + (row + 0.5) * cell_height,
        )

    def sample_radius(self) -> float:
        cell_width = (self.right - self.left) / 12.0
        cell_height = (self.bottom - self.top) / 8.0
        return min(cell_width, cell_height) * self.sample_radius_fraction

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlateCalibration":
        if "plate_box" in payload:
            left, top, right, bottom = payload["plate_box"]
            payload = {**payload, "left": left, "top": top,
                       "right": right, "bottom": bottom}
            payload.pop("plate_box", None)
        calibration = cls(**payload)
        verdict = calibration.verify()
        if not verdict["passed"]:
            raise MeasurementError("; ".join(verdict["reasons"]))
        return calibration

    @classmethod
    def load(cls, path: str | Path) -> "PlateCalibration":
        return cls.from_dict(json.loads(Path(path).read_text()))

    def save(self, path: str | Path) -> Path:
        verdict = self.verify()
        if not verdict["passed"]:
            raise MeasurementError("; ".join(verdict["reasons"]))
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
        return destination


def project_color_signal(
    sample_rgb: tuple[float, float, float],
    low_rgb: tuple[float, float, float],
    high_rgb: tuple[float, float, float],
) -> float:
    """Project an RGB sample onto the low-to-high reference color axis."""
    axis = tuple(high - low for low, high in zip(low_rgb, high_rgb))
    denominator = sum(component * component for component in axis)
    if denominator < 1.0:
        raise MeasurementError("camera reference wells have insufficient contrast")
    offset = tuple(sample - low for sample, low in zip(sample_rgb, low_rgb))
    value = sum(a * b for a, b in zip(offset, axis)) / denominator
    return max(0.0, min(1.0, value))


def sample_well_rgb(
    image_or_path: Any,
    calibration: PlateCalibration,
    well: str,
) -> tuple[float, float, float]:
    """Return the mean RGB value from a circular well region."""
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - depends on optional package
        raise MeasurementError(
            "camera measurement requires Pillow: pip install pillow"
        ) from exc

    close_image = isinstance(image_or_path, (str, Path))
    image = Image.open(image_or_path) if close_image else image_or_path
    try:
        rgb_image = image.convert("RGB")
        center_x, center_y = calibration.well_center(well)
        radius = calibration.sample_radius()
        x0 = max(0, int(math.floor(center_x - radius)))
        x1 = min(rgb_image.width - 1, int(math.ceil(center_x + radius)))
        y0 = max(0, int(math.floor(center_y - radius)))
        y1 = min(rgb_image.height - 1, int(math.ceil(center_y + radius)))
        if x0 > x1 or y0 > y1:
            raise MeasurementError(f"well {well} falls outside the image")
        pixels: list[tuple[int, int, int]] = []
        radius_squared = radius * radius
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if (x - center_x) ** 2 + (y - center_y) ** 2 <= radius_squared:
                    pixels.append(rgb_image.getpixel((x, y)))
        if not pixels:
            raise MeasurementError(f"well {well} has no sampled pixels")
        return tuple(sum(pixel[channel] for pixel in pixels) / len(pixels)
                     for channel in range(3))
    finally:
        if close_image:
            image.close()


class CsvWellMeasurement:
    """Read a well value from a CSV exported by a camera or plate reader."""

    def __init__(
        self,
        path: str | Path,
        *,
        calibration: LinearSignalCalibration | None = None,
        well_column: str = "well",
        value_column: str | None = None,
        provenance: str = "measured:reader-csv",
    ):
        self.path = Path(path)
        self.calibration = calibration
        self.well_column = well_column
        self.value_column = value_column
        self.provenance = provenance
        self.last_evidence: dict[str, Any] = {}

    def _values(self) -> dict[str, float]:
        if not self.path.exists():
            raise MeasurementError(f"reader CSV does not exist: {self.path}")
        with self.path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames or []
            if self.well_column not in fields:
                raise MeasurementError(
                    f"reader CSV is missing the {self.well_column!r} column"
                )
            value_column = self.value_column
            if value_column is None:
                value_column = next(
                    (name for name in ("value", "signal", "fluorescence", "rfu")
                     if name in fields),
                    None,
                )
            if value_column is None or value_column not in fields:
                raise MeasurementError(
                    "reader CSV needs one value column: value, signal, fluorescence, or rfu"
                )
            values: dict[str, float] = {}
            for row in reader:
                well = str(row[self.well_column]).upper()
                if not is_well_name(well):
                    raise MeasurementError(f"reader CSV contains invalid well {well!r}")
                try:
                    values[well] = float(row[value_column])
                except (TypeError, ValueError) as exc:
                    raise MeasurementError(
                        f"reader CSV contains a non-numeric value for {well}"
                    ) from exc
        return values

    def read_well(self, well: str) -> float:
        normalized_well = str(well).upper()
        values = self._values()
        if normalized_well not in values:
            raise MeasurementError(f"reader CSV has no value for {normalized_well}")
        raw_value = values[normalized_well]
        if self.calibration is not None:
            normalized = self.calibration.normalize(raw_value)
            self.last_evidence = {
                "path": str(self.path),
                "sha256": file_sha256(self.path),
                "well": normalized_well,
                "raw_value": raw_value,
                "normalized_value": normalized,
                "calibration": asdict(self.calibration),
            }
            return normalized
        if not math.isfinite(raw_value) or not 0.0 <= raw_value <= 1.0:
            raise MeasurementError(
                "uncalibrated reader values must already be normalized to [0, 1]"
            )
        self.last_evidence = {
            "path": str(self.path),
            "sha256": file_sha256(self.path),
            "well": normalized_well,
            "raw_value": raw_value,
            "normalized_value": raw_value,
            "calibration": "input already normalized",
        }
        return raw_value

    def __call__(self, plan: LiquidHandlingPlan, _readout: Any = None) -> float:
        return self.read_well(plan.destination)


class CameraWellMeasurement:
    """Measure a destination well from a plate image using in-frame references."""

    provenance = "measured:camera"

    def __init__(
        self,
        image_pattern: str | Path,
        calibration: PlateCalibration | str | Path,
    ):
        self.image_pattern = str(image_pattern)
        self.calibration = (
            calibration
            if isinstance(calibration, PlateCalibration)
            else PlateCalibration.load(calibration)
        )
        self.last_evidence: dict[str, Any] = {}

    def image_path(self, well: str, run_id: int = 0) -> Path:
        return Path(self.image_pattern.format(well=well, run_id=run_id))

    def read_well(self, well: str, run_id: int = 0) -> float:
        path = self.image_path(well, run_id)
        if not path.exists():
            raise MeasurementError(f"plate image does not exist: {path}")
        low_rgb = sample_well_rgb(path, self.calibration, self.calibration.low_well)
        high_rgb = sample_well_rgb(path, self.calibration, self.calibration.high_well)
        sample_rgb = sample_well_rgb(path, self.calibration, well)
        value = project_color_signal(sample_rgb, low_rgb, high_rgb)
        self.last_evidence = {
            "path": str(path),
            "sha256": file_sha256(path),
            "well": str(well).upper(),
            "low_reference": {
                "well": self.calibration.low_well,
                "mean_rgb": [round(component, 3) for component in low_rgb],
            },
            "high_reference": {
                "well": self.calibration.high_well,
                "mean_rgb": [round(component, 3) for component in high_rgb],
            },
            "sample_mean_rgb": [round(component, 3) for component in sample_rgb],
            "normalized_value": value,
            "calibration": self.calibration.to_dict(),
        }
        return value

    def __call__(self, plan: LiquidHandlingPlan, _readout: Any = None) -> float:
        return self.read_well(plan.destination, plan.run_id)


def render_calibration_overlay(
    image_path: str | Path,
    calibration: PlateCalibration,
    output_path: str | Path,
) -> Path:
    """Draw the plate box and all sampled well regions for visual calibration."""
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:  # pragma: no cover - depends on optional package
        raise MeasurementError(
            "camera overlay requires Pillow: pip install pillow"
        ) from exc
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle(
        (calibration.left, calibration.top, calibration.right, calibration.bottom),
        outline=(92, 174, 90),
        width=3,
    )
    radius = calibration.sample_radius()
    for row in ROWS:
        for column in range(1, 13):
            well = f"{row}{column}"
            x, y = calibration.well_center(well)
            color = (
                (47, 111, 214)
                if well == calibration.high_well
                else (111, 130, 116)
                if well == calibration.low_well
                else (92, 174, 90)
            )
            draw.ellipse((x - radius, y - radius, x + radius, y + radius),
                         outline=color, width=2)
    for well in (calibration.high_well, calibration.low_well):
        x, y = calibration.well_center(well)
        draw.text((x + radius + 2, y - radius), well, fill=(40, 55, 42))
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)
    image.close()
    return destination


def _parse_box(value: str) -> tuple[float, float, float, float]:
    try:
        parts = tuple(float(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("box coordinates must be numeric") from exc
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("box must be left,top,right,bottom")
    return parts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="calibrate and check bay-hack physical measurement adapters"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    calibration_parser = subparsers.add_parser(
        "calibrate", help="write plate geometry for camera colorimetry"
    )
    calibration_parser.add_argument("--box", required=True, type=_parse_box)
    calibration_parser.add_argument("--output", required=True)
    calibration_parser.add_argument("--low-well", default="A2")
    calibration_parser.add_argument("--high-well", default="A1")
    calibration_parser.add_argument("--radius", type=float, default=0.24)

    csv_parser = subparsers.add_parser("csv", help="read one well from a reader CSV")
    csv_parser.add_argument("path")
    csv_parser.add_argument("well")
    csv_parser.add_argument("--raw-low", type=float)
    csv_parser.add_argument("--raw-high", type=float)

    camera_parser = subparsers.add_parser(
        "camera", help="read one well from a calibrated plate image"
    )
    camera_parser.add_argument("image")
    camera_parser.add_argument("calibration")
    camera_parser.add_argument("well")

    overlay_parser = subparsers.add_parser(
        "overlay", help="render sampled well regions over a plate image"
    )
    overlay_parser.add_argument("image")
    overlay_parser.add_argument("calibration")
    overlay_parser.add_argument("output")

    args = parser.parse_args()
    if args.command == "calibrate":
        left, top, right, bottom = args.box
        calibration = PlateCalibration(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            low_well=args.low_well.upper(),
            high_well=args.high_well.upper(),
            sample_radius_fraction=args.radius,
        )
        destination = calibration.save(args.output)
        print(json.dumps({"passed": True, "calibration": str(destination)}))
        return

    if args.command == "csv":
        if (args.raw_low is None) != (args.raw_high is None):
            parser.error("--raw-low and --raw-high must be supplied together")
        calibration = (
            LinearSignalCalibration(args.raw_low, args.raw_high)
            if args.raw_low is not None
            else None
        )
        adapter = CsvWellMeasurement(args.path, calibration=calibration)
        value = adapter.read_well(args.well)
        print(json.dumps({"well": args.well.upper(), "value": value,
                          "provenance": adapter.provenance,
                          "evidence": adapter.last_evidence}))
        return

    if args.command == "overlay":
        calibration = PlateCalibration.load(args.calibration)
        destination = render_calibration_overlay(
            args.image, calibration, args.output
        )
        print(json.dumps({"passed": True, "overlay": str(destination)}))
        return

    calibration = PlateCalibration.load(args.calibration)
    adapter = CameraWellMeasurement(args.image, calibration)
    value = adapter.read_well(args.well)
    print(json.dumps({"well": args.well.upper(), "value": value,
                      "provenance": adapter.provenance,
                      "evidence": adapter.last_evidence}))


if __name__ == "__main__":
    main()
