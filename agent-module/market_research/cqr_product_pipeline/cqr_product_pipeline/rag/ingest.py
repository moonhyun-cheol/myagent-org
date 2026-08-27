"""Ingest MANAGER_ROOT/data markdown into Chroma collections."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter

from cqr_product_pipeline.config.paths import CHROMA_PATH, DATA_PATH
from cqr_product_pipeline.config.settings import Settings, get_settings
from cqr_product_pipeline.rag.collections import COLLECTIONS, all_ingest_files

LINE_HINTS = ("Covert", "Liberator", "Expedition", "Sapper")


def _detect_lines(text: str) -> str:
    found = [line for line in LINE_HINTS if line.lower() in text.lower()]
    return ",".join(found) if found else "general"


def _chunk_document(
    text: str,
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    return splitter.split_text(text)


def _chunk_id(source_path: str, index: int, content: str) -> str:
    digest = hashlib.sha256(f"{source_path}:{index}:{content[:120]}".encode()).hexdigest()[:16]
    return f"{Path(source_path).stem}-{index}-{digest}"


def ingest_corpus(
    *,
    data_root: Path | None = None,
    chroma_path: Path | None = None,
    settings: Settings | None = None,
    rebuild: bool = False,
) -> dict[str, int]:
    settings = settings or get_settings()
    data_root = data_root or settings.data_path
    chroma_path = chroma_path or settings.chroma_path

    if rebuild and chroma_path.exists():
        import shutil

        shutil.rmtree(chroma_path)

    chroma_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_path))
    embed_fn = embedding_functions.DefaultEmbeddingFunction()

    counts: dict[str, int] = {}
    files = all_ingest_files(data_root)
    if not files:
        raise FileNotFoundError(f"No ingest files found under {data_root}")

    for spec in COLLECTIONS:
        collection = client.get_or_create_collection(
            name=spec.name,
            embedding_function=embed_fn,
            metadata={"doc_type": spec.doc_type},
        )
        if rebuild:
            existing = collection.get(include=[])
            if existing["ids"]:
                collection.delete(ids=existing["ids"])

        collection_count = 0
        spec_files = [(c, p, d) for c, p, d in files if c == spec.name]
        for _collection, path, doc_type in spec_files:
            text = path.read_text(encoding="utf-8")
            rel_path = str(path.relative_to(data_root)).replace("\\", "/")
            line_hint = _detect_lines(text)
            chunks = _chunk_document(
                text,
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            )
            ids: list[str] = []
            documents: list[str] = []
            metadatas: list[dict] = []
            for idx, chunk in enumerate(chunks):
                chunk = re.sub(r"\\Nas\\[^\s]+", "[local-source]", chunk, flags=re.I)
                ids.append(_chunk_id(rel_path, idx, chunk))
                documents.append(chunk)
                metadatas.append(
                    {
                        "source_path": rel_path,
                        "doc_type": doc_type,
                        "collection": spec.name,
                        "line": line_hint,
                        "chunk_index": idx,
                    }
                )
            if ids:
                collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
                collection_count += len(ids)

        counts[spec.name] = collection_count

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest CQR data corpus into Chroma")
    parser.add_argument("--rebuild", action="store_true", help="Drop and rebuild all collections")
    parser.add_argument("--data", type=Path, default=None, help="Override data root path")
    args = parser.parse_args()

    settings = get_settings()
    data_root = args.data or settings.data_path or DATA_PATH
    counts = ingest_corpus(data_root=data_root, rebuild=args.rebuild, settings=settings)
    print(f"Ingest complete → {settings.chroma_path or CHROMA_PATH}")
    for name, count in counts.items():
        print(f"  {name}: {count} chunks")


if __name__ == "__main__":
    main()
