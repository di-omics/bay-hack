"""Reader CSV and camera colorimetry adapters stay portable and calibrated."""
import csv

import pytest

from bayhack.assay import LiquidHandlingAssay
from bayhack.measurements import (
    CameraWellMeasurement,
    CsvWellMeasurement,
    LinearSignalCalibration,
    MeasurementError,
    PlateCalibration,
    parse_well,
    project_color_signal,
    render_calibration_overlay,
)


def test_parse_well_uses_standard_plate_coordinates():
    assert parse_well("A1") == (0, 0)
    assert parse_well("h12") == (7, 11)
    with pytest.raises(MeasurementError):
        parse_well("Q99")


def test_linear_reader_calibration_normalizes_and_clamps():
    calibration = LinearSignalCalibration(raw_low=100.0, raw_high=1100.0)
    assert calibration.normalize(100.0) == 0.0
    assert calibration.normalize(600.0) == 0.5
    assert calibration.normalize(1500.0) == 1.0


def test_invalid_plate_calibration_fails_closed(tmp_path):
    calibration = PlateCalibration(100, 100, 50, 50)
    with pytest.raises(MeasurementError, match="positive width"):
        calibration.save(tmp_path / "invalid.json")


def test_csv_adapter_reads_the_planned_well(tmp_path):
    path = tmp_path / "reader.csv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["well", "rfu"])
        writer.writeheader()
        writer.writerows([
            {"well": "B1", "rfu": 600},
            {"well": "C1", "rfu": 900},
        ])
    adapter = CsvWellMeasurement(
        path,
        calibration=LinearSignalCalibration(raw_low=100, raw_high=1100),
    )
    plan = LiquidHandlingAssay().plan(1, "seed", 0.2)
    assert adapter(plan, {}) == 0.5
    assert adapter.provenance == "measured:reader-csv"
    assert adapter.last_evidence["well"] == "B1"
    assert adapter.last_evidence["raw_value"] == 600.0
    assert len(adapter.last_evidence["sha256"]) == 64


def test_uncalibrated_raw_reader_values_are_refused(tmp_path):
    path = tmp_path / "reader.csv"
    path.write_text("well,value\nB1,9000\n")
    with pytest.raises(MeasurementError, match="normalized"):
        CsvWellMeasurement(path).read_well("B1")


def test_color_projection_uses_in_frame_low_and_high_references():
    assert project_color_signal((128, 128, 128), (255, 255, 255), (1, 1, 1)) \
        == pytest.approx(0.5, abs=0.01)
    with pytest.raises(MeasurementError, match="insufficient contrast"):
        project_color_signal((10, 10, 10), (20, 20, 20), (20, 20, 20))


def test_camera_adapter_reads_synthetic_plate_fixture(tmp_path):
    image_module = pytest.importorskip("PIL.Image")
    draw_module = pytest.importorskip("PIL.ImageDraw")
    image = image_module.new("RGB", (1200, 800), (225, 225, 225))
    draw = draw_module.Draw(image)
    calibration = PlateCalibration(0, 0, 1200, 800)
    colors = {
        "A1": (30, 80, 200),
        "A2": (240, 240, 240),
        "B1": (135, 160, 220),
    }
    for well, color in colors.items():
        x, y = calibration.well_center(well)
        draw.ellipse((x - 34, y - 34, x + 34, y + 34), fill=color)
    path = tmp_path / "plate.png"
    image.save(path)
    adapter = CameraWellMeasurement(path, calibration)
    value = adapter.read_well("B1")
    assert value == pytest.approx(0.5, abs=0.06)
    assert adapter.provenance == "measured:camera"
    assert adapter.last_evidence["well"] == "B1"
    assert adapter.last_evidence["low_reference"]["well"] == "A2"
    assert adapter.last_evidence["high_reference"]["well"] == "A1"
    assert len(adapter.last_evidence["sha256"]) == 64
    overlay = render_calibration_overlay(
        path, calibration, tmp_path / "calibration-overlay.png"
    )
    assert overlay.exists() and overlay.stat().st_size > 0
