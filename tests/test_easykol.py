from outreach.models import Criteria
from outreach.search import run_search
from outreach.sources import easykol


class FakeResp:
    def __init__(self, body, status=200):
        self._body, self.status_code = body, status

    def json(self):
        return self._body


def test_easykol_search_polls_and_maps(monkeypatch):
    calls = []
    replies = [
        {"statusCode": 1000, "data": {"taskId": "t1", "status": "PROCESSING"}},
        {"statusCode": 1000, "data": {"taskId": "t1", "status": "PROCESSING"}},
        {"statusCode": 1000, "data": {"taskId": "t1", "status": "COMPLETED", "total": 1, "data": [
            {"nickname": "Fit", "username": "fitcreator", "profileUrl": "https://www.youtube.com/@fitcreator",
             "followerCount": 250000, "averagePlayCount": 52000, "averageLikeCount": None,
             "region": None, "language": "en", "email": "hello@example.com",
             "relevanceScore": 0.91, "reason": "Channel matches fitness"}]}},
    ]

    def fake_request(self, method, url, timeout=30, **kw):
        calls.append((method, url, kw.get("json")))
        return FakeResp(replies.pop(0))

    monkeypatch.setattr(easykol.requests.Session, "request", fake_request)
    monkeypatch.setattr(easykol.time, "sleep", lambda s: None)
    src = easykol.EasyKolSource("ek_x", "me@x.com", "youtube")
    src.min_followers, src.language, src.min_avg = 10000, "en", 50
    crit = Criteria(name="t", keywords="fitness", min_followers=10000, min_avg_likes=50, platforms=["youtube"])
    res = run_search(src, crit, ["US fitness YouTubers"], set(), pages_per_query=1, tweet_budget=100)

    method, url, body = calls[0]
    assert method == "POST" and url.endswith("/web-search")
    assert body["platform"] == "YOUTUBE" and body["searchType"] == "smart"
    assert body["minSubscribers"] == 10000 and body["languages"] == ["en"] and body["hasContactInfo"] is True
    assert calls[-1][1].endswith("/web-search/t1")
    (c,) = res.candidates  # kept even though avg likes is null: EasyKOL prefiltered
    assert c.email == "hello@example.com" and c.email_source == "easykol"
    assert c.followers == 250000 and c.key == "youtube:fitcreator" and c.relevance == 0.91


def test_easykol_error_envelope(monkeypatch):
    monkeypatch.setattr(easykol.requests.Session, "request",
                        lambda self, m, u, timeout=30, **kw: FakeResp(
                            {"statusCode": 1403, "error": "FORBIDDEN", "message": "quota exhausted"}, 403))
    src = easykol.EasyKolSource("ek_x", "me@x.com", "tiktok")
    try:
        list(src.search("x", 1))
    except easykol.EasyKolError as e:
        assert "1403" in str(e)
    else:
        raise AssertionError("expected EasyKolError")
