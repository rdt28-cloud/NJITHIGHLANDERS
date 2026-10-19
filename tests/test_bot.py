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
            sent[f"{g['uid']}|{kind}"] = t.isoformat()
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
    assert len(fired) == 5  # nothing sent twice


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
        assert p["allowed_mentions"] == {"parse": []}
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


def test_every_template_renders_for_every_kind():
    for g in games():
        for kind in messages.TEMPLATES:
            ctx = messages._ctx(g, SPORTS["mens-soccer"], 15)
            for t in messages.TEMPLATES[kind](ctx):
                p = t()
                text = messages.plain_text(p)
                assert text and "{" not in text and len(text) < 1900
                for e in p.get("embeds", []):
                    assert len(e.get("title", "")) <= 256
