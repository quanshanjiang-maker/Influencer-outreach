from outreach.models import Creator, Criteria
from outreach.prefilter import hire_bio, passes


def test_hire_bio():
    for bio in ["AI Creator | DM for collab", "📩 DM for collaborations", "Open for Paid Collaborations 📩",
                "DM For Paid Collaborations", "dm 4 promo", "Paid collabs DM", "Promos & Collabs 📧", "For Collab Query : x", "CPP: @a | sponsorships", "ᴅᴍ ꜰᴏʀ ᴄᴏʟʟᴀʙ"]:
        assert hire_bio(bio), bio
    for bio in ["AI filmmaker in LA", "Building in public with AI", "DM me your questions"]:
        assert not hire_bio(bio), bio


def test_passes_drops_hire_bio_and_follow_for_follow():
    crit = Criteria(name="t", keywords="ai", min_followers=1000)
    ok = Creator(username="a", followers=10000, following=500, bio="AI filmmaker")
    assert passes(ok, crit, set())
    assert not passes(Creator(username="b", followers=10000, following=500, bio="DM for collab"), crit, set())
    assert not passes(Creator(username="c", followers=10000, following=9000, bio="AI filmmaker"), crit, set())
    assert passes(Creator(username="d", followers=10000, following=0, bio="AI filmmaker"), crit, set())
    assert not passes(Creator(username="e", followers=10000, bio="AI filmmaker", location="DM for collab"), crit, set())


def test_generic_ai_curator():
    from outreach.prefilter import generic_ai
    from outreach.models import Creator
    mk = lambda b: Creator(platform="x", username="u", bio=b)
    assert generic_ai(mk("Future With Al | Sharing latest AI tools"))
    assert generic_ai(mk("Helping you to make money with AI"))
    assert not generic_ai(mk("Scaling fashion stores behind the scenes"))
    assert not generic_ai(mk("Writer Director Showrunner | ElevenLabs Ambassador"))
