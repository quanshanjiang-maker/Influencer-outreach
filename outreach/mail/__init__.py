"""Mailbox adapters: Gmail API and generic SMTP+IMAP. Add more by implementing Mailbox."""
from __future__ import annotations

import os

from .base import Mailbox, Reply, SentMessage


def get_mailbox(conf: dict) -> Mailbox:
    """conf is one entry of `mailboxes:` in config.yaml. Secrets are read from env vars
    named in the entry (e.g. refresh_token_env: GOOGLE_REFRESH_TOKEN)."""
    kind = conf.get("type", "gmail")
    if not conf.get("address"):
        env_name = conf.get("address_env")
        raise ValueError(f"mailbox {conf.get('name', '')}: no address; "
                         + (f"set the {env_name} secret" if env_name else "set address or address_env"))

    def env(key: str, required: bool = True) -> str:
        name = conf.get(f"{key}_env")
        value = os.getenv(name, "") if name else ""
        if required and not value:
            raise ValueError(f"mailbox {conf.get('address')}: set {key}_env and that environment variable")
        return value

    if kind == "gmail":
        from .gmail import GmailMailbox
        return GmailMailbox(conf["address"], conf.get("from_name", ""),
                            client_id=env("client_id"), client_secret=env("client_secret"),
                            refresh_token=env("refresh_token"))
    if kind == "smtp":
        from .smtp_imap import SmtpImapMailbox
        return SmtpImapMailbox(conf["address"], conf.get("from_name", ""),
                               smtp_host=conf["smtp_host"], smtp_port=int(conf.get("smtp_port", 465)),
                               imap_host=conf["imap_host"], imap_port=int(conf.get("imap_port", 993)),
                               username=conf.get("username") or conf["address"], password=env("password"))
    raise ValueError(f"Unknown mailbox type: {kind}")


__all__ = ["Mailbox", "Reply", "SentMessage", "get_mailbox"]
