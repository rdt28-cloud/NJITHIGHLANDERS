"""Game-day posts and fan polls, written to sound like a person, not a bot.

Every post type has several templates in different shapes (one-liners,
short lists, headlines, questions). One is picked at random, but never one
used recently for that sport + post type, so the channel never feels
copy-pasted. Posts are plain text (no bot-style cards or footers) and go out
under DISPLAY_NAME / AVATAR_URL from bot/sports.py.
"""
from __future__ import annotations

import random
import re
from datetime import datetime

EVENT_WORDS = ("invitational", "championship", "classic", "tournament", "open",
               "quarterfinal", "semifinal", "final", "relays", "meet", "cup",
               "showcase", "challenge", "games", "regional", "conference",
               "carnival", "opener", "invite", "festival", "collegiate", "individual",
               "regionals", "sectional", "masters", "eibt")
MEET_SPORTS = ("cross-country", "track-field", "swimming-diving", "fencing", "bowling")


# ------------------------------------------------------------------- helpers

def _time(g) -> str:
    if not g["start"]:
        return "time TBA"
    t = datetime.fromisoformat(g["start"])
    s = t.strftime("%I:%M %p").lstrip("0")
    return s.replace(":00 ", " ")


def _day(g) -> str:
    return datetime.fromisoformat(g["date"]).strftime("%A")


def _is_event(g) -> bool:
    opp = g["opponent"].lower()
    if any(w in opp for w in EVENT_WORDS):
        return True
    if any(s in g["sport"] for s in MEET_SPORTS) and (" vs" not in opp):
        # a meet name like "Lafayette XC Invitational" vs a dual meet like "Iona"
        return len(opp.split()) > 2
    # tournament games against a named team ("Merrimack") still read as "NJIT vs Merrimack"
    return g["tournament"] and len(opp.split()) > 2


def matchup(g) -> str:
    """'NJIT vs Bryant' / 'NJIT at UMBC' / 'the Princeton Invitational'."""
    opp = g["opponent"]
    if _is_event(g):
        return opp if opp.lower().startswith("the ") else f"the {opp}"
    if g["where"] == "home":
        return f"NJIT vs {opp}"
    if g["where"] == "neutral":
        return f"NJIT vs {opp} (neutral site)"
    return f"NJIT at {opp}"


def _where_line(g) -> str:
    if g["where"] == "home":
        return g["venue"] if g["venue"] not in ("", "TBA") else "Newark"
    return g["location"]


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def _ctx(g, sport, minutes_to_start=None):
    m = minutes_to_start
    countdown = "any minute now" if (m is None or m <= 0) else f"in {m} min"
    unconfirmed = bool(g["stream"].get("unconfirmed"))
    name, url = g["stream"]["name"], g["stream"]["url"]
    return {
        # watch lines that read right whether or not NJIT has listed a stream
        "watch": (f"Updates here: {url}" if unconfirmed else f"It's on {name}: {url}"),
        "watch_short": ("updates on the NJIT site" if unconfirmed else f"on {name}"),
        "stream": "the stream" if unconfirmed else name, "stream_url": url,
        "e": sport["emoji"], "sport": sport["name"], "noun": sport["noun"],
        "start_word": sport["start_word"], "opp": g["opponent"],
        "matchup": matchup(g), "Matchup": _cap(matchup(g)), "time": _time(g), "day": _day(g),
        "where": _where_line(g), "schedule": g["schedule_url"], "countdown": countdown,
        "is_event": _is_event(g),
    }


SIGNOFF = ["Go Highlanders 🔴⚪", "Let's go NJIT 🗡️", "LET'S GOOO 🔴", "Highlander pride 🔴⚪",
           "Let's get this W 💪", "Red and white all day 🔴⚪", "Bring it home 🗡️", ""]


def _so():
    s = random.choice(SIGNOFF)
    return ("\n" + s) if s else ""


# ------------------------------------------------------- AWAY: morning post

