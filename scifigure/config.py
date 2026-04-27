from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - dotenv is optional at runtime
    load_dotenv = None


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "SciFigure AI Studio"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4.1-mini"
    timeout: int = 45
    export_dpi: int = 600


ENV_KEYS = {
    "api_key": "AI_FIGURE_API_KEY",
    "base_url": "AI_FIGURE_BASE_URL",
    "model": "AI_FIGURE_MODEL",
    "timeout": "AI_FIGURE_TIMEOUT",
}


def _env_path() -> Path:
    return Path.cwd() / ".env"


def load_config() -> AppConfig:
    env_path = _env_path()
    if load_dotenv and env_path.exists():
        # override=True lets the in-app settings dialog take effect after saving.
        load_dotenv(env_path, override=True)

    timeout_raw = os.getenv("AI_FIGURE_TIMEOUT", "45")
    try:
        timeout = int(timeout_raw)
    except ValueError:
        timeout = 45

    return AppConfig(
        api_key=os.getenv("AI_FIGURE_API_KEY", "").strip(),
        base_url=os.getenv("AI_FIGURE_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        model=os.getenv("AI_FIGURE_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini",
        timeout=timeout,
    )


def save_config(config: AppConfig) -> Path:
    """Persist LLM settings to .env without logging or exposing secrets."""
    env_path = _env_path()
    lines = [
        "# SciFigure AI Studio model settings",
        "# OpenAI example: AI_FIGURE_BASE_URL=https://api.openai.com/v1, AI_FIGURE_MODEL=gpt-4.1-mini",
        "# DeepSeek example: AI_FIGURE_BASE_URL=https://api.deepseek.com, AI_FIGURE_MODEL=deepseek-chat",
        f"AI_FIGURE_API_KEY={config.api_key}",
        f"AI_FIGURE_BASE_URL={config.base_url.rstrip('/')}",
        f"AI_FIGURE_MODEL={config.model}",
        f"AI_FIGURE_TIMEOUT={int(config.timeout)}",
        "",
    ]
    env_path.write_text("\n".join(lines), encoding="utf-8")
    os.environ["AI_FIGURE_API_KEY"] = config.api_key
    os.environ["AI_FIGURE_BASE_URL"] = config.base_url.rstrip("/")
    os.environ["AI_FIGURE_MODEL"] = config.model
    os.environ["AI_FIGURE_TIMEOUT"] = str(int(config.timeout))
    return env_path
