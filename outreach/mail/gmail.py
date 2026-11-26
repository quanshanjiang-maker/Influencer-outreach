"""Gmail API mailbox (works for personal Gmail and Google Workspace).

Auth uses an OAuth refresh token for the sending account. Create one once with
`python -m outreach gmail-auth` (see README).
"""
from __future__ import annotations

import base64
import re
import time

import requests

from .base import Mailbox, Reply, SentMessage

API = "https://gmail.googleapis.com/gmail/v1/users/me"
SCOPES = ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/spreadsheets"]  # one token can also open the sheet


class GmailMailbox(Mailbox):
    def __init__(self, address: str, from_name: str, client_id: str, client_secret: str, refresh_token: str):
        self.address, self.from_name = address, from_name
        self._creds = {"client_id": client_id.strip(), "client_secret": client_secret.strip(),
                       "refresh_token": refresh_token.strip(), "grant_type": "refresh_token"}
        self._token, self._expires = "", 0.0

    def _auth(self) -> dict:
        if time.time() > self._expires - 60:
            r = requests.post("https://oauth2.googleapis.com/token", data=self._creds, timeout=20)
            if not r.ok:  # Google's error code (e.g. invalid_grant / invalid_client) says which secret is wrong
                try:
                    err = r.json()
                except ValueError:
                    err = {}
                raise RuntimeError(f"Google token refresh failed ({r.status_code}): "
                                   f"{err.get('error', '')} {err.get('error_description', '')}".strip())
            d = r.json()
            self._token, self._expires = d["access_token"], time.time() + int(d.get("expires_in", 3600))
        return {"Authorization": f"Bearer {self._token}"}

    def _thread(self, thread_id: str) -> dict:
        r = requests.get(f"{API}/threads/{thread_id}", headers=self._auth(), timeout=20,
                         params={"format": "metadata",
                                 "metadataHeaders": ["From", "Subject", "Date", "Message-ID"]})
        r.raise_for_status()
        return r.json()

    @staticmethod
    def _headers(m: dict) -> dict:
        return {h["name"].lower(): h["value"] for h in m.get("payload", {}).get("headers", [])}

    def send(self, to: str, subject: str, body: str, thread_id: str = "", in_reply_to: str = "") -> SentMessage:
        if thread_id and not in_reply_to:
            first = self._thread(thread_id).get("messages", [{}])[0]
            in_reply_to = self._headers(first).get("message-id", "")
        msg = self.build(to, subject, body, in_reply_to=in_reply_to)
        payload = {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()}
        if thread_id:
            payload["threadId"] = thread_id
        r = requests.post(f"{API}/messages/send", headers=self._auth(), json=payload, timeout=30)
        r.raise_for_status()
        return SentMessage(message_id=msg["Message-ID"], thread_id=r.json()["threadId"])

    @staticmethod
    def _plain(part: dict) -> str:
        """First text/plain body in a message payload, without the quoted earlier mail."""
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            text = base64.urlsafe_b64decode(part["body"]["data"] + "==").decode("utf-8", "replace")
            return re.split(r"\n\s*On .{0,200}wrote:\s*\n|\n>", text, maxsplit=1)[0].strip()
        for sub in part.get("parts", []) or []:
            got = GmailMailbox._plain(sub)
            if got:
                return got
        return ""

    def replies(self, thread_id: str, full: bool = False) -> list[Reply]:
        """Replies in a thread. full=True reads the whole plain-text body (not the ~200-char snippet)."""
        out = []
        if full:
            r = requests.get(f"{API}/threads/{thread_id}", headers=self._auth(), timeout=20,
                             params={"format": "full"})
            r.raise_for_status()
            messages = r.json().get("messages", [])
        else:
            messages = self._thread(thread_id).get("messages", [])
        for m in messages:
            h = self._headers(m)
            sender = h.get("from", "")
            if self.address.lower() in sender.lower() or "SENT" in m.get("labelIds", []):
                continue
            text = (self._plain(m.get("payload", {})) if full else "") or m.get("snippet", "")
            out.append(Reply(sender=sender, date=h.get("date", ""), text=text,
                             is_bounce=self.looks_like_bounce(sender, h.get("subject", ""))))
        return out


def authorize(client_secret_file: str) -> str:
    """Run the one-time browser consent flow and return a refresh token."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    return creds.refresh_token
