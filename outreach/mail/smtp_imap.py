"""Generic SMTP (send) + IMAP (replies) mailbox for any provider:
Microsoft 365, Tencent Exmail, Zoho, Fastmail, etc. Use an app password where required."""
from __future__ import annotations

import email
import imaplib
import smtplib
import ssl
from email.header import decode_header, make_header

from .base import Mailbox, Reply, SentMessage


class SmtpImapMailbox(Mailbox):
    def __init__(self, address: str, from_name: str, smtp_host: str, smtp_port: int,
                 imap_host: str, imap_port: int, username: str, password: str):
        self.address, self.from_name = address, from_name
        self.smtp_host, self.smtp_port = smtp_host, smtp_port
        self.imap_host, self.imap_port = imap_host, imap_port
        self.username, self.password = username, password

    def send(self, to: str, subject: str, body: str, thread_id: str = "", in_reply_to: str = "") -> SentMessage:
        msg = self.build(to, subject, body, in_reply_to=in_reply_to or thread_id)
        ctx = ssl.create_default_context()
        if self.smtp_port == 465:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=ctx, timeout=30) as s:
                s.login(self.username, self.password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as s:
                s.starttls(context=ctx)
                s.login(self.username, self.password)
                s.send_message(msg)
        # Without a provider thread id, the first Message-ID identifies the conversation.
        return SentMessage(message_id=msg["Message-ID"], thread_id=thread_id or msg["Message-ID"])

    def replies(self, thread_id: str) -> list[Reply]:
        out = []
        with imaplib.IMAP4_SSL(self.imap_host, self.imap_port) as im:
            im.login(self.username, self.password)
            im.select("INBOX", readonly=True)
            ids: set[bytes] = set()
            for header in ("In-Reply-To", "References"):
                typ, data = im.search(None, "HEADER", header, f'"{thread_id}"')
                if typ == "OK" and data and data[0]:
                    ids.update(data[0].split())
            for num in sorted(ids, key=int):
                typ, data = im.fetch(num, "(BODY.PEEK[])")
                if typ != "OK" or not data or not isinstance(data[0], tuple):
                    continue
                m = email.message_from_bytes(data[0][1])
                sender = str(make_header(decode_header(m.get("From", ""))))
                subject = str(make_header(decode_header(m.get("Subject", ""))))
                if self.address.lower() in sender.lower():
                    continue
                out.append(Reply(sender=sender, date=m.get("Date", ""), text=_text(m)[:2000],
                                 is_bounce=self.looks_like_bounce(sender, subject)))
        return out


def _text(m: email.message.Message) -> str:
    if m.is_multipart():
        for part in m.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
        return ""
    return (m.get_payload(decode=True) or b"").decode(m.get_content_charset() or "utf-8", "replace")
