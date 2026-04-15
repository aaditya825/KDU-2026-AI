"""Typed settings and configuration loading helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.core.config import constants


def _deep_merge(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_env_file(path: str | Path) -> dict[str, str]:
    """Parse a dotenv-style file without requiring external dependencies."""

    env_path = Path(path)
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values


def load_yaml_file(path: str | Path) -> dict[str, Any]:
    """Load YAML configuration lazily so imports stay lightweight."""

    config_path = Path(path)
    if not config_path.exists():
        return {}

    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - exercised only when PyYAML is missing.
        raise RuntimeError("PyYAML is required to load config/config.yaml.") from exc

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at {config_path}, received {type(data).__name__}.")
    return data


@dataclass(slots=True)
class ChunkingSettings:
    strategy: str = constants.DEFAULT_CHUNKING_STRATEGY
    chunk_size: int = constants.DEFAULT_CHUNK_SIZE
    overlap: int = constants.DEFAULT_CHUNK_OVERLAP
    section_aware: bool = True


@dataclass(slots=True)
class EmbeddingSettings:
    provider: str = constants.DEFAULT_EMBEDDING_PROVIDER
    model_name: str = "all-MiniLM-L6-v2"
    batch_size: int = 32


@dataclass(slots=True)
class RetrievalSettings:
    semantic_top_k: int = constants.DEFAULT_SEMANTIC_TOP_K
    keyword_top_k: int = constants.DEFAULT_KEYWORD_TOP_K
    fused_top_k: int = constants.DEFAULT_FUSED_TOP_K
    rerank_top_k: int = constants.DEFAULT_FUSED_TOP_K
    final_top_k: int = constants.DEFAULT_FINAL_TOP_K
    fusion_strategy: str = constants.DEFAULT_FUSION_STRATEGY
    reranker_name: str = constants.DEFAULT_RERANKER
    reranker_required: bool = True


@dataclass(slots=True)
class GenerationSettings:
    provider: str = constants.DEFAULT_LLM_PROVIDER
    model_name: str = "gemini-2.5-flash"
    temperature: float = 0.1
    max_tokens: int = 800
    request_timeout_seconds: float = 60.0


@dataclass(slots=True)
class StorageSettings:
    vector_store: str = constants.DEFAULT_VECTOR_STORE
    vector_store_path: str = "data/vector_db"
    keyword_store: str = constants.DEFAULT_KEYWORD_STORE
    keyword_store_path: str = "data/keyword_index"
    metadata_store_path: str = "data/processed/metadata.json"


@dataclass(slots=True)
class UISettings:
    framework: str = "streamlit"
    page_title: str = constants.APP_NAME
    show_metrics: bool = True
    upload_directory: str = "data/raw/uploads"


@dataclass(slots=True)
class LoggingSettings:
    config_path: str = "config/logging.yaml"
    level: str = "INFO"


@dataclass(slots=True)
class APISettings:
    gemini_api_key: str | None = None
    openai_api_key: str | None = None


@dataclass(slots=True)
class AppSettings:
    """Central application settings respecting the documented precedence contract."""

    app_name: str = constants.APP_NAME
    environment: str = "development"
    data_dir: str = "data"
    chunking: ChunkingSettings = field(default_factory=ChunkingSettings)
    embeddings: EmbeddingSettings = field(default_factory=EmbeddingSettings)
    retrieval: RetrievalSettings = field(default_factory=RetrievalSettings)
    generation: GenerationSettings = field(default_factory=GenerationSettings)
    storage: StorageSettings = field(default_factory=StorageSettings)
    ui: UISettings = field(default_factory=UISettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    api: APISettings = field(default_factory=APISettings)

    @classmethod
    def from_mapping(
        cls,
        config_data: dict[str, Any] | None = None,
        *,
        env_data: dict[str, str] | None = None,
        session_overrides: dict[str, Any] | None = None,
    ) -> "AppSettings":
        payload = _deep_merge({}, config_data or {})
        payload = _deep_merge(payload, session_overrides or {})

        api_settings = APISettings(
            gemini_api_key=(env_data or {}).get("GEMINI_API_KEY"),
            openai_api_key=(env_data or {}).get("OPENAI_API_KEY"),
        )
        return cls(
            app_name=payload.get("app_name", constants.APP_NAME),
            environment=payload.get("environment", "development"),
            data_dir=payload.get("data_dir", "data"),
            chunking=ChunkingSettings(**payload.get("chunking", {})),
            embeddings=EmbeddingSettings(**payload.get("embeddings", {})),
            retrieval=RetrievalSettings(**payload.get("retrieval", {})),
            generation=GenerationSettings(**payload.get("generation", {})),
            storage=StorageSettings(**payload.get("storage", {})),
            ui=UISettings(**payload.get("ui", {})),
            logging=LoggingSettings(**payload.get("logging", {})),
            api=api_settings,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_settings(
    config_path: str | Path = "config/config.yaml",
    env_path: str | Path = ".env",
    *,
    session_overrides: dict[str, Any] | None = None,
) -> AppSettings:
    """Load settings using config defaults, environment secrets, and session overrides."""

    config_data = load_yaml_file(config_path)
    env_data = load_env_file(env_path)
    return AppSettings.from_mapping(
        config_data,
        env_data=env_data,
        session_overrides=session_overrides,
    )
