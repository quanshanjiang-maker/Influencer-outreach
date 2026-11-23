from outreach import emails


def test_parsing_variants_and_junk():
    assert emails.emails_in_text("Biz: Jane.Doe [at] gmail [dot] com | hi@studio.io") == [
        "jane.doe@gmail.com", "hi@studio.io"]
    assert emails.emails_in_text("reach me: jane at gmail dot com") == ["jane@gmail.com"]
    assert emails.emails_in_text("Look at this.Then logo@2x.png a@example.com") == []


def test_find_email_order(monkeypatch):
    monkeypatch.setattr(emails, "emails_on_page", lambda url: ["site@creator.co"])
    monkeypatch.setattr(emails, "hunter_domain_search", lambda d, k: "hunter@creator.co")
    assert emails.find_email("EK@x.com", "easykol", "", "", None).source == "easykol"
    assert emails.find_email("", "", "mail: me@bio.io", "https://creator.co", None).email == "me@bio.io"
    assert emails.find_email("", "", "no mail", "https://creator.co", None).source == "website"
    assert emails.find_email("", "", "", "https://x.com/foo", "k").status == "not_found"

    monkeypatch.setattr(emails, "emails_on_page", lambda url: [])
    assert emails.find_email("", "", "", "https://creator.co", "k").source == "hunter"
    assert emails.find_email("", "", "", "https://linktr.ee/foo", "k").status == "not_found"


def test_verify(monkeypatch):
    monkeypatch.setattr(emails, "millionverifier", lambda e, k: "invalid")
    assert emails.verify(emails.EmailResult("a@b.co", "bio"), "key").status == "invalid"
    assert emails.verify(emails.EmailResult("a@b.co", "bio"), None).status == "unverified"
    assert "invalid" not in emails.SENDABLE
