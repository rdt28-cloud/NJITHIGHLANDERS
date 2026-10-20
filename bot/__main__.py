"""NJIT Game Day bot.

  python -m bot refresh        re-read every NJIT schedule (once a day)
  python -m bot alerts         send any alerts that are due right now
  python -m bot test           post a test message to every configured channel
  python -m bot preview [days] write data/preview.md showing upcoming alerts
"""
from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

from . import alerts, messages, schedule
from .schedule import ET
from .sports import AVATAR_URL, DISPLAY_NAME, SPORTS

DATA = Path(__file__).resolve().parent.parent / "data"
GAMES = DATA / "games.json"
ROSTERS = DATA / "rosters.json"
STATE = DATA / "state.json"


def _load(path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def cmd_refresh():
    print("Reading NJIT schedules (30s apart, as njithighlanders.com asks)…")
    pages = schedule.fetch_all()
    games = schedule.build_games(pages)
    if not games:
        print("No games parsed. Keeping the previous games.json.")
        return 1
    old = _load(GAMES, {}).get("games", [])
    # keep sports whose page failed today, so one outage doesn't wipe them
    got = {raw["sport"] for raw in pages.values()}
    today = datetime.now(ET).date().isoformat()
    kept = [g for g in old if g["sport"] not in got and g["date"] >= today]
    games = sorted(games + kept, key=lambda g: (g["date"], g["start"] or "99", g["sport"]))
    _save(GAMES, {"updated": datetime.now(ET).isoformat(timespec="seconds"), "games": games})
    print(f"Saved {len(games)} games.")

    # rosters change rarely: re-read them once a week (player-pick polls use them)
    old_r = _load(ROSTERS, {})
    try:
        age = datetime.now(ET) - datetime.fromisoformat(old_r.get("updated", "2000-01-01T00:00:00-05:00"))
    except ValueError:
        age = timedelta(days=99)
    if age >= timedelta(days=7) or "--rosters" in sys.argv:
        print("Reading NJIT rosters…")
        fresh = schedule.fetch_rosters()
        merged = {**old_r.get("rosters", {}), **{k: v for k, v in fresh.items() if v}}
        _save(ROSTERS, {"updated": datetime.now(ET).isoformat(timespec="seconds"), "rosters": merged})
        print(f"Saved rosters for {len(merged)} sports.")
    return 0


def cmd_alerts():
    games = _load(GAMES, {}).get("games", [])
    state = _load(STATE, {})
    n = alerts.run(games, state, rosters=_load(ROSTERS, {}).get("rosters", {}))
    _save(STATE, state)
    print(f"{n} alert(s) handled.")
    return 0


def cmd_test():
    hooks = alerts.load_webhooks()
    if not hooks:
        print("DISCORD_WEBHOOKS secret is empty or invalid JSON.")
        return 1
    for key, url in hooks.items():
        sport = SPORTS.get(key)
        if not sport:
            print(f"  ! '{key}' is not a known sport key (see bot/sports.py)")
            continue
        alerts.post(url, {"username": DISPLAY_NAME, "avatar_url": AVATAR_URL, "allowed_mentions": {"parse": []},
                          "content": f"{sport['emoji']} Quick check, game-day updates for **{sport['name']}** "
                                     "will show up right here. Go Highlanders 🔴⚪"})
        print(f"  ✓ {key}")
    missing = [k for k in SPORTS if k not in hooks]
    if missing:
        print("No webhook set for: " + ", ".join(missing))
    return 0


def cmd_preview(days=14):
    """Simulate the next N days in 5-minute steps and write every post to preview.md."""
    games = _load(GAMES, {}).get("games", [])
    rosters = _load(ROSTERS, {}).get("rosters", {})
    state, out = {}, []
    now = datetime.now(ET).replace(second=0, microsecond=0)
    now = now.replace(minute=now.minute - now.minute % 5)  # the real job runs on :00, :05, :10…
    end = now + timedelta(days=int(days))
    random.seed(7)
    t = now
    while t < end:
        for kind, g, mins in list(alerts.due_alerts(games, t, state.setdefault("sent", {}))):
            sport = SPORTS[g["sport"]]
            for k, payload in alerts.payloads_for(kind, g, sport, state, mins, t, rosters):
                text = messages.plain_text(payload)
                text = text.replace(f"<@&{sport.get('role_id')}>", f"@{sport['name']} Fans")
                label = k + (f" ({payload['_kind']})" if payload.get("_kind") else "")
                out.append(f"### {t.strftime('%a %b %d, %I:%M %p')} · #{g['sport']} · {label}\n\n"
                           + "\n".join("> " + line for line in text.splitlines()) + "\n")
            state["sent"][alerts.sent_key(kind, g)] = t.isoformat()
        t += timedelta(minutes=5)
    _save_md = DATA / "preview.md"
    _save_md.write_text(f"# Upcoming posts, next {days} days ({len(out)} posts)\n\n" + "\n".join(out))
    print(f"Wrote {len(out)} posts to {_save_md}")
    return 0


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "alerts"
    if cmd == "refresh":
        return cmd_refresh()
    if cmd == "alerts":
        return cmd_alerts()
    if cmd == "test":
        return cmd_test()
    if cmd == "preview":
        return cmd_preview(*(argv[2:3] or [14]))
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
