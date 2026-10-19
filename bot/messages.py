"""Alert messages. Every alert type has many templates in different formats
(plain text, headline posts, embeds, countdown cards, lists...). The bot
picks one at random but never repeats any of the last few it used for
that sport + alert type, so the channel never feels copy-pasted.
"""
from __future__ import annotations

import random
import re
from datetime import datetime

NJIT_RED = 0xD22630
GOLD = 0xF2C14E
NAVY = 0x1F2A44
WHITE = 0xFFFFFF

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
    return s.replace(":00 ", " ") + " ET"


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
        return g["venue"] if g["venue"] not in ("", "TBA") else "Newark, NJ"
    return g["location"]


def _ctx(g, sport, minutes_to_start=None):
    m = minutes_to_start
    if m is None or m <= 0:
        countdown = "right now"
        mins_word = "NOW"
    else:
        countdown = f"in {m} minute{'s' if m != 1 else ''}"
        mins_word = f"{m} MIN"
    unconfirmed = bool(g["stream"].get("unconfirmed"))
    name, url = g["stream"]["name"], g["stream"]["url"]
    return {
        # lines that read right whether or not NJIT has listed a stream
        "watch": (f"📲 Game info & live updates: {url}" if unconfirmed
                  else f"📺 Watch on {name}: {url}"),
        "watch_md": (f"[Game info & updates]({url})" if unconfirmed else f"[{name}]({url})"),
        "watch_short": ("live updates on the game page" if unconfirmed else f"streaming on {name}"),
        "cheer": ("Follow along and send good vibes!" if unconfirmed else "Can't be there? Watch with us online."),
        "e": sport["emoji"], "sport": sport["name"], "noun": sport["noun"],
        "start_word": sport["start_word"], "opp": g["opponent"],
        "matchup": matchup(g), "time": _time(g), "where": _where_line(g),
        "stream": "the game page" if g["stream"].get("unconfirmed") else g["stream"]["name"],
        "stream_url": g["stream"]["url"],
        "schedule": g["schedule_url"], "countdown": countdown, "mins": mins_word,
        "is_event": _is_event(g),
    }


def _embed(title, desc=None, color=NJIT_RED, fields=None, footer=None, url=None):
    e = {"title": title, "color": color}
    if desc:
        e["description"] = desc
    if fields:
        e["fields"] = [{"name": n, "value": v, "inline": inline} for n, v, inline in fields]
    if footer:
        e["footer"] = {"text": footer}
    if url:
        e["url"] = url
    return e


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


HYPE = ["Go Highlanders! 🔴⚪", "Let's go NJIT! 🗡️", "Highlander pride! 🔴", "Bring the energy! ⚡",
        "Red and white all day! 🔴⚪", "Let's get this W! 💪", "Highlanders rise! 🏴"]


def _hype():
    return random.choice(HYPE)


# ------------------------------------------------------- AWAY: morning alert

