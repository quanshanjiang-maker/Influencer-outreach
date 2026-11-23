from outreach import prefilter
from outreach.models import Creator, Criteria, Tweet
from outreach.search import run_search
from outreach.sources.base import XSource
from outreach.sources.twitterapi_io import _creator, _tweet


def mk(user, followers, likes, lang="en", tid="1"):
    return Creator(username=user, followers=followers), Tweet(id=tid, text="x", url="", likes=likes, lang=lang)


class FakeSource(XSource):
    def __init__(self, hits):
        self.hits = hits

    def search(self, query, max_pages):
        yield from self.hits.get(query, [])

    def recent_tweets(self, username, limit=20):
        return []


def test_prefilter_rules():
    crit = Criteria(name="t", keywords="k", language="en", min_followers=1000,
                    max_followers=50000, min_avg_likes=10)
    ok, t = mk("good", 5000, 50)
    prefilter.merge({}, ok, t, "q")
    ok.tweets.append(t)
    assert prefilter.passes(ok, crit, known=set())
    assert not prefilter.passes(ok, crit, known={"good"})
    small, t2 = mk("small", 10, 50)
    small.tweets.append(t2)
    assert not prefilter.passes(small, crit, set())
    big, t3 = mk("big", 10**6, 50)
    big.tweets.append(t3)
    assert not prefilter.passes(big, crit, set())
    zh, t4 = mk("zh", 5000, 50, lang="zh")
    d = {}
    prefilter.merge(d, zh, t4, "q")
    assert not prefilter.passes(d["zh"], crit, set())


def test_run_search_groups_ranks_and_budgets():
    hits = {
        "q1": [mk("Alice", 5000, 40, tid="1"), mk("bob", 3000, 5, tid="2")],
        "q2": [mk("alice", 5000, 60, tid="3"), mk("carol", 8000, 30, tid="4")],
    }
    crit = Criteria(name="t", keywords="k", min_followers=1000, min_avg_likes=10)
    res = run_search(FakeSource(hits), crit, ["q1", "q2"], known={"carol"},
                     pages_per_query=1, tweet_budget=100)
    assert res.tweets_fetched == 4
    assert [c.username for c in res.candidates] == ["Alice"]  # bob too few likes, carol known
    assert res.candidates[0].avg_likes == 50
    assert len(res.candidates[0].matched_queries) == 2

    capped = run_search(FakeSource(hits), crit, ["q1", "q2"], set(), 1, tweet_budget=2)
    assert capped.tweets_fetched == 2


def test_twitterapi_io_parsing():
    author = {"userName": "dev", "name": "Dev", "followers": 1234, "description": "AI tools",
              "profile_bio": {"entities": {"url": {"urls": [{"expanded_url": "https://dev.io"}]}}}}
    c = _creator(author)
    assert c.username == "dev" and c.followers == 1234 and c.website == "https://dev.io"
    assert c.profile_url == "https://x.com/dev"
    t = _tweet({"id": 9, "text": "hi", "likeCount": 7, "lang": "en"})
    assert t.id == "9" and t.likes == 7
