from pathlib import Path
import os

PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def _find_manager_root() -> Path:
    env_root = os.environ.get("CQR_MANAGER_ROOT")
    if env_root:
        return Path(env_root).resolve()

    for parent in PACKAGE_ROOT.parents:
        if (parent / "skills" / "manifest.json").exists() and (
            parent / "market_research"
        ).is_dir():
            return parent

    raise FileNotFoundError(
        "Cannot locate organization pack root. Set CQR_MANAGER_ROOT to agent-module."
    )


MANAGER_ROOT = _find_manager_root()
MARKET_RESEARCH_ROOT = MANAGER_ROOT / "market_research"
PROJECT_ROOT = MARKET_RESEARCH_ROOT / "cqr_product_pipeline"
DATA_PATH = MANAGER_ROOT / "data"
CHROMA_PATH = MARKET_RESEARCH_ROOT / ".chroma" / "cqr"
CHECKPOINT_PATH = MARKET_RESEARCH_ROOT / ".checkpoints" / "pipeline.db"
