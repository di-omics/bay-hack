"""Pinned TEM-1 structures stay identifiable, intact, and claim-limited."""
import json
from pathlib import Path

from bayhack.structure import validate_manifest


ROOT = Path(__file__).resolve().parents[1]


def test_pinned_tem1_structures_pass_manifest_validation():
    result = validate_manifest(ROOT / "structures" / "manifest.json")
    assert result["passed"]
    assert len(result["entries"]) == 2
    assert result["entries"][0]["pdb_id"] == "1XPB"
    assert result["entries"][0]["active_site"]["70"] == "SER"
    assert "not docking-ready receptors" in result["claim"]


def test_structure_digest_tampering_fails_closed(tmp_path):
    source = ROOT / "structures"
    manifest = json.loads((source / "manifest.json").read_text())
    manifest["entries"] = [manifest["entries"][0]]
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "1XPB.pdb").write_bytes(
        (source / "1XPB.pdb").read_bytes() + b"REMARK tampered\n"
    )
    result = validate_manifest(tmp_path / "manifest.json")
    assert not result["passed"]
    assert any(
        "SHA-256" in error for error in result["entries"][0]["errors"]
    )
