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
from .assay import (
    FollowUpAction, LiquidHandlingAssay, LiquidHandlingPlan, Transfer,
    is_well_name,
)
from .ledger import TrustLedger, TrustRecord

# NOTE: the Zeon bridge is imported on demand (`from bayhack.zeon_bridge import
# ZeonArmBackend`), never here -- so `import bayhack` never attempts to load
# pylabrobot/plr_lr (repository rule: keep the sim path dependency-free).

__version__ = "0.3.0"
__all__ = [
    "WorldModel", "Bench", "DBTLLoop", "RoundLog",
    "rhodamine_gate", "cv_checkpoint", "conformal_gate",
    "Transfer", "LiquidHandlingPlan", "FollowUpAction", "LiquidHandlingAssay",
    "TrustRecord", "TrustLedger",
    "is_well_name",
]