def _away_morning(c):
    return [
        lambda: f"GAME DAY {c['e']}\n{c['Matchup']}, {c['time']} in {c['where']}.\n{c['watch']}{_so()}",
        lambda: f"Morning Highlanders ☀️ {c['sport']} is on the road today: **{c['matchup']}**, {c['time']}.\n"
                f"Can't make the trip? {c['watch']}",
        lambda: f"{c['e']} {c['sport']} today\n• {c['Matchup']}\n• {c['time']}\n• {c['where']}\n• {c['watch_short']}{_so()}",
        lambda: f"Road game today {c['e']} Our {c['sport'].lower()} squad takes on {c['opp']} in {c['where']} at {c['time']}. "
                f"I'll post again right before it starts.{_so()}",
        lambda: f"# {c['e']} Game day\n{c['Matchup']} · {c['time']} · {c['where']}\n-# {c['watch_short']}",
        lambda: f"Who's watching {c['sport'].lower()} tonight? {c['e']} {c['Matchup']} at {c['time']}.\n{c['watch']}",
        lambda: f"Don't forget, {c['sport']} plays today! {c['e']}\n{c['Matchup']} ({c['where']}), {c['start_word']} at {c['time']}.{_so()}",
        lambda: f"{c['e']}{c['e']} {c['Matchup'].upper()} {c['e']}{c['e']}\nToday, {c['time']}. Send the team some love 🙌\n{c['watch']}",
    ]


# ---------------------------------------- AWAY: 15 minutes before (stream)

def _away_live(c):
    return [
        lambda: f"We're live {c['countdown']}! {c['e']} {c['Matchup']} on {c['stream']}\n{c['stream_url']}",
        lambda: f"🔴 {c['Matchup']} starts {c['countdown']}, tune in on {c['stream']}: {c['stream_url']}{_so()}",
        lambda: f"{c['start_word'].capitalize()} {c['countdown']} {c['e']} Pull up the stream: {c['stream_url']}\nDrop your predictions below 👇",
        lambda: f"Almost time! {c['e']} {c['sport']} on {c['stream']} {c['countdown']}.\n<{c['stream_url']}>",
        lambda: f"# 🔴 Live {c['countdown']}\n{c['Matchup']}\n-# watch on {c['stream']}: {c['stream_url']}",
        lambda: f"3… 2… 1… {c['e']} {c['Matchup']} goes live {c['countdown']}. Link: {c['stream_url']}{_so()}",
        lambda: f"Grab a snack and get on {c['stream']} 🍿 {c['Matchup']}, {c['start_word']} {c['countdown']}.\n{c['stream_url']}",
    ]


# --------------------------- AWAY: 15 minutes before (no stream listed yet)

def _away_soon(c):
    return [
        lambda: f"Almost go time {c['e']} {c['Matchup']} starts {c['countdown']}.\nLive updates: {c['schedule']}{_so()}",
        lambda: f"{c['start_word'].capitalize()} {c['countdown']}! {c['e']} Send the team some good vibes 🙌\n<{c['schedule']}>",
        lambda: f"Heads up, {c['sport']} gets going {c['countdown']} in {c['where']} {c['e']}\nI'll keep an eye on results: {c['schedule']}",
        lambda: f"# {c['e']} Starting {c['countdown']}\n{c['Matchup']} · {c['where']}\n-# updates: {c['schedule']}",
        lambda: f"Here we go {c['e']} {c['Matchup']}, {c['countdown']}. Drop your predictions 👇{_so()}",
        lambda: f"3… 2… 1… {c['e']} {c['sport']} is about to start ({c['countdown']}). Follow along: {c['schedule']}",
    ]


# --------------------------------------------------------- HOME: morning post