def _away_morning(c):
    soon = ("We'll ping you right before it starts. 🔔" if c["stream"] == "the game page"
            else f"We'll ping you when we go live on {c['stream']}. 🔔")
    return [
        lambda: {"content": f"{c['e']} **GAME DAY!** {c['e']}\n{c['sport']}: **{_cap(c['matchup'])}**\n🕒 {c['time']} · 📍 {c['where']}\n{c['watch']}\n{_hype()}"},
        lambda: {"embeds": [_embed(f"{c['e']} It's {c['sport']} game day!",
                                   f"The Highlanders hit the road today: **{c['matchup']}**.",
                                   fields=[("🕒 Start", c["time"], True), ("📍 Where", c["where"], True),
                                           ("📺 Watch", c["watch_md"], True)],
                                   footer=f"{c['cheer']} {_hype()}")]},
        lambda: {"content": f"☀️ Rise and shine, Highlanders!\nNJIT {c['sport']} is on the road today {c['e']}\n> **{_cap(c['matchup'])}**\n> {c['time']} in {c['where']}\n{soon}"},
        lambda: {"content": f"🚌 **ROAD TRIP** 🚌\n{c['e']} {c['sport']} heads to {c['where']} today.\n\n**{_cap(c['matchup'])}** · {c['time']}\n{c['watch']}"},
        lambda: {"embeds": [_embed(f"📅 TODAY · {c['matchup'].upper()}"[:256],
                                   f"{c['e']} **{c['sport']}**\n\n🕒 **{c['time']}**\n📍 {c['where']}\n{c['watch_md']}",
                                   color=NAVY, footer=_hype())]},
        lambda: {"content": f"{c['e']}{c['e']}{c['e']}\n# GAME DAY\n**{c['sport']}** · {_cap(c['matchup'])}\n-# {c['time']} · {c['where']} · {c['watch_short']}"},
        lambda: {"content": f"Mark your calendar 🗓️ {c['sport']} competes today!\n• **What:** {_cap(c['matchup'])}\n• **Time:** {c['time']}\n• **Location:** {c['where']}\n• {c['watch']}\n{_hype()}"},
        lambda: {"embeds": [_embed(f"{c['e']} Away {c['noun']} today",
                                   f"*{_cap(c['start_word'])} at {c['time']}.*\n**{_cap(c['matchup'])}** in {c['where']}.\n\n{c['cheer']} 👉 {c['watch_md']}",
                                   color=GOLD, url=c["schedule"])]},
    ]


# --------------------------------------------- AWAY: 15 minutes / we're live

def _away_live(c):
    return [
        lambda: {"content": f"🔴 **WE'RE LIVE {c['countdown'].upper()}!**\n{c['e']} {c['matchup']} is on **{c['stream']}**\n👉 {c['stream_url']}"},
        lambda: {"embeds": [_embed(f"🔴 LIVE on {c['stream']}",
                                   f"{c['e']} **{c['sport']}**: {c['matchup']}\n{_cap(c['start_word'])} {c['countdown']}!",
                                   url=c["stream_url"], fields=[("Watch now", f"[Open {c['stream']}]({c['stream_url']})", False)],
                                   footer=_hype())]},
        lambda: {"content": f"⏰ {c['mins']} TO GO ⏰\n{c['e']} {c['sport']} {c['start_word']} {c['countdown']}. Grab a seat on the couch and tune in to {c['stream']}: {c['stream_url']}"},
        lambda: {"content": f"📺 Highlanders, tune in! {c['e']}\n**{c['matchup']}** goes live on {c['stream']} {c['countdown']}.\n<{c['stream_url']}>\n{_hype()}"},
        lambda: {"embeds": [_embed(f"⏱️ {c['mins']} · {c['matchup']}",
                                   f"{c['e']} Streaming on **[{c['stream']}]({c['stream_url']})**\nDrop your predictions below 👇",
                                   color=NAVY)]},
        lambda: {"content": f"# 🔴 LIVE SOON\n{c['e']} {c['sport']} · **{c['matchup']}**\n-# {c['start_word']} {c['countdown']} · watch on {c['stream']}: {c['stream_url']}"},
        lambda: {"content": f"3… 2… 1… {c['e']}\nNJIT {c['sport']} is about to go live on **{c['stream']}** ({c['countdown']})!\n🔗 {c['stream_url']}"},
        lambda: {"embeds": [_embed(f"{c['e']} Lights, camera, Highlanders!",
                                   f"We're live on {c['stream']} {c['countdown']}.\n**{c['matchup']}** · {c['where']}",
                                   color=GOLD, url=c["stream_url"], footer="Click the title to watch · " + _hype())]},
    ]


# ------------- AWAY: 15 minutes, when NJIT hasn't listed a stream (meets, etc.)

