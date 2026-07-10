"""
Configuration module — loads/saves API settings from config.json.
"""

import json
from pathlib import Path
from utils import app_dir


CONFIG_FILE = Path(app_dir()) / "config.json"

DEFAULT_CONFIG = {
    "api_key": "",
    "api_url": "https://api.openai.com/v1/chat/completions",
    "model": "gpt-4o-mini",
}


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def get_api_key() -> str:
    return load_config().get("api_key", "")


def get_api_url() -> str:
    return load_config().get("api_url", DEFAULT_CONFIG["api_url"])


def get_model() -> str:
    return load_config().get("model", DEFAULT_CONFIG["model"])
