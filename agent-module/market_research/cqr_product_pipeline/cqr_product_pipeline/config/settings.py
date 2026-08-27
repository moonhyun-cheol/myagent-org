from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from cqr_product_pipeline.config.paths import CHECKPOINT_PATH, CHROMA_PATH, DATA_PATH


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: Literal["ollama", "openai", "anthropic"] = "ollama"
    llm_model: str = "qwen3.6:35b"
    ollama_base_url: str | None = None
    openai_base_url: str | None = None
    llm_timeout_seconds: float = 180.0

    use_llm_scoring: bool = True
    llm_fallback_heuristic: bool = True

    embedding_provider: Literal["chromadb", "ollama", "openai"] = "chromadb"
    embedding_model: str = "all-MiniLM-L6-v2"

    search_provider: Literal["duckduckgo", "tavily", "none"] = "duckduckgo"

    # Report prose language. Search queries stay English (Amazon US evidence) regardless.
    report_language: Literal["ko", "en"] = "ko"

    chroma_path: Path = Field(default=CHROMA_PATH)
    checkpoint_path: Path = Field(default=CHECKPOINT_PATH)
    data_path: Path = Field(default=DATA_PATH)

    max_research_tool_calls: int = 10
    hitl_max_iterations: int = 3
    k_per_collection: int = 4

    chunk_size: int = 800
    chunk_overlap: int = 120

    brand_weight: float = 0.30
    manufacturing_weight: float = 0.40
    cannibalization_weight: float = 0.30


@lru_cache
def get_settings() -> Settings:
    return Settings()
