"""Stdlib validation for the pinned TEM-1 experimental structures."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ACTIVE_SITE_RESIDUES = {
    70: "SER",
    73: "LYS",
    130: "SER",
    166: "GLU",
    170: "ASN",
    234: "LYS",
}


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_pdb(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    lines = source.read_text().splitlines()
    header = next((line for line in lines if line.startswith("HEADER")), "")
    titles = [
        line[10:].strip()
        for line in lines
        if line.startswith("TITLE")
    ]
    resolution = None
    for line in lines:
        if line.startswith("REMARK   2 RESOLUTION."):
            match = re.search(r"([0-9]+(?:\.[0-9]+)?) ANGSTROMS", line)
            if match:
                resolution = float(match.group(1))
                break

    residues: set[tuple[str, int, str, str]] = set()
    heterogens: set[tuple[str, str, int]] = set()
    atom_count = 0
    for line in lines:
        record = line[:6].strip()
        if record not in {"ATOM", "HETATM"}:
            continue
        try:
            residue_number = int(line[22:26])
        except ValueError:
            continue
        residue_name = line[17:20].strip()
        chain = line[21].strip() or "_"
        if record == "ATOM":
            atom_count += 1
            residues.add(
                (chain, residue_number, line[26].strip(), residue_name)
            )
        elif residue_name != "HOH":
            heterogens.add((residue_name, chain, residue_number))

    residue_lookup = {
        (chain, number): name
        for chain, number, _insertion, name in residues
    }
    return {
        "path": str(source),
        "pdb_id": header[62:66].strip(),
        "title": " ".join(titles),
        "resolution_angstrom": resolution,
        "chains": sorted({chain for chain, *_ in residues}),
        "protein_residue_count": len(residues),
        "protein_atom_count": atom_count,
        "residue_lookup": residue_lookup,
        "heterogens": sorted(heterogens),
        "seqadv_count": sum(line.startswith("SEQADV") for line in lines),
        "modres": [
            line.strip() for line in lines if line.startswith("MODRES")
        ],
        "links": [
            line.strip() for line in lines if line.startswith("LINK")
        ],
        "sha256": sha256(source),
    }


def validate_entry(base: Path, entry: dict[str, Any]) -> dict[str, Any]:
    path = base / str(entry["file"])
    errors: list[str] = []
    if not path.is_file():
        return {
            "pdb_id": entry["pdb_id"],
            "role": entry["role"],
            "passed": False,
            "errors": [f"missing structure file: {path}"],
        }

    observed = inspect_pdb(path)
    if observed["pdb_id"] != entry["pdb_id"]:
        errors.append(
            f"PDB ID is {observed['pdb_id']}, expected {entry['pdb_id']}"
        )
    if observed["sha256"] != entry["sha256"]:
        errors.append("SHA-256 digest does not match the pinned RCSB download")
    expected_resolution = float(entry["resolution_angstrom"])
    if observed["resolution_angstrom"] is None or abs(
        observed["resolution_angstrom"] - expected_resolution
    ) > 0.001:
        errors.append(
            f"resolution is {observed['resolution_angstrom']}, "
            f"expected {expected_resolution}"
        )
    if observed["chains"] != entry["protein_chains"]:
        errors.append(
            f"protein chains are {observed['chains']}, "
            f"expected {entry['protein_chains']}"
        )
    if observed["protein_residue_count"] != entry["protein_residue_count"]:
        errors.append(
            f"protein residue count is {observed['protein_residue_count']}, "
            f"expected {entry['protein_residue_count']}"
        )
    if entry.get("require_no_seqadv") and observed["seqadv_count"]:
        errors.append("unexpected SEQADV mutation record")

    chain = str(entry["active_site_chain"])
    active_site = {
        str(number): observed["residue_lookup"].get((chain, number))
        for number in ACTIVE_SITE_RESIDUES
    }
    for number, expected_name in ACTIVE_SITE_RESIDUES.items():
        observed_name = observed["residue_lookup"].get((chain, number))
        if observed_name != expected_name:
            errors.append(
                f"active-site residue {chain}{number} is {observed_name}, "
                f"expected {expected_name}"
            )

    observed_heterogens = {
        name for name, _chain, _number in observed["heterogens"]
    }
    for required in entry.get("required_heterogens", []):
        if required not in observed_heterogens:
            errors.append(f"required reference heterogen is missing: {required}")

    return {
        "pdb_id": entry["pdb_id"],
        "role": entry["role"],
        "passed": not errors,
        "errors": errors,
        "file": str(path),
        "sha256": observed["sha256"],
        "resolution_angstrom": observed["resolution_angstrom"],
        "protein_chains": observed["chains"],
        "protein_residue_count": observed["protein_residue_count"],
        "active_site": active_site,
        "heterogens": sorted(observed_heterogens),
    }


def validate_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    manifest = json.loads(manifest_path.read_text())
    results = [
        validate_entry(manifest_path.parent, entry)
        for entry in manifest["entries"]
    ]
    return {
        "schema_version": manifest["schema_version"],
        "source": manifest["source"],
        "passed": all(result["passed"] for result in results),
        "entries": results,
        "claim": (
            "structures validated as pinned experimental references; "
            "not docking-ready receptors"
        ),
    }
