"""bay-hack: a verified Track A TEM-1 inhibitor loop.

The primary challenge path confirms cell-free TEM-1 expression, screens
replicated compounds with kinetic controls, and uses round 1 evidence to design
a dose-response confirmation round. The original generic loop still composes
the di-omics stack:

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

__version__ = "0.4.0"
__all__ = [
    "WorldModel", "Bench", "DBTLLoop", "RoundLog",
    "rhodamine_gate", "cv_checkpoint", "conformal_gate",
    "Transfer", "LiquidHandlingPlan", "FollowUpAction", "LiquidHandlingAssay",
    "TrustRecord", "TrustLedger",
    "is_well_name",
]
