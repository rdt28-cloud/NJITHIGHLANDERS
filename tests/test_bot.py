import random
from datetime import date, datetime, timedelta
from pathlib import Path

from bot import alerts, messages
from bot.schedule import ET, extract_raw, normalize, parse_time
from bot.sports import SPORTS

HTML = (Path(__file__).parent / "fixture_soccer.html").read_text()
TODAY = date(2026, 10, 19)


def games():
    raw = extract_raw(HTML, "/sports/mens-soccer/schedule")
    return normalize(raw, "mens-soccer", TODAY)


def test_parse_real_page():
    g = {x["opponent"]: x for x in games()}
    bryant, umbc, qf = g["Bryant"], g["UMBC"], g["America East Quarterfinals"]
    assert bryant["where"] == "home" and bryant["start"] == "2026-10-30T18:00:00-04:00"
    assert bryant["venue"] == "Lubetkin Field at Mal Simon Stadium"
    assert bryant["promo"] == "Senior Night"
    assert bryant["stream"]["name"] == "ESPN+"          # from the coverage logo, not the intl link
    assert umbc["where"] == "away" and umbc["start"] == "2026-11-03T19:00:00-05:00"  # after DST ends
    assert qf["start"] is None and qf["tournament"]
    assert qf["stream"].get("unconfirmed")


def test_time_parsing():
    assert parse_time("7pm") == (19, 0, "ET")
    assert parse_time("7:30 p.m.") == (19, 30, "ET")
    assert parse_time("12 PM") == (12, 0, "ET")
    assert parse_time("Noon") == (12, 0, "ET")
    assert parse_time("10 a.m. PT") == (10, 0, "PT")
    assert parse_time("TBD") is None and parse_time("All Day") is None


def _fire_times(gs, start, end):
    sent, out = {}, []
    t = start
    while t < end:
        for kind, g, mins in list(alerts.due_alerts(gs, t, sent)):
            sent[alerts.sent_key(kind, g)] = t.isoformat()
            out.append((t, kind, g["opponent"], mins))
        t += timedelta(minutes=5)
    return out


def test_alert_schedule():
    gs = games()
    fired = _fire_times(gs, datetime(2026, 10, 30, 0, 0, tzinfo=ET), datetime(2026, 11, 8, 0, 0, tzinfo=ET))
    by = {(o, k): (t, m) for t, k, o, m in fired}
    # home: 9am "hosting" + 45 min "pull up"
    assert by[("Bryant", "home_morning")][0].hour == 9
    t, m = by[("Bryant", "home_pullup")]
    assert (t.hour, t.minute, m) == (17, 15, 45)
    # away: 9am "game day" + 15 min "live"
    assert by[("UMBC", "away_morning")][0].hour == 9
    t, m = by[("UMBC", "away_live")]
    assert (t.hour, t.minute, m) == (18, 45, 15)
    # TBD game: morning only
    assert ("America East Quarterfinals", "away_morning") in by
    assert ("America East Quarterfinals", "away_live") not in by
    # 2 days out: a fun poll at noon (UMBC Nov 3 → Nov 1; quarterfinal Nov 7 → Nov 5)
    t, _ = by[("UMBC", "preview_poll")]
    assert (t.month, t.day, t.hour) == (11, 1, 12)
    assert by[("America East Quarterfinals", "preview_poll")][0].day == 5
    assert len([f for f in fired if f[1] != "preview_poll"]) == 5  # nothing sent twice
    assert len([f for f in fired if f[1] == "preview_poll"]) == 2


def test_late_runner_still_sends_once():
    g = [x for x in games() if x["opponent"] == "UMBC"]
    sent = {}
    late = datetime(2026, 11, 3, 18, 53, tzinfo=ET)  # GitHub ran 8 min late
    due = list(alerts.due_alerts(g, late, sent))
    kinds = [k for k, *_ in due]
    assert "away_live" in kinds
    mins = [m for k, _, m in due if k == "away_live"][0]
    assert mins == 7  # message says "in 7 minutes", not a wrong "15"