def _home_morning(c):
    return [
        lambda: f"WE'RE HOME TODAY 🏟️ {c['e']}\n{c['Matchup']}, {c['time']} at {c['where']}. Come out and make some noise!",
        lambda: f"Morning Highlanders ☀️ {c['sport']} hosts {c['opp']} today at {c['time']} ({c['where']}). "
                f"Bring a friend, wear red 🔴",
        lambda: f"{c['e']} Home {c['noun']} today\n• {c['Matchup']}\n• {c['time']}\n• {c['where']}\n• dress code: red 🔴{_so()}",
        lambda: f"Who's coming out today? 🙋 {c['Matchup']} at {c['where']}, {c['start_word']} at {c['time']}. Let's pack it {c['e']}",
        lambda: f"# {c['e']} Home game day\n{c['Matchup']} · {c['time']}\n-# {c['where']} · see you there",
        lambda: f"Today's plans: sorted ✅ {c['sport']} is home vs {c['opp']}, {c['time']} at {c['where']}.{_so()}",
        lambda: f"Newark, we play today {c['e']} {c['Matchup']} at {c['time']}. Every seat filled = more noise = more wins 📈",
        lambda: f"{c['e']}{c['e']} HOME {c['noun'].upper()} {c['e']}{c['e']}\n{c['Matchup']}, {c['time']}, {c['where']}. Don't miss it!",
    ]


# ------------------------------------------- HOME: 45 minutes before, pull up

def _home_pullup(c):
    return [
        lambda: f"PULL UP 📣 {c['e']} {c['Matchup']}, {c['start_word']} {c['countdown']} at {c['where']}. Let's fill those stands!",
        lambda: f"{c['countdown'].capitalize()} until {c['start_word']} 🏟️ Get to {c['where']} and bring the noise {c['e']}",
        lambda: f"Still on the fence? Here's your sign 👀 {c['sport']} is home {c['countdown']} at {c['where']}.{_so()}",
        lambda: f"Stands check 🚨 {c['Matchup']} starts {c['countdown']}. Who's already there? Tag a friend who's coming 👇",
        lambda: f"# 🏟️ Doors are open\n{c['Matchup']} · {c['start_word']} {c['countdown']}\n-# {c['where']} · be loud",
        lambda: f"It's almost time, Newark {c['e']} {c['start_word'].capitalize()} {c['countdown']} at {c['where']}. Red out the stands 🔴",
        lambda: f"On my way to {c['where']} 🏃 {c['Matchup']} {c['countdown']}. See you there {c['e']}",
        lambda: f"The team needs us 🗣️ {c['sport']} {c['start_word']} {c['countdown']} at {c['where']}. Show up, show out {c['e']}",
    ]


TEMPLATES = {
    "away_morning": _away_morning,
    "away_live": _away_live,
    "away_soon": _away_soon,
    "home_morning": _home_morning,
    "home_pullup": _home_pullup,
}


def _pick(key: str, n: int, state: dict, rng) -> int:
    """Random index in range(n), avoiding the last few used for `key`."""
    recent = state.setdefault("recent", {}).setdefault(key, [])
    avoid = recent[-min(n - 1, 4):] if recent else []
    idx = rng.choice([i for i in range(n) if i not in avoid] or list(range(n)))
    recent.append(idx)
    del recent[:-6]
    return idx


def _author(payload: dict) -> dict:
    from .sports import AVATAR_URL, DISPLAY_NAME
    payload["username"] = DISPLAY_NAME
    if AVATAR_URL:
        payload["avatar_url"] = AVATAR_URL
    return payload


def build(kind: str, game: dict, sport: dict, state: dict, minutes_to_start=None, rng=random, ping=True):
    """Return a Discord webhook payload for a game-day post, rotating formats."""
    ctx = _ctx(game, sport, minutes_to_start)
    if kind == "away_live" and game["stream"].get("unconfirmed"):
        kind = "away_soon"  # don't claim "we're live on X" when NJIT hasn't listed a stream
    options = TEMPLATES[kind](ctx)
    text = options[_pick(f"{game['sport']}:{kind}", len(options), state, rng)]()
    promo = game.get("promo")
    if promo and kind.startswith("home"):
        text += f"\nAlso it's **{promo}** 🎉 don't miss it!"
    payload = {"content": text, "allowed_mentions": {"parse": []}}  # never @everyone
    role = sport.get("role_id")
    if role and ping:
        payload["content"] = f"<@&{role}> " + payload["content"]
        payload["allowed_mentions"] = {"parse": [], "roles": [role]}
    return _author(payload)


def _poll(question: str, answers: list[str], hours: int, intro: str | None = None) -> dict:
    payload = {
        "allowed_mentions": {"parse": []},
        "poll": {
            "question": {"text": question[:300]},
            "answers": [{"poll_media": {"text": a[:55]}} for a in answers[:10]],
            "duration": max(1, min(168, int(hours))),
            "allow_multiselect": False,
        },
    }
    if intro:
        payload["content"] = intro
    return _author(payload)


