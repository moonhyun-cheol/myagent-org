"""RAG collection → source file mapping."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cqr_product_pipeline.config.paths import DATA_PATH

CollectionName = str


@dataclass(frozen=True)
class CollectionSpec:
    name: CollectionName
    relative_paths: tuple[str, ...]
    doc_type: str


COLLECTIONS: tuple[CollectionSpec, ...] = (
    CollectionSpec(
        name="brand",
        relative_paths=(
            "codex/CQR_BRAND_CONCEPT.md",
            "SLOGAN_VOICE.md",
            "CQR_BRAND_IMAGE_PLAYBOOK.md",
        ),
        doc_type="brand",
    ),
    CollectionSpec(
        name="catalog",
        relative_paths=(
            "BRAND_INDEX.md",
            "cqr_development_direction.txt",
            "brand_active_report.json",
            "model_catalog.json",
            "new_lineup_index.txt",
            "model_row_index.txt",
        ),
        doc_type="catalog",
    ),
    CollectionSpec(
        name="product_spec",
        relative_paths=(
            "PRODUCT_DEV_SPEC_ENGINE.md",
            "COLOR_CODE.md",
            "color_code_index.txt",
            "po_color_index.json",
        ),
        doc_type="product_spec",
    ),
    CollectionSpec(
        name="process",
        relative_paths=("NAS_05_DEV_FOLDER_INDEX.md",),
        doc_type="process",
    ),
)


def resolve_source_paths(data_root: Path | None = None) -> dict[CollectionName, list[Path]]:
    root = data_root or DATA_PATH
    mapping: dict[CollectionName, list[Path]] = {}
    for spec in COLLECTIONS:
        paths = [root / rel for rel in spec.relative_paths]
        mapping[spec.name] = [p for p in paths if p.exists()]
    return mapping


def all_ingest_files(data_root: Path | None = None) -> list[tuple[CollectionName, Path, str]]:
    """Return (collection, path, doc_type) for every file to ingest."""
    root = data_root or DATA_PATH
    files: list[tuple[CollectionName, Path, str]] = []
    for spec in COLLECTIONS:
        for rel in spec.relative_paths:
            path = root / rel
            if path.exists():
                files.append((spec.name, path, spec.doc_type))
    return files
