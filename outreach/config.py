"""Load config.yaml and environment variables."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass
class Config:
    models: dict = field(default_factory=dict)
    data_source: str = "twitterapi_io"
    search: dict = field(default_factory=dict)
    sheet_tabs: dict = field(default_factory=dict)

    # secrets (from env)
    anthropic_api_key: str | None = None
    twitterapi_io_key: str | None = None
    google_service_account: dict | None = None
    sheet_id: str | None = None


def _load_service_account(value: str | None) -> dict | None:
    if not value:
        return None
    value = value.strip()
    if value.startswith("{"):
        return json.loads(value)
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text())
    raise FileNotFoundError(f"GOOGLE_SERVICE_ACCOUNT_JSON points to missing file: {value}")


def load_config(path: str | os.PathLike = "config.yaml") -> Config:
    load_dotenv()
    p = Path(path)
    if not p.exists():
        p = Path("config.example.yaml")
    raw = yaml.safe_load(p.read_text()) or {}
    return Config(
        models=raw.get("models", {}),
        data_source=raw.get("data_source", "twitterapi_io"),
        search=raw.get("search", {}),
        sheet_tabs=raw.get("sheet_tabs", {}),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        twitterapi_io_key=os.getenv("TWITTERAPI_IO_KEY"),
        google_service_account=_load_service_account(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")),
        sheet_id=os.getenv("SHEET_ID"),
    )
