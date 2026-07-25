"""bay-hack: verified physical skills for scientific automation.

The primary Track C path uncaps a tube, independently verifies cap removal,
presents the opening for liquid handling, then recaps and verifies closure. The
Track A TEM-1 loop remains available as a complete fallback.

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
from .track_c import (
    CapObservation,
    CapState,
    SimulatedCapCamera,
    SimulatedTubeCell,
    TubeAccessConfig,
    VerifiedTubeAccessController,
    run_simulated_tube_access,
    verify_track_c_receipt,
)

# NOTE: the Zeon bridge is imported on demand (`from bayhack.zeon_bridge import
# ZeonArmBackend`), never here -- so `import bayhack` never attempts to load
# pylabrobot/plr_lr (repository rule: keep the sim path dependency-free).

__version__ = "0.5.0"
__all__ = [
    "WorldModel", "Bench", "DBTLLoop", "RoundLog",
    "rhodamine_gate", "cv_checkpoint", "conformal_gate",
    "Transfer", "LiquidHandlingPlan", "FollowUpAction", "LiquidHandlingAssay",
    "TrustRecord", "TrustLedger",
    "is_well_name",
    "CapObservation", "CapState", "SimulatedCapCamera", "SimulatedTubeCell",
    "TubeAccessConfig",
    "VerifiedTubeAccessController", "run_simulated_tube_access",
    "verify_track_c_receipt",
]
