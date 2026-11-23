"""Minimal Apify client: run an Actor synchronously and return its dataset items."""
from __future__ import annotations

import requests

API = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"


def run_actor(token: str, actor: str, run_input: dict, timeout: int = 300) -> list[dict]:
    """actor is 'owner~name', e.g. 'apify~instagram-scraper'."""
    r = requests.post(API.format(actor=actor), params={"token": token}, json=run_input, timeout=timeout)
    r.raise_for_status()
    items = r.json()
    return [i for i in items if isinstance(i, dict) and not i.get("error")]