def _hours_until(game, now, after=3, default=12):
    if game.get("start") and now is not None:
        left = (datetime.fromisoformat(game["start"]) - now).total_seconds() / 3600 + after
        return max(1, int(left + 0.999))
    return default


# ------------------------------------------- HOME: game-morning poll

def _poll_options(c, opp):
    """Each entry: (question, [answers]). Answers ≤ 55 chars (Discord limit)."""
    if c["is_event"]:
        return [
            (f"{c['e']} How does NJIT do at {c['matchup']} today?",
             ["🥇 Podium finishes!", "📈 Big personal bests", "💪 Solid team showing", "🔥 Best result of the season"]),
            (f"{c['e']} Coming out to support NJIT {c['sport']} today?",
             ["🙋 I'll be there!", "📲 Following along online", "🔜 Next time!"]),
        ]
    o = opp[:28]
    return [
        (f"{c['e']} {c['Matchup']}: how does NJIT win today?",
         ["🔥 NJIT in a blowout", "🔴 NJIT in a close one", "😤 NJIT comeback win"]),
        (f"{c['e']} Are you pulling up to {c['matchup']} today?",
         ["🙋 I'll be in the stands!", "👯 Bringing friends", "📺 Watching from home", "🔜 Next time!"]),
        (f"{c['e']} Hype meter for {c['matchup']}?",
         ["🔥🔥🔥 Max hype", "🔥🔥 Feeling good", "🔥 Nervous but believing"]),
        (f"{c['e']} Who's the X-factor for NJIT today?",
         ["🌟 Our stars", "🪑 The bench", "📣 The home crowd", "🧑‍🏫 The coaching staff"]),
    ]


def build_poll(game: dict, sport: dict, state: dict, now=None, rng=random):
    """A quick poll posted right after the home-game morning post."""
    ctx = _ctx(game, sport)
    options = _poll_options(ctx, game["opponent"])
    question, answers = options[_pick(f"{game['sport']}:home_poll", len(options), state, rng)]
    return _poll(question, answers, min(24, _hours_until(game, now)))


# ------------------------------------- 2 DAYS OUT: rotating fan polls

FOOD = ["🍕 Pizza", "🍗 Wings", "🌭 Hot dogs", "🌯 Halal cart", "🥨 Soft pretzels", "🍔 Burgers",
        "🌮 Tacos", "🍿 Popcorn", "🍖 Ironbound Portuguese BBQ", "🥯 Bagel run", "🍩 Donuts",
        "🧋 Bubble tea", "🍜 Ramen", "🥤 Just an energy drink", "🍪 Cookies", "🥟 Dumplings"]

SCORE_WORDS = {  # what NJIT "scores" in each sport, for player questions
    "basketball": "leads NJIT in scoring", "soccer": "scores first for NJIT",
    "lacrosse": "scores first for NJIT", "hockey": "scores first for NJIT",
    "volleyball": "leads NJIT in kills", "baseball": "gets NJIT's first hit",
    "tennis": "picks up the first W for NJIT",
}
NON_SCORERS = {  # positions left out of "who scores" questions, per sport
    "soccer": {"GK"}, "hockey": {"G"}, "lacrosse": {"GOALKEEPER", "G"},
    "volleyball": {"L", "LIB", "DS", "S"}, "baseball": {"RHP", "LHP", "P"},
}


def _family(sport_key: str) -> str:
    for f in ("basketball", "soccer", "lacrosse", "hockey", "volleyball", "baseball", "tennis"):
        if f in sport_key:
            return f
    return "meet"


