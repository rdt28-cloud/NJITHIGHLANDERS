"""Decides which alerts are due and sends them to each sport's channel.

Alert plan (all times Eastern):
  AWAY / neutral  · morning of game day (9:00 AM)  → "game day" alert
                  · 15 minutes before start         → "we're live on <stream>"
  HOME            · morning of game day (9:00 AM)  → "we're hosting" alert
                  · 45 minutes before start         → "pull up & fill the stands"
Games with a TBA/TBD time get the morning alert only.
"""
from __future__ import annotations

import json
import math
import os
import time
from datetime import datetime, timedelta

from . import messages
from .schedule import ET
from .sports import SPORTS

MORNING_HOUR = 9
AWAY_LEAD_MIN = 15
HOME_LEAD_MIN = 45
GRACE_MIN = 15  # GitHub's scheduler can run a few minutes late; still send within this grace
POLLS = True    # post a fan prediction poll after each home-game morning alert


def due_alerts(games, now, sent):
    """Yield (kind, game, minutes_to_start) for every alert that should go out now."""
    for g in games:
        gdate = datetime.fromisoformat(g["date"]).date()
        start = datetime.fromisoformat(g["start"]) if g["start"] else None
        home = g["where"] == "home"

        # Morning alert
        morning_at = datetime(gdate.year, gdate.month, gdate.day, MORNING_HOUR, tzinfo=ET)
        if start and start - timedelta(hours=1) < morning_at:
            morning_at = max(start - timedelta(hours=2),
                             datetime(gdate.year, gdate.month, gdate.day, 6, tzinfo=ET))
        morning_until = start if start else morning_at.replace(hour=20)
        kind = "home_morning" if home else "away_morning"
        if f"{g['uid']}|{kind}" not in sent and morning_at <= now < morning_until:
            yield kind, g, None

        if not start:
            continue

        # Pre-game alert
        lead = HOME_LEAD_MIN if home else AWAY_LEAD_MIN
        kind = "home_pullup" if home else "away_live"
        fire_at = start - timedelta(minutes=lead)
        latest = start + timedelta(minutes=GRACE_MIN) if not home else start
        if f"{g['uid']}|{kind}" not in sent and fire_at <= now < latest:
            mins = math.ceil((start - now).total_seconds() / 60)
            yield kind, g, mins


def post(webhook_url, payload, attempts=4):
    import requests
    for _ in range(attempts):
        r = requests.post(webhook_url, json=payload, params={"wait": "true"}, timeout=20)
        if r.status_code == 429:
            time.sleep(float(r.json().get("retry_after", 2)) + 0.5)
            continue
        r.raise_for_status()
        return True
    return False


def load_webhooks():
    raw = os.environ.get("DISCORD_WEBHOOKS", "").strip()
    if not raw:
        return {}
    data = json.loads(raw)
    return {k: v for k, v in data.items() if isinstance(v, str) and v.startswith("https://")}


def run(games, state, now=None, webhooks=None, dry_run=False, log=print):
    now = now or datetime.now(ET)
    webhooks = load_webhooks() if webhooks is None else webhooks
    sent = state.setdefault("sent", {})
    count = 0
    for kind, g, mins in due_alerts(games, now, sent):
        sport = SPORTS.get(g["sport"])
        if not sport:
            continue
        payloads = [(kind, messages.build(kind, g, sport, state, minutes_to_start=mins))]
        if kind == "home_morning" and POLLS:
            payloads.append(("home_poll", messages.build_poll(g, sport, state, now=now)))
        url = webhooks.get(g["sport"])
        for k, payload in payloads:
            label = f"{k:13s} {g['sport']:22s} {g['opponent']}"
            if dry_run or not url:
                log(f"[{'dry-run' if dry_run else 'no webhook'}] {label}")
                if dry_run:
                    log("    " + messages.plain_text(payload).replace("\n", "\n    "))
            else:
                try:
                    post(url, payload)
                    log(f"[sent] {label}")
                except Exception as e:  # a failed poll must never block the alert itself
                    if k != "home_poll":
                        raise
                    log(f"[poll skipped] {label}: {e}")
                time.sleep(1)
        if not dry_run:
            sent[f"{g['uid']}|{kind}"] = now.isoformat()
        count += 1

    cutoff = (now - timedelta(days=30)).isoformat()
    state["sent"] = {k: v for k, v in sent.items() if v >= cutoff}
    return count
