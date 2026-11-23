"""Step 3: find and verify a contact email for each scored creator.

Order: email already supplied (EasyKOL) -> bio text -> creator's website/link-in-bio
page -> Hunter domain search (optional) -> MillionVerifier check (optional).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

log = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Normalise common obfuscations before matching:
#   name [at] gmail [dot] com, name(at)gmail.com, name at gmail dot com
_BRACKET_AT = re.compile(r"\s*[\[\(\{<]\s*(?:at|@)\s*[\]\)\}>]\s*", re.IGNORECASE)
_BRACKET_DOT = re.compile(r"\s*[\[\(\{<]\s*dot\s*[\]\)\}>]\s*", re.IGNORECASE)
_WORDY = re.compile(r"\b([A-Za-z0-9._%+-]+)\s+at\s+([A-Za-z0-9-]+)\s+dot\s+([A-Za-z]{2,})\b", re.IGNORECASE)
JUNK_DOMAINS = ("example.com", "sentry.io", "wixpress.com", "domain.com", "email.com", "yourdomain.com")
JUNK_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
SOCIAL_HOSTS = ("x.com", "twitter.com", "instagram.com", "tiktok.com", "youtube.com", "youtu.be",
                "facebook.com", "linkedin.com", "threads.net", "t.co")
LINK_PAGES = ("linktr.ee", "beacons.ai", "bio.link", "stan.store", "carrd.co", "lnk.bio", "linkin.bio")
UA = {"User-Agent": "Mozilla/5.0 (compatible; outreach-email-finder/0.1)"}


def _clean(e: str) -> str | None:
    e = e.strip().strip(".").lower()
    if e.endswith(JUNK_SUFFIXES) or any(e.endswith("@" + d) or e.endswith("." + d) for d in JUNK_DOMAINS):
        return None
    return e


def emails_in_text(text: str) -> list[str]:
    """Plain and lightly obfuscated emails, in order of appearance, de-duplicated."""
    text = _WORDY.sub(r"\1@\2.\3", text or "")
    text = _BRACKET_DOT.sub(".", _BRACKET_AT.sub("@", text))
    out, seen = [], set()
    for m in EMAIL_RE.finditer(text):
        c = _clean(m.group(0))
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _host(url: str) -> str:
    h = urlparse(url if "://" in url else "https://" + url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def emails_on_page(url: str, timeout: int = 10) -> list[str]:
    try:
        r = requests.get(url if "://" in url else "https://" + url, headers=UA, timeout=timeout)
        if r.status_code >= 400 or "html" not in r.headers.get("content-type", "html"):
            return []
        return emails_in_text(r.text.replace("mailto:", " "))
    except requests.RequestException as e:
        log.info("fetch %s failed: %s", url, e)
        return []


def hunter_domain_search(domain: str, api_key: str, timeout: int = 15) -> str | None:
    """Best-confidence personal/generic email Hunter knows for a domain (1 credit per call)."""
    r = requests.get("https://api.hunter.io/v2/domain-search",
                     params={"domain": domain, "api_key": api_key, "limit": 10}, timeout=timeout)
    if r.status_code != 200:
        log.info("hunter %s: HTTP %s", domain, r.status_code)
        return None
    emails = sorted((r.json().get("data") or {}).get("emails") or [],
                    key=lambda e: e.get("confidence") or 0, reverse=True)
    return emails[0]["value"].lower() if emails else None


def millionverifier(email: str, api_key: str, timeout: int = 20) -> str:
    """Returns ok | catch_all | unknown | invalid | disposable | error."""
    try:
        r = requests.get("https://api.millionverifier.com/api/v3/",
                         params={"api": api_key, "email": email, "timeout": 10}, timeout=timeout)
        return str(r.json().get("result") or "unknown").lower()
    except (requests.RequestException, ValueError) as e:
        log.info("verify %s failed: %s", email, e)
        return "error"


@dataclass
class EmailResult:
    email: str = ""
    source: str = ""     # easykol | bio | website | hunter
    status: str = ""     # ok | catch_all | unknown | invalid | disposable | unverified | not_found


SENDABLE = {"ok", "catch_all", "unverified"}


def find_email(existing: str, existing_source: str, bio: str, website: str,
               hunter_key: str | None = None) -> EmailResult:
    if existing:
        return EmailResult(existing.lower(), existing_source or "sheet")
    bio_emails = emails_in_text(bio)
    if bio_emails:
        return EmailResult(bio_emails[0], "bio")
    if website and _host(website) not in SOCIAL_HOSTS:
        page = emails_on_page(website)
        if page:
            return EmailResult(page[0], "website")
        host = _host(website)
        if hunter_key and not any(host.endswith(lp) for lp in LINK_PAGES):
            hit = hunter_domain_search(host, hunter_key)
            if hit:
                return EmailResult(hit, "hunter")
    return EmailResult(status="not_found")


def verify(result: EmailResult, verifier_key: str | None) -> EmailResult:
    if not result.email:
        return result
    result.status = millionverifier(result.email, verifier_key) if verifier_key else "unverified"
    return result
