from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr, make_msgid


@dataclass
class SentMessage:
    message_id: str   # RFC 5322 Message-ID, e.g. <abc@host>
    thread_id: str    # provider thread id (Gmail) or the first Message-ID (SMTP/IMAP)


@dataclass
class Reply:
    sender: str
    date: str
    text: str
    is_bounce: bool = False


BOUNCE_SENDERS = ("mailer-daemon", "postmaster", "mail delivery subsystem")


class Mailbox(ABC):
    address: str
    from_name: str

    def build(self, to: str, subject: str, body: str, in_reply_to: str = "",
              unsubscribe_mailto: bool = True) -> EmailMessage:
        msg = EmailMessage()
        msg["From"] = formataddr((self.from_name, self.address)) if self.from_name else self.address
        msg["To"] = to
        msg["Subject"] = subject
        msg["Message-ID"] = make_msgid(domain=self.address.split("@")[-1])
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
            msg["References"] = in_reply_to
        if unsubscribe_mailto:
            msg["List-Unsubscribe"] = f"<mailto:{self.address}?subject=unsubscribe>"
        msg.set_content(body)
        return msg

    @abstractmethod
    def send(self, to: str, subject: str, body: str, thread_id: str = "", in_reply_to: str = "") -> SentMessage:
        """Send a message; pass thread_id/in_reply_to to reply in an existing thread."""

    @abstractmethod
    def replies(self, thread_id: str) -> list[Reply]:
        """Messages in the thread that were not sent by this mailbox, oldest first."""

    @staticmethod
    def looks_like_bounce(sender: str, subject: str = "") -> bool:
        s = f"{sender} {subject}".lower()
        return any(b in s for b in BOUNCE_SENDERS) or "undeliverable" in s or "delivery status notification" in s
