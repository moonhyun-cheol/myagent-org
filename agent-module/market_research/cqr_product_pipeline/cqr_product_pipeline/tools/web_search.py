"""Web search tools (Phase 2)."""

from __future__ import annotations

from langchain_core.tools import BaseTool


def create_duckduckgo_tool() -> BaseTool:
    from langchain_community.tools import DuckDuckGoSearchResults

    return DuckDuckGoSearchResults(max_results=5, output_format="list")
