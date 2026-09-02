"""Operator/environment settings. This file has no machine-specific hosts."""

from __future__ import annotations

import json
import os
from pathlib import Path

DISABLED = frozenset({"0", "off", "none", "false", "disabled"})


def find_repo_root(start: Path | None = None) -> Path:
    start = (start or Path.cwd()).resolve()
    for path in [start, *start.parents]:
        if (path / "manifest.json").is_file() and (path / "agent-module").is_dir():
            return path
    here = Path(__file__).resolve().parent.parent
    if (here / "manifest.json").is_file() and (here / "agent-module").is_dir():
        return here
    raise FileNotFoundError("organization module repo root not found")


def load_operator_config(root: Path | None = None) -> dict:
    root = root or find_repo_root()
    path = root / "_local" / "operator.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def first_nonempty(*values: object) -> str:
    for value in values:
        text = str(value or "").strip()
        if text and text.lower() not in DISABLED:
            return text
    return ""


def _nas(root: Path | None = None) -> dict:
    cfg = load_operator_config(root)
    nas = cfg.get("nas")
    return nas if isinstance(nas, dict) else {}


def brand_manual_url(root: Path | None = None) -> str:
    cfg = load_operator_config(root)
    hub = cfg.get("hub") if isinstance(cfg.get("hub"), dict) else {}
    return first_nonempty(
        os.environ.get("MY_AGENT_BRAND_MANUAL_URL"),
        hub.get("brand_manual_url") if isinstance(hub, dict) else None,
        cfg.get("brand_manual_url"),
    )


def product_data_base_url(root: Path | None = None) -> str:
    cfg = load_operator_config(root)
    hub = cfg.get("hub") if isinstance(cfg.get("hub"), dict) else {}
    return first_nonempty(
        os.environ.get("MY_AGENT_PRODUCT_DATA_BASE_URL"),
        hub.get("product_data_base_url") if isinstance(hub, dict) else None,
        cfg.get("product_data_base_url"),
    )


def openclaw_adapter_base_url(root: Path | None = None) -> str:
    cfg = load_operator_config(root)
    hub = cfg.get("hub") if isinstance(cfg.get("hub"), dict) else {}
    return first_nonempty(
        os.environ.get("MY_AGENT_OPENCLAW_ADAPTER_BASE_URL"),
        os.environ.get("OPENCLAW_ADAPTER_BASE_URL"),
        hub.get("openclaw_adapter_base_url") if isinstance(hub, dict) else None,
        cfg.get("openclaw_adapter_base_url"),
    )


def deployment_phase(root: Path | None = None) -> str:
    cfg = load_operator_config(root)
    return first_nonempty(cfg.get("deployment_phase")) or "operator_pc"


def nas_root(root: Path | None = None) -> Path | None:
    text = first_nonempty(os.environ.get("CQR_NAS_ROOT"), _nas(root).get("root"))
    return Path(text) if text else None


def nas_alllisting(root: Path | None = None) -> Path | None:
    nas = _nas(root)
    text = first_nonempty(os.environ.get("CQR_NAS_ALLLISTING"), nas.get("alllisting"))
    return Path(text) if text else None


def nas_dev_xlsx(root: Path | None = None) -> Path | None:
    nas = _nas(root)
    text = first_nonempty(os.environ.get("CQR_DEV_XLSX"), nas.get("dev_xlsx"))
    return Path(text) if text else None


def nas_po_dir(root: Path | None = None) -> Path | None:
    nas = _nas(root)
    text = first_nonempty(os.environ.get("CQR_PO_DIR"), nas.get("po_clothing"))
    return Path(text) if text else None


def listing_file(root: Path | None = None) -> Path | None:
    text = first_nonempty(os.environ.get("CQR_LISTING"))
    if text:
        path = Path(text)
        return path if path.is_file() else None
    return None


def resolve_listing_file(root: Path | None = None) -> Path | None:
    root = root or find_repo_root()
    explicit = listing_file(root)
    if explicit:
        return explicit
    candidates: list[Path] = []
    cache = root / "_local" / "cache" / "listings"
    if cache.is_dir():
        candidates.extend(cache.glob("*alllisting*.txt"))
        candidates.extend(cache.glob("*.txt"))
    folder = nas_alllisting(root)
    if folder is not None:
        try:
            if folder.exists():
                candidates.extend(folder.glob("*alllisting*.txt"))
                candidates.extend(folder.glob("*.txt"))
        except OSError:
            pass
    files = [path for path in candidates if path.is_file()]
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]