def _result_poll(c, g, rng):
    fam = _family(g["sport"])
    if c["is_event"] or fam == "meet":
        qs = [f"{c['e']} Bold prediction time: how does NJIT do at {c['matchup']} on {c['day']}?",
              f"{c['e']} {c['day']}'s {c['noun']}: what's the headline going to be?"]
        ans = ["🥇 Someone wins an event", "🏆 Top-3 team finish", "📈 Personal bests everywhere",
               "🔥 Best result of the season", "💪 Solid day, building momentum"]
        return rng.choice(qs), rng.sample(ans, 4)
    # every answer is an NJIT win: fans just pick HOW we win
    options = {
        "basketball": ["🔴 NJIT by 20+, total blowout", "🔴 NJIT by 10–19", "🔴 NJIT by 1–9", "🚨 NJIT on a buzzer-beater"],
        "soccer": ["🔴 NJIT 1–0, a grind", "🔴 NJIT 2–1", "🧤 NJIT 3–0, clean sheet", "🔥 NJIT 4+ goals"],
        "lacrosse": ["🔥 NJIT by 10+", "🔴 NJIT by 5–9", "🔴 NJIT in a close one", "🚨 NJIT in overtime"],
        "hockey": ["🔥 NJIT by 3+", "🔴 NJIT by 1–2", "🧤 NJIT shutout", "🚨 NJIT in overtime"],
        "baseball": ["🔥 NJIT slugfest (8+ runs)", "🔴 NJIT in a pitchers' duel", "🧤 NJIT shutout", "🎉 NJIT walk-off"],
        "volleyball": ["🧹 3–0 NJIT sweep", "🔴 3–1 NJIT", "😤 3–2 NJIT comeback", "🔥 NJIT wins every set by 5+"],
        "tennis": ["🧹 NJIT 4–0", "🔴 NJIT 4–1", "🔴 NJIT 4–2", "😤 NJIT 4–3, clutch"],
    }[fam]
    qs = [f"{c['e']} Call it now: how does NJIT win {c['matchup']} on {c['day']}?",
          f"{c['e']} 2 days out. How big is the NJIT W vs {c['opp']}?",
          f"{c['e']} {c['day']}: {c['matchup']}. Pick the NJIT final score 👇",
          f"{c['e']} Lock in your NJIT win prediction for {c['matchup']} 🔒"]
    return rng.choice(qs), options


def _food_poll(c, g, rng):
    home = g["where"] == "home"
    qs = ([f"{c['e']} What are you grabbing before {c['matchup']} on {c['day']}?",
           f"{c['e']} Pre-game meal before we head to {c['where']}?",
           f"{c['e']} Official snack of {c['day']}'s home {c['noun']}?"] if home else
          [f"{c['e']} Watch-party menu for {c['matchup']} on {c['day']}?",
           f"{c['e']} What's the official snack of {c['day']}'s {c['noun']}?",
           f"{c['e']} You can only eat ONE thing while watching {c['matchup']}. What is it?"])
    return rng.choice(qs), rng.sample(FOOD, 5)


def _player_poll(c, g, roster, rng):
    fam = _family(g["sport"])
    pool = [p for p in roster if p.get("name")]
    if fam in SCORE_WORDS and fam != "tennis":
        skip = NON_SCORERS.get(fam, set())
        pool = [p for p in pool if (p.get("pos") or "").upper() not in skip] or pool
    if len(pool) < 3:
        return None
    picks = rng.sample(pool, min(4, len(pool)))
    ans = [(f"#{p['num']} " if p.get("num") else "") + p["name"] for p in picks]
    if c["is_event"] or fam == "meet":
        qs = [f"{c['e']} Who has the standout performance at {c['matchup']} on {c['day']}?",
              f"{c['e']} Who's your Highlander to watch at {c['matchup']}?"]
    else:
        qs = [f"{c['e']} Who {SCORE_WORDS.get(fam, 'leads NJIT')} vs {c['opp']} on {c['day']}?",
              f"{c['e']} Player of the game vs {c['opp']}? Make your pick 👇",
              f"{c['e']} Who's going off on {c['day']}? 🔥",
              f"{c['e']} Your X-factor for {c['matchup']}?"]
    return rng.choice(qs), ans + ["🤷 Someone else!"]


