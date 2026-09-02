"""RAG collection → source file mapping.

Local agent-module/data/ indexes are retired. Ingest is disabled until
product_data_base_url feeds are wired; use live API + slash lookups in chat.
"""

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


COLLECTIONS: tuple[CollectionSpec, ...] = ()


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
