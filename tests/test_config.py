from outreach.config import _resolve_mailboxes


def test_mailbox_address_from_env(monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", " me@example.com ")
    monkeypatch.setenv("SENDER_NAME", "Me")
    out = _resolve_mailboxes([{"type": "gmail", "address_env": "GMAIL_ADDRESS", "from_name_env": "SENDER_NAME"}])
    assert out[0]["address"] == "me@example.com" and out[0]["from_name"] == "Me"


def test_mailbox_literal_address_kept(monkeypatch):
    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    out = _resolve_mailboxes([{"address": "a@b.com", "address_env": "GMAIL_ADDRESS"}])
    assert out[0]["address"] == "a@b.com"