FUN = [
    ("{e} Where are you watching {matchup} on {day}?",
     ["🏟️ In person", "🛋️ On the couch", "📱 Sneaking it in class", "👯 With the crew", "🍻 At a watch party"]),
    ("{e} Game-day fit check for {day}?",
     ["🔴 Full red, head to toe", "👕 Vintage NJIT gear", "🧢 Just the hat", "🧥 Whatever's clean lol"]),
    ("{e} Be honest: what's your game-day superstition?",
     ["🧦 Lucky socks", "🍕 Same meal every time", "🤐 Never say 'shutout' out loud", "🪑 Same seat, always", "😎 None, I'm built different"]),
    ("{e} Hype level for {day}, 1 to 🔥?",
     ["🔥", "🔥🔥", "🔥🔥🔥", "🔥🔥🔥🔥 I'm already yelling"]),
    ("{e} Best way to celebrate a W?",
     ["🕺 Dance it out", "🍕 Team pizza", "📸 Post it everywhere", "🗣️ Scream in the group chat"]),
    ("{e} Pick the warm-up playlist for {day}",
     ["🎤 Hip-hop", "🎧 EDM", "🎸 Rock", "💃 Reggaeton", "🎶 Throwbacks"]),
    ("{e} How many times will you check the score during class on {day}?",
     ["😇 Zero, I'm focused", "📱 Every 10 minutes", "👀 Constantly", "🏃 Skipping class to watch"]),
    ("{e} Who's the loudest Highlander fan you know?",
     ["🙋 Me, obviously", "👯 My roommate", "👨‍👩‍👧 My family", "🗡️ The mascot"]),
]


def _fun_poll(c, g, rng):
    q, ans = rng.choice(FUN)
    return q.format(e=c["e"], matchup=c["matchup"], day=c["day"]), ans


PREVIEW_INTROS = [
    "2 days until {matchup} {e} ({day}, {time}). Let's hear it 👇",
    "{day}: {matchup} {e} Quick poll while we wait 👇",
    "Countdown's on ⏳ {matchup}, {day} at {time}. Vote below 👇",
    "{e} {Matchup} is {day}! Settle this for me 👇",
    "Getting ready for {day} {e} {matchup}. Your turn 👇",
]
PREVIEW_KINDS = ["result", "food", "players", "fun"]


def build_preview_poll(game: dict, sport: dict, state: dict, roster: list | None = None, now=None, rng=random):
    """Fun poll 2 days before a game. Rotates result → food → players → fun per sport."""
    ctx = _ctx(game, sport)
    cur = state.setdefault("preview_kind", {})
    # each sport starts at a different poll type, so week one isn't all score predictions
    i = cur.get(game["sport"], sum(map(ord, game["sport"])) % len(PREVIEW_KINDS) - 1)
    for _ in range(len(PREVIEW_KINDS)):
        i = (i + 1) % len(PREVIEW_KINDS)
        kind = PREVIEW_KINDS[i]
        if kind == "result":
            qa = _result_poll(ctx, game, rng)
        elif kind == "food":
            qa = _food_poll(ctx, game, rng)
        elif kind == "players":
            qa = _player_poll(ctx, game, roster or [], rng)
        else:
            qa = _fun_poll(ctx, game, rng)
        if qa:
            break
    cur[game["sport"]] = i
    intro = PREVIEW_INTROS[_pick(f"{game['sport']}:preview_intro", len(PREVIEW_INTROS), state, rng)]
    intro = intro.format(matchup=ctx["matchup"], Matchup=ctx["Matchup"], e=ctx["e"], day=ctx["day"], time=ctx["time"])
    payload = _poll(qa[0], qa[1], _hours_until(game, now, after=0, default=48), intro=intro)
    payload["_kind"] = kind  # for logs/preview only; stripped before sending
    return payload


def plain_text(payload: dict) -> str:
    """Readable preview of a payload (used for the preview file and tests)."""
    parts = []
    if payload.get("content"):
        parts.append(payload["content"])
    if payload.get("poll"):
        p = payload["poll"]
        parts.append(f"[poll, {p['duration']}h] {p['question']['text']}")
        parts.extend("  ◻ " + a["poll_media"]["text"] for a in p["answers"])
    for e in payload.get("embeds", []):
        parts.append(f"[embed] {e.get('title', '')}")
        if e.get("description"):
            parts.append(e["description"])
    text = "\n".join(parts)
    return re.sub(r"\n{3,}", "\n\n", text)
