"""bay-hack -- Track-A demo glue for the AI for Science World Models Hack.

Composes @di-omics repos into one closed loop:
  plan (plr-epigenome sow) -> design (ml-bio-eval world model) ->
  build/test (plr-mcp) -> verify (Rhodamine gate + lab-cv) ->
  learn (conformal gate) -> repeat, then bridge to Zeon (zeon_bridge).
"""
from .loop import (
    WorldModel, Bench, DBTLLoop, RoundLog,
    rhodamine_gate, cv_checkpoint, conformal_gate,
)
from .zeon_bridge import ZeonArmBackend, bridge_notes

__version__ = "0.1.0"
__all__ = [
    "WorldModel", "Bench", "DBTLLoop", "RoundLog",
    "rhodamine_gate", "cv_checkpoint", "conformal_gate",
    "ZeonArmBackend", "bridge_notes",
]
