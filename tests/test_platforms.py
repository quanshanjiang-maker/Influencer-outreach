from outreach import expand
from outreach.models import Creator, Criteria, Post
from outreach.search import run_search
from outreach.sources import apify_instagram, apify_tiktok, youtube
from outreach.sources.base import Source


def test_tiktok_parsing_and_hashtag_input(monkeypatch):
    seen = {}

    def fake_run(token, actor, run_input, timeout=300):
        seen.update(run_input)
        return [{"id": "1", "text": "cool", "webVideoUrl": "u", "diggCount": 50, "playCount": 900,
                 "authorMeta": {"name": "tt", "fans": 12000, "signature": "biz: a@b.co"}}]

    monkeypatch.setattr(apify_tiktok, "run_actor", fake_run)
    src = apify_tiktok.ApifyTikTokSource("tok")
    (c, p), = list(src.search("#aivideo", 1))
    assert seen["hashtags"] == ["aivideo"] and "searchQueries" not in seen
    assert c.platform == "tiktok" and c.followers == 12000 and c.key == "tiktok:tt"
    assert p.likes == 50 and p.views == 900
    list(src.search("ai video review", 1))
    assert seen["searchQueries"] == ["ai video review"]


def test_instagram_enrich_fills_followers(monkeypatch):
    calls = []

    def fake_run(token, actor, run_input, timeout=300):
        calls.append(run_input)
        if run_input.get("resultsType") == "posts":
            return [{"ownerUsername": "ig1", "likesCount": 30, "url": "p", "id": "9"}]
        return [{"username": "ig1", "followersCount": 7000, "biography": "hi", "externalUrl": "https://ig1.com"}]

    monkeypatch.setattr(apify_instagram, "run_actor", fake_run)
    src = apify_instagram.ApifyInstagramSource("tok")
    crit = Criteria(name="t", keywords="k", min_followers=5000, platforms=["instagram"])
    res = run_search(src, crit, ["#aivideo"], set(), pages_per_query=1, tweet_budget=100)
    assert [c.username for c in res.candidates] == ["ig1"]
    assert res.candidates[0].followers == 7000 and res.candidates[0].website == "https://ig1.com"
    assert calls[1]["resultsType"] == "details"


def test_youtube_parsing(monkeypatch):
    def fake_get(self, endpoint, params):
        if endpoint == "search":
            return {"items": [{"id": {"videoId": "v1"}, "snippet": {"channelId": "c1", "title": "Review",
                                                                     "publishedAt": "2026-01-01"}}]}
        if endpoint == "videos":
            return {"items": [{"id": "v1", "statistics": {"likeCount": "40", "viewCount": "1000"},
                               "snippet": {"description": "desc"}}]}
        return {"items": [{"id": "c1", "snippet": {"customUrl": "@chan", "title": "Chan",
                                                     "description": "email me"},
                           "statistics": {"subscriberCount": "25000"}}]}

    monkeypatch.setattr(youtube.YouTubeSource, "_get", fake_get)
    (c, p), = list(youtube.YouTubeSource("k").search("ai video", 1))
    assert c.username == "chan" and c.followers == 25000 and c.platform == "youtube"
    assert p.likes == 40 and p.url.endswith("v1")


def test_fallback_queries_per_platform():
    crit = Criteria(name="t", keywords="AI video", language="en")
    assert expand._fallback_query(crit, "instagram") == "#aivideo"
    assert expand._fallback_query(crit, "youtube") == "AI video"
    assert "lang:en" in expand._fallback_query(crit, "x")