def _away_soon(c):
    return [
        lambda: {"content": f"⏰ **{c['mins']} TO GO!** {c['e']}\n{c['sport']}: **{c['matchup']}** starts {c['countdown']} in {c['where']}.\n📲 Game info & live updates: {c['schedule']}\n{_hype()}"},
        lambda: {"embeds": [_embed(f"{c['e']} Almost go time!",
                                   f"**{c['matchup']}**\n{_cap(c['start_word'])} {c['countdown']} · {c['where']}",
                                   url=c["schedule"], fields=[("Follow along", f"[Schedule, stream & stats]({c['schedule']})", False)],
                                   footer=_hype())]},
        lambda: {"content": f"🔔 Heads up, Highlanders!\n{c['e']} {c['sport']} {c['start_word']} {c['countdown']}. Send the squad some good vibes 🙌\n<{c['schedule']}>"},
        lambda: {"content": f"# {c['e']} {c['mins']}\n**{c['matchup']}** · {c['where']}\n-# {c['start_word']} {c['countdown']} · updates: {c['schedule']}"},
        lambda: {"embeds": [_embed(f"⏱️ {c['matchup']}",
                                   f"{c['e']} {_cap(c['start_word'])} {c['countdown']}!\nDrop your predictions below 👇",
                                   color=NAVY, url=c["schedule"])]},
        lambda: {"content": f"3… 2… 1… {c['e']}\nNJIT {c['sport']} is about to get going ({c['countdown']}) at {c['where']}!\nCheck the game page for any stream or live stats: {c['schedule']}"},
    ]


# -------------------------------------------------------- HOME: morning alert

def _home_morning(c):
    return [
        lambda: {"content": f"🏟️ **WE'RE HOSTING TODAY!** 🏟️\n{c['e']} {c['sport']}: **{c['matchup']}**\n🕒 {c['time']} · 📍 {c['where']}\nPack the stands, Highlanders! 🔴⚪"},
        lambda: {"embeds": [_embed(f"{c['e']} HOME GAME DAY",
                                   f"The Highlanders host today, and we need YOU there!\n**{c['matchup']}**",
                                   fields=[("🕒 Start", c["time"], True), ("📍 Venue", c["where"], True),
                                           ("📣 Bring", "Your loudest voice + your red", True)],
                                   footer=_hype())]},
        lambda: {"content": f"☀️ Good morning, NJIT!\nHome {c['noun']} today {c['e']}\n> **{c['matchup']}**\n> {c['time']} at {c['where']}\nBring a friend. Let's make it loud. 📣"},
        lambda: {"content": f"🔴⚪ **HOME SWEET HOME** ⚪🔴\n{c['e']} {c['sport']} defends Newark today!\n**{c['matchup']}** · {c['time']} · {c['where']}\nSee you in the stands 👀"},
        lambda: {"embeds": [_embed(f"📣 Newark, we play today!",
                                   f"{c['e']} **{c['sport']}**\n{c['matchup']}\n\n🕒 **{c['time']}**\n📍 **{c['where']}**\n\nFill the stands and show them whose house this is. 🏠",
                                   color=GOLD)]},
        lambda: {"content": f"{c['e']}{c['e']}{c['e']}\n# HOME {c['noun'].upper()} TODAY\n**{c['matchup']}**\n-# {c['time']} · {c['where']} · wear red!"},
        lambda: {"content": f"Today's plans? Sorted ✅\n• **What:** {c['sport']}, {c['matchup']}\n• **When:** {c['time']}\n• **Where:** {c['where']}\n• **Dress code:** NJIT red 🔴\n{_hype()}"},
        lambda: {"embeds": [_embed(f"{c['e']} {c['matchup']}",
                                   f"*We're hosting!* {_cap(c['start_word'])} at **{c['time']}** at {c['where']}.\nEvery seat filled = more noise = more wins. 📈",
                                   color=NAVY, url=c["schedule"], footer=_hype())]},
    ]


# ---------------------------------------------- HOME: 45 minutes / pull up!