def test_messages_rotate_and_never_repeat_back_to_back():
    g = [x for x in games() if x["opponent"] == "Bryant"][0]
    state, rng = {}, random.Random(1)
    seen = []
    for _ in range(40):
        p = messages.build("home_pullup", g, SPORTS["mens-soccer"], state, minutes_to_start=45, rng=rng)
        seen.append(messages.plain_text(p))
        assert p["allowed_mentions"]["parse"] == []  # never @everyone/@here
        assert "Senior Night" in seen[-1]
    assert all(a != b for a, b in zip(seen, seen[1:]))
    assert len(set(seen)) >= 6  # many different formats in play


def test_unlisted_stream_never_claims_live_platform():
    g = dict([x for x in games() if x["opponent"] == "UMBC"][0])
    g["stream"] = {"name": "the live stream", "url": g["schedule_url"], "unconfirmed": True}
    for i in range(10):
        text = messages.plain_text(messages.build("away_live", g, SPORTS["mens-soccer"], {}, 15, rng=random.Random(i)))
        assert "LIVE on" not in text and "live on" not in text.lower().replace("live updates", "")


def test_stale_old_season_is_skipped():
    from bot.schedule import normalize
    raw = {"path": "/x", "ld": [], "games": [
        {"id": "9834", "cls": "sidearm-schedule-away-game", "dateSpans": ["Oct 26 (Sat)", "All Day"],
         "opp": "EIBT # 2", "loc": "Strathmore, NJ", "links": [], "imgs": []},  # Oct 26 is a Saturday in 2024, not 2026
        {"id": "1", "cls": "sidearm-schedule-away-game", "dateSpans": ["Oct 24 (Sat)", "- Oct 25 (Sun)", "Oct 24 (Sat)", "- Oct 25 (Sun)"],
         "opp": "Nikki Franke Open", "loc": "Philadelphia, PA", "links": [], "imgs": []}]}
    out = normalize(raw, "fencing", TODAY)
    assert [g["opponent"] for g in out] == ["Nikki Franke Open"]
    assert out[0]["date"] == "2026-10-24" and out[0]["start"] is None


def test_alerts_ping_only_that_sports_fans():
    g = [x for x in games() if x["opponent"] == "UMBC"][0]
    sport = SPORTS["mens-soccer"]
    for i in range(12):
        p = messages.build("away_morning", g, sport, {}, rng=random.Random(i))
        assert p["content"].startswith(f"<@&{sport['role_id']}>")
        assert p["allowed_mentions"] == {"parse": [], "roles": [sport["role_id"]]}  # no @everyone, ever


def test_home_poll_is_valid_discord_poll():
    from datetime import datetime
    for g in games():
        state = {}
        for i in range(8):
            p = messages.build_poll(g, SPORTS["mens-soccer"], state,
                                    now=datetime(2026, 10, 30, 9, 0, tzinfo=ET), rng=random.Random(i))["poll"]
            assert 0 < len(p["question"]["text"]) <= 300
            assert 2 <= len(p["answers"]) <= 10
            assert all(0 < len(a["poll_media"]["text"]) <= 55 for a in p["answers"])
            assert 1 <= p["duration"] <= 24
    bryant = [x for x in games() if x["opponent"] == "Bryant"][0]
    p = messages.build_poll(bryant, SPORTS["mens-soccer"], {}, now=datetime(2026, 10, 30, 9, 0, tzinfo=ET))
    assert p["poll"]["duration"] == 12  # 6 PM start + 3h → open until ~9 PM


def test_zz_home_morning_posts_alert_then_poll():
    from datetime import datetime
    bryant = [x for x in games() if x["opponent"] == "Bryant"]
    sent_payloads = []
    alerts.post = lambda url, payload: sent_payloads.append(payload)
    alerts.time.sleep = lambda s: None
    alerts.run(bryant, {}, now=datetime(2026, 10, 30, 9, 0, tzinfo=ET), webhooks={"mens-soccer": "https://x"}, log=lambda *a: None)
    assert len(sent_payloads) == 2 and "poll" not in sent_payloads[0] and "poll" in sent_payloads[1]


