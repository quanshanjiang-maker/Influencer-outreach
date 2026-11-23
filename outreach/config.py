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
    search: dict = field(default_factory=dict)
    scoring: dict = field(default_factory=dict)
    sheet_tabs: dict = field(default_factory=dict)

    # secrets (from env)
    anthropic_api_key: str | None = None
    twitterapi_io_key: str | None = None
    youtube_api_key: str | None = None
    apify_token: str | None = None
    hunter_api_key: str | None = None
    millionverifier_api_key: str | None = None
    easykol_api_key: str | None = None
    easykol_api_email: str | None = None
    providers: dict = field(default_factory=dict)
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
        search=raw.get("search", {}),
        scoring=raw.get("scoring", {}),
        sheet_tabs=raw.get("sheet_tabs", {}),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        twitterapi_io_key=os.getenv("TWITTERAPI_IO_KEY"),
        youtube_api_key=os.getenv("YOUTUBE_API_KEY"),
        apify_token=os.getenv("APIFY_TOKEN"),
        hunter_api_key=os.getenv("HUNTER_API_KEY"),
        millionverifier_api_key=os.getenv("MILLIONVERIFIER_API_KEY"),
        easykol_api_key=os.getenv("EASYKOL_API_KEY"),
        easykol_api_email=os.getenv("EASYKOL_API_EMAIL"),
        providers=raw.get("providers", {}),
        google_service_account=_load_service_account(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")),
        sheet_id=os.getenv("SHEET_ID"),
    )
