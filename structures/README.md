# TEM-1 structure packet

This directory pins two experimental RCSB Protein Data Bank entries for the
organizer-requested pre-event structure preparation.

## Selected references

- **1XPB** is the primary wild-type receptor reference. RCSB reports one
  unmutated TEM-1 chain at 1.90 angstrom resolution. Its sulfate occupies the
  catalytic cleft and is useful for checking pocket placement.
- **1ERO** is a pocket-validation reference containing a designed boronic acid
  inhibitor covalently linked to catalytic Ser70. It is not the default docking
  receptor.

The validation script checks the downloaded file digests, entry IDs,
resolution, chain and residue counts, and the canonical TEM-1 catalytic
residues Ser70, Lys73, Ser130, Glu166, Asn170, and Lys234.

```bash
python scripts/validate_tem1_structures.py
```

## Before any docking run

The committed files are validated experimental references, not prepared
docking receptors. When the organizer releases the compound structures:

1. Confirm whether the library contains 2D structures, 3D conformers, names
   only, or organizer-provided scores.
2. Choose protonation and tautomer rules appropriate to the organizer's assay
   conditions.
3. Select retained waters and ions deliberately. Do not silently delete the
   1XPB sulfate or use it as part of the receptor.
4. Add hydrogens, charges, and atom types with one named, versioned tool.
5. Define the search box from the catalytic pocket and validate it by
   recovering the 1ERO reference pose or an organizer-approved equivalent.
6. Record tool versions, receptor digest, ligand-input digest, box coordinates,
   random seed, and every failed ligand.
7. Convert scores into `priority_score` only if every library member was
   processed under the same contract. Record the method in `priority_source`.
8. Treat docking as a round-1 prioritization signal, not as measured inhibition
   and not as proof of binding.

If the compound library remains names-only or time is short, use the shipped
deterministic coverage plan. A complete physical loop is worth more than an
unvalidated docking leaderboard.

## Primary sources

- [RCSB PDB 1XPB](https://www.rcsb.org/structure/1XPB)
- [RCSB PDB 1ERO](https://www.rcsb.org/structure/1ERO)