def test_every_template_renders_for_every_kind():
    for g in games():
        for kind in messages.TEMPLATES:
            ctx = messages._ctx(g, SPORTS["mens-soccer"], 15)
            for t in messages.TEMPLATES[kind](ctx):
                text = t()
                assert text and "{" not in text and "None" not in text and len(text) < 1900
                assert "bot" not in text.lower()  # reads like a person wrote it


def test_posts_come_from_you_not_a_bot():
    from bot.sports import AVATAR_URL, DISPLAY_NAME
    g = [x for x in games() if x["opponent"] == "Bryant"][0]
    for p in (messages.build("home_morning", g, SPORTS["mens-soccer"], {}),
              messages.build_poll(g, SPORTS["mens-soccer"], {}),
              messages.build_preview_poll(g, SPORTS["mens-soccer"], {})):
        assert p["username"] == DISPLAY_NAME and p.get("avatar_url") == AVATAR_URL
        assert "embeds" not in p  # plain messages, no bot-style cards


def test_roster_page_parsing():
    from bot.schedule import extract_roster
    r = extract_roster((Path(__file__).parent / "fixture_roster.html").read_text())
    assert r[0] == {"name": "Samori McKell-Jeffers", "num": "1", "pos": "GK"}
    assert [p["name"] for p in r] == ["Samori McKell-Jeffers", "Luan Lazoja", "Rodrigo Grenha", "Test Striker"]


def test_preview_polls_rotate_and_are_valid():
    from bot.schedule import extract_roster
    roster = extract_roster((Path(__file__).parent / "fixture_roster.html").read_text())
    state = {}
    kinds = []
    for g in games() * 3:
        p = messages.build_preview_poll(g, SPORTS["mens-soccer"], state, roster=roster,
                                        now=datetime(2026, 10, 28, 12, tzinfo=ET), rng=random.Random(len(kinds)))
        kinds.append(p["_kind"])
        poll = p["poll"]
        assert p["content"] and "{" not in p["content"]
        assert 0 < len(poll["question"]["text"]) <= 300 and "{" not in poll["question"]["text"]
        assert 2 <= len(poll["answers"]) <= 10
        assert all(0 < len(a["poll_media"]["text"]) <= 55 for a in poll["answers"])
        assert 1 <= poll["duration"] <= 168
        if p["_kind"] == "players":
            names = " ".join(a["poll_media"]["text"] for a in poll["answers"])
            assert "McKell-Jeffers" not in names or "standout" in poll["question"]["text"]  # keeper never a "scorer"
    order = ["result", "food", "players", "fun"]
    first = order.index(kinds[0])
    assert kinds[:4] == [order[(first + i) % 4] for i in range(4)]  # changes every time, full rotation
    # Bryant (Fri 6 PM) poll posted Wed noon stays open until kickoff
    bryant = [x for x in games() if x["opponent"] == "Bryant"][0]
    p = messages.build_preview_poll(bryant, SPORTS["mens-soccer"], {}, now=datetime(2026, 10, 28, 12, tzinfo=ET))
    assert p["poll"]["duration"] == 54


def test_no_roster_skips_player_polls():
    g = [x for x in games() if x["opponent"] == "Bryant"][0]
    state = {"preview_kind": {"mens-soccer": 1}}  # next up would be "players"
    p = messages.build_preview_poll(g, SPORTS["mens-soccer"], state, roster=[])
    assert p["_kind"] == "fun"


def test_one_preview_poll_per_sport_per_day():
    g1 = [x for x in games() if x["opponent"] == "UMBC"][0]
    g2 = dict(g1, uid="mens-soccer:dh2", opponent="UMBC (DH)")
    due = [k for k, *_ in alerts.due_alerts([g1, g2], datetime(2026, 11, 1, 12, tzinfo=ET), {})]
    assert due.count("preview_poll") == 1