def _home_pullup(c):
    return [
        lambda: {"content": f"📣 **PULL UP, HIGHLANDERS!** 📣\n{c['e']} {c['matchup']}: {c['start_word']} {c['countdown']} at {c['where']}.\nLet's fill those stands! 🏟️🔴"},
        lambda: {"embeds": [_embed(f"🏃‍♂️ Get to {c['where']}!",
                                   f"{c['e']} **{c['sport']}** {c['start_word']} {c['countdown']}.\nThe best seats go fast. Grab yours and bring the noise. 🔊",
                                   fields=[("Matchup", c["matchup"], True), ("Start", c["time"], True)],
                                   footer=_hype())]},
        lambda: {"content": f"⏰ **{c['mins']} UNTIL {c['start_word'].upper()}** ⏰\n{c['e']} {c['matchup']} at {c['where']}\nDrop what you're doing and come support the squad! 🙌"},
        lambda: {"content": f"🚨 Stands check 🚨\n{c['e']} {c['sport']} {c['start_word']} {c['countdown']}. We want a FULL house at {c['where']}!\nTag a friend who's coming 👇"},
        lambda: {"embeds": [_embed(f"🔥 It's almost time, Newark!",
                                   f"{c['e']} {c['matchup']}\n📍 **{c['where']}**\n🕒 {c['start_word']} {c['countdown']}\n\nRed out the stands. Every cheer counts! 🔴",
                                   color=GOLD)]},
        lambda: {"content": f"# 🏟️ DOORS ARE OPEN\n{c['e']} **{c['matchup']}**\n-# {c['start_word']} {c['countdown']} · {c['where']} · be loud, be proud"},
        lambda: {"content": f"Still on the fence? 🤔 Here's your sign:\n{c['e']} {c['sport']} plays at home {c['countdown']}.\n📍 {c['where']} · {c['time']}\nCome watch the Highlanders work! 💪"},
        lambda: {"embeds": [_embed(f"{c['e']} HIGHLANDERS NEED YOU",
                                   f"{_cap(c['start_word'])} {c['countdown']} at **{c['where']}**.\nShow up, show out, and make it a home-field advantage. 🗡️",
                                   color=NAVY, footer=_hype())]},
    ]


TEMPLATES = {
    "away_morning": _away_morning,
    "away_live": _away_live,
    "away_soon": _away_soon,
    "home_morning": _home_morning,
    "home_pullup": _home_pullup,
}


def build(kind: str, game: dict, sport: dict, state: dict, minutes_to_start=None, rng=random):
    """Return a Discord webhook payload for an alert, rotating formats.

    `state["recent"]` remembers which templates were used lately per
    sport + alert type so the same format never shows up twice in a row.
    """
    ctx = _ctx(game, sport, minutes_to_start)
    if kind == "away_live" and game["stream"].get("unconfirmed"):
        kind = "away_soon"  # don't claim "we're live on X" when NJIT hasn't listed a stream
    options = TEMPLATES[kind](ctx)
    recent_key = f"{game['sport']}:{kind}"
    recent = state.setdefault("recent", {}).setdefault(recent_key, [])
    avoid = recent[-min(len(options) - 1, 4):] if recent else []
    choices = [i for i in range(len(options)) if i not in avoid] or list(range(len(options)))
    idx = rng.choice(choices)
    recent.append(idx)
    del recent[:-6]
    payload = options[idx]()
    promo = game.get("promo")
    if promo and kind.startswith("home"):
        extra = f"🎉 **{promo}**: don't miss it!"
        if payload.get("embeds"):
            e = payload["embeds"][0]
            e["description"] = (e.get("description", "") + "\n\n" + extra).strip()
        else:
            payload["content"] += "\n" + extra
    payload["allowed_mentions"] = {"parse": []}  # never ping @everyone by accident
    payload["username"] = "NJIT Game Day"
    return payload


def plain_text(payload: dict) -> str:
    """Readable preview of a payload (used for the preview file and tests)."""
    parts = []
    if payload.get("content"):
        parts.append(payload["content"])
    for e in payload.get("embeds", []):
        parts.append(f"[embed] {e.get('title', '')}")
        if e.get("description"):
            parts.append(e["description"])
        for f in e.get("fields", []):
            parts.append(f"  {f['name']}: {f['value']}")
        if e.get("footer"):
            parts.append(f"  — {e['footer']['text']}")
    text = "\n".join(parts)
    return re.sub(r"\n{3,}", "\n\n", text)
