from types import SimpleNamespace

from outreach import slack_bot as sb


def rows():
    return [
        (2, {"platform": "x", "username": "alice", "status": "ready", "score": 9, "followers": 12000,
             "score_reason": "AI video reviews", "opener": "Loved your Veo test."}),
        (3, {"platform": "youtube", "username": "bob", "status": "ready", "score": 8}),
        (4, {"platform": "x", "username": "carol", "status": "followup_due", "score": 7}),
        (5, {"platform": "x", "username": "dan", "status": "replied", "reply_category": "interested",
             "reply_summary": "Wants rates"}),
    ]


def test_digest_lists_ready_and_hot_replies():
    t = sb.digest_text(rows())
    assert "x:alice" in t and "12k" in t and "youtube:bob" in t and "Wants rates" in t
    assert t.index("x:alice") < t.index("youtube:bob")


def test_execute_approve_with_skip_and_followups():
    plan = sb.Plan(summary="s", actions=[sb.Action(kind="approve", min_score=8, skip=["@bob"]),
                                         sb.Action(kind="approve_followups")])
    updates, note = sb.execute(plan, rows())
    assert updates == [(2, {"status": "approved"}), (4, {"status": "followup_approved"})]
    assert "alice" in note


def test_execute_never_approves_everything_without_selection():
    updates, _ = sb.execute(sb.Plan(summary="s", actions=[sb.Action(kind="approve")]), rows())
    assert updates == []


def test_skip_and_confirm_words():
    updates, _ = sb.execute(sb.Plan(summary="s", actions=[sb.Action(kind="skip", handles=["youtube:bob"])]), rows())
    assert updates == [(3, {"status": "skipped"})]
    assert sb.is_confirm("确认") and sb.is_confirm(" Yes! ") and not sb.is_confirm("yes but skip bob")


class FakeSlack:
    bot_user, token, channel = "UBOT", "t", "C"

    def __init__(self, thread):
        self._thread, self.posts = thread, []

    def latest_digest(self):
        return {"ts": "1", "text": "shortlist"}

    def thread(self, ts):
        return self._thread

    def post(self, text, thread_ts="", event="", payload=None):
        self.posts.append((text, event, payload))
        self._thread.append({"user": "UBOT", "text": text, "metadata": {"event_type": event, "event_payload": payload}})
        return "x"


class FakeSheet:
    def __init__(self):
        self.updates = []

    def read_candidates(self):
        return rows()

    def update_candidates(self, u):
        self.updates += u


def test_poll_asks_first_then_executes_on_confirm():
    plan = sb.Plan(summary="批准 alice", actions=[sb.Action(kind="approve", handles=["alice"])])
    client = SimpleNamespace(messages=SimpleNamespace(
        parse=lambda **kw: SimpleNamespace(stop_reason="end_turn", parsed_output=plan)))
    thread = [{"user": "UBOT", "text": "shortlist", "metadata": {"event_type": sb.DIGEST_EVENT}},
              {"user": "UME", "text": "发 alice"}]
    slack, sheet = FakeSlack(thread), FakeSheet()
    ctx = sb.Context(slack, sheet, client, "m")
    assert sb.poll(ctx) == 1
    assert sheet.updates == [] and slack.posts[-1][1] == sb.PLAN_EVENT  # asked, did nothing
    assert sb.poll(ctx) == 0  # nothing new
    thread.append({"user": "UME", "text": "确认"})
    assert sb.poll(ctx) == 1
    assert sheet.updates == [(2, {"status": "approved"})] and slack.posts[-1][0].startswith("✅")
