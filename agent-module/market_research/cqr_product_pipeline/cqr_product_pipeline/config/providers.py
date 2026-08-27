import logging
import os

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from cqr_product_pipeline.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

# `localhost` can resolve to ::1 where the Ollama daemon is not listening,
# which surfaces as httpx ConnectError and silently degrades reports.
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"


def resolve_ollama_base_url(settings: Settings) -> str:
    return (
        settings.ollama_base_url
        or os.getenv("OLLAMA_BASE_URL")
        or DEFAULT_OLLAMA_BASE_URL
    )


def pick_ollama_model(want: str, installed: list[str]) -> str:
    """Choose an installed tag: exact → same family → first installed."""
    if not installed or want in installed:
        return want
    family = want.split(":")[0]
    for name in installed:
        if name.split(":")[0] == family:
            return name
    logger.warning("ollama model %r not installed; using %r", want, installed[0])
    return installed[0]


def _installed_ollama_models(base_url: str) -> list[str]:
    try:
        import httpx

        resp = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=5.0)
        resp.raise_for_status()
        models = resp.json().get("models") or []
        return [str(m.get("name")) for m in models if m.get("name")]
    except Exception as exc:
        logger.warning("ollama tag listing failed (%s); using configured model", exc)
        return []


def get_chat_model(settings: Settings | None = None) -> BaseChatModel:
    settings = settings or get_settings()
    if settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama

        base_url = resolve_ollama_base_url(settings)
        model = pick_ollama_model(
            settings.llm_model, _installed_ollama_models(base_url)
        )
        return ChatOllama(model=model, base_url=base_url)
    if settings.llm_provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ModuleNotFoundError as exc:
            # Host always prefers OpenAI-compatible gateway (OWUI). If venv was
            # built without langchain-openai, fail clearly so bootstrap is fixed —
            # silent Ollama fallback burns the chat budget on a too-small local model.
            raise ModuleNotFoundError(
                "langchain_openai is not installed in this Python environment. "
                "Re-run tools/bootstrap-pipeline-venv.ps1 -Root <CQR_PA> (or: "
                "pip install langchain-openai) so market research can use the "
                "injected OPENAI_BASE_URL/KEY. "
                f"Original: {exc}"
            ) from exc

        # Host app injects OPENAI_BASE_URL/KEY so the pipeline reuses the same
        # OpenAI-compatible gateway (OWUI) as chat instead of a local model.
        kwargs: dict = {
            "model": settings.llm_model,
            "timeout": settings.llm_timeout_seconds,
            "max_retries": 1,
        }
        base_url = settings.openai_base_url or os.getenv("OPENAI_BASE_URL")
        if base_url:
            kwargs["base_url"] = base_url.rstrip("/")
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            kwargs["api_key"] = api_key
        return ChatOpenAI(**kwargs)
    if settings.llm_provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "langchain_anthropic is not installed — pip install langchain-anthropic "
                f"or set LLM_PROVIDER=openai/ollama. Original: {exc}"
            ) from exc

        return ChatAnthropic(model=settings.llm_model)
    raise ValueError(f"Unsupported llm_provider: {settings.llm_provider}")


def get_embeddings(settings: Settings | None = None) -> Embeddings:
    settings = settings or get_settings()
    if settings.embedding_provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(model=settings.embedding_model)
    if settings.embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=settings.embedding_model)
    if settings.embedding_provider == "chromadb":
        from langchain_community.embeddings import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name=settings.embedding_model)
    raise ValueError(f"Unsupported embedding_provider: {settings.embedding_provider}")


def get_search_tool(settings: Settings | None = None) -> BaseTool | None:
    settings = settings or get_settings()
    if settings.search_provider == "duckduckgo":
        from cqr_product_pipeline.tools.web_search import create_duckduckgo_tool

        return create_duckduckgo_tool()
    if settings.search_provider == "tavily":
        from langchain_community.tools.tavily_search import TavilySearchResults

        return TavilySearchResults(max_results=5)
    return None
