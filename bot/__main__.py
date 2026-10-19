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
from .sports import SPORTS

DATA = Path(__file__).resolve().parent.parent / "data"
GAMES = DATA / "games.json"
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
    return 0


def cmd_alerts():
    games = _load(GAMES, {}).get("games", [])
    state = _load(STATE, {})
    n = alerts.run(games, state)
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
        alerts.post(url, {"username": "NJIT Game Day", "allowed_mentions": {"parse": []},
                          "content": f"{sport['emoji']} NJIT Game Day bot is connected to **{sport['name']}**! "
                                     "Game-day alerts will show up here. 🔴⚪"})
        print(f"  ✓ {key}")
    missing = [k for k in SPORTS if k not in hooks]
    if missing:
        print("No webhook set for: " + ", ".join(missing))
    return 0


def cmd_preview(days=14):
    """Simulate the next N days minute by minute and write every alert to preview.md."""
    games = _load(GAMES, {}).get("games", [])
    state, out = {}, []
    now = datetime.now(ET).replace(second=0, microsecond=0)
    now = now.replace(minute=now.minute - now.minute % 5)  # the real job runs on :00, :05, :10…
    end = now + timedelta(days=int(days))
    random.seed(7)
    t = now
    while t < end:
        for kind, g, mins in list(alerts.due_alerts(games, t, state.setdefault("sent", {}))):
            payloads = [(kind, messages.build(kind, g, SPORTS[g["sport"]], state, minutes_to_start=mins, ping=alerts.PING_ROLES))]
            if kind == "home_morning" and alerts.POLLS:
                payloads.append(("home_poll", messages.build_poll(g, SPORTS[g["sport"]], state, now=t)))
            state["sent"][f"{g['uid']}|{kind}"] = t.isoformat()
            for k, payload in payloads:
                text = messages.plain_text(payload)
                text = text.replace(f"<@&{SPORTS[g['sport']].get('role_id')}>", f"@{SPORTS[g['sport']]['name']} Fans")
                out.append(f"### {t.strftime('%a %b %d, %I:%M %p')} · #{g['sport']} · {k}\n\n"
                           + "\n".join("> " + line for line in text.splitlines()) + "\n")
        t += timedelta(minutes=5)
    _save_md = DATA / "preview.md"
    _save_md.write_text(f"# Upcoming alerts, next {days} days ({len(out)} alerts)\n\n" + "\n".join(out))
    print(f"Wrote {len(out)} alerts to {_save_md}")
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
