"""Reads NJIT schedule pages and turns them into a clean list of games.

njithighlanders.com asks crawlers to wait 30 seconds between requests and
blocks the /services/ export endpoints, so this only reads the normal
public schedule pages, once a day, 30 seconds apart.
"""
from __future__ import annotations

import json
import re
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

TZ_OFFSETS_FROM_ET = {  # hours to ADD to a listed local time to get ET
    "ET": 0, "EST": 0, "EDT": 0,
    "CT": 1, "CST": 1, "CDT": 1,
    "MT": 2, "MST": 2, "MDT": 2,
    "PT": 3, "PST": 3, "PDT": 3,
}


# ---------------------------------------------------------------- extraction

def extract_raw(html: str, path: str) -> dict:
    """Pull the raw fields out of one schedule page (same shape the browser
    loader produced, so both paths share `normalize`)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    ld = []
    for s in soup.select('script[type="application/ld+json"]'):
        try:
            j = json.loads(s.string or s.get_text() or "")
        except Exception:
            continue
        for x in (j if isinstance(j, list) else [j]):
            if isinstance(x, dict) and x.get("@type") == "SportsEvent":
                ld.append({"name": x.get("name"), "start": x.get("startDate"),
                           "loc": (x.get("location") or {}).get("name")})

    def txt(el):
        return re.sub(r"\s+", " ", el.get_text(" ")).strip() if el else None

    games = []
    for li in soup.select("li.sidearm-schedule-game"):
        links, seen = [], set()
        for a in li.select("a"):
            label = txt(a) or a.get("aria-label") or a.get("title") or ""
            item = f"{label} -> {a.get('href', '')}"
            if item not in seen:
                seen.add(item)
                links.append(item)
        games.append({
            "id": li.get("data-game-id"),
            "cls": " ".join(li.get("class", [])),
            "dateSpans": [txt(s) for s in li.select(".sidearm-schedule-game-opponent-date span")],
            "vs": txt(li.select_one(".sidearm-schedule-game-conference-vs")),
            "opp": txt(li.select_one(".sidearm-schedule-game-opponent-name")),
            "loc": txt(li.select_one(".sidearm-schedule-game-location")),
            "links": links,
            "imgs": [f"{i.get('alt', '')}|{i.get('data-src') or i.get('src') or ''}" for i in li.select("img")],
            "promo": txt(li.select_one(".sidearm-schedule-game-promotion-name")),
        })
    title = soup.title.get_text().strip() if soup.title else ""
    return {"path": path, "title": title, "games": games, "ld": ld}


# ------------------------------------------------------------- normalization

DATE_RE = re.compile(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2})")
TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*([ap])\.?\s*m\.?", re.I)
TZ_RE = re.compile(r"\b(E[SD]?T|C[SD]?T|M[SD]?T|P[SD]?T)\b")


WEEKDAYS = {d: i for i, d in enumerate(["mon", "tue", "wed", "thu", "fri", "sat", "sun"])}


def _year_for(month: int, day: int, weekday: int | None, ld_dates: list[date], today: date):
    """Pick the year for a 'Nov 3 (Tue)' style date. Uses the page's structured
    data first, then the listed weekday (which also exposes stale old-season
    pages: their weekdays don't match any nearby year). Returns None if unsure."""
    for d in ld_dates:
        if d.month == month and d.day == day and (weekday is None or d.weekday() == weekday):
            return d.year
    best = None
    for y in (today.year - 1, today.year, today.year + 1):
        try:
            cand = date(y, month, day)
        except ValueError:
            continue
        if weekday is not None and cand.weekday() != weekday:
            continue
        if best is None or abs((cand - today).days) < abs((best - today).days):
            best = cand
    return best.year if best else None


def parse_time(text: str):
    """'7pm' -> (19, 0, 'ET'); 'TBD' / 'All Day' -> None."""
    if not text:
        return None
    t = text.strip()
    if re.search(r"\bnoon\b", t, re.I):
        return (12, 0, "ET")
    m = TIME_RE.search(t)
    if not m:
        return None
    hour = int(m.group(1)) % 12 + (12 if m.group(3).lower() == "p" else 0)
    minute = int(m.group(2) or 0)
    tz = TZ_RE.search(t[m.end():m.end() + 8])
    return (hour, minute, tz.group(1) if tz else "ET")


COVERAGE_LOGOS = {  # filename fragment of the TV/stream logo NJIT shows -> platform
    "espn": "ESPN+", "flo": "FloSports", "nec": "NEC Front Row", "youtube": "YouTube",
    "acc": "ACC Network", "bigten": "Big Ten+", "b1g": "Big Ten+", "cbs": "CBS Sports",
    "snyit": "SNY", "sny": "SNY", "nbc": "NBC Sports", "fox": "FOX Sports", "hudl": "Hudl",
}


def detect_stream(raw: dict, schedule_url: str = "") -> dict:
    """Best stream for US fans: an explicit watch link, else the TV/stream logo
    NJIT shows for the game, else a pointer to the schedule page."""
    from .sports import ESPN_PLUS_URL
    candidates = []
    watch_words = re.compile(r"\b(watch|stream|video|tv|espn\+?|flosports|youtube|front row)\b", re.I)
    for item in raw.get("links", []):
        label, _, url = item.partition(" -> ")
        low_label, low_url = label.lower(), url.lower()
        if any(w in low_label for w in ("stats", "history", "ticket", "recap", "box score", "preview")):
            continue
        if "espn" in low_label or "espn.com" in low_url or "plus.espn" in low_url:
            return {"name": "ESPN+", "url": url if url.startswith("http") else ESPN_PLUS_URL}
        if watch_words.search(label) or any(d in low_url for d in ("flosports.tv", "youtube.com", "youtu.be")):
            if "international" in low_label:
                continue  # America East's international feed isn't for US viewers
            name = label.strip() or "Live Stream"
            if "americaeast.com" in low_url:
                name = "America East Live"
            elif name.lower() in ("watch", "video", "live video", "stream"):
                name = "Live Stream"
            candidates.append({"name": name, "url": url})

    logo_platforms = []
    for img in raw.get("imgs", []):
        alt, _, src = img.partition("|")
        if "/logos/" in src:  # opponent / conference logos, not TV
            continue
        name = (alt + " " + src.rsplit("/", 1)[-1]).lower()
        for frag, platform in COVERAGE_LOGOS.items():
            if frag in name and platform not in logo_platforms:
                logo_platforms.append(platform)
    # NJIT's ESPN+ logo beats a generic "Watch" link: it's where US fans actually watch
    if "ESPN+" in logo_platforms:
        return {"name": "ESPN+", "url": ESPN_PLUS_URL}
    if candidates:
        return candidates[0]
    if logo_platforms:
        return {"name": logo_platforms[0], "url": schedule_url or ESPN_PLUS_URL}
    # Nothing listed: point fans at the game's schedule entry, where NJIT posts stream info.
    return {"name": "the live stream", "url": schedule_url or ESPN_PLUS_URL, "unconfirmed": True}


def normalize(raw_page: dict, sport_key: str, today: date | None = None) -> list[dict]:
    from .sports import SITE
    today = today or datetime.now(ET).date()
    ld_dates = []
    for x in raw_page.get("ld", []):
        try:
            ld_dates.append(datetime.fromisoformat((x.get("start") or "")[:19]).date())
        except ValueError:
            pass

    out = []
    for g in raw_page.get("games", []):
        spans = [s for s in (g.get("dateSpans") or []) if s]
        if not spans:
            continue
        m = DATE_RE.search(spans[0])
        if not m or m.group(1).lower()[:3] not in MONTHS:
            continue
        month, day = MONTHS[m.group(1).lower()[:3]], int(m.group(2))
        wd = re.search(r"\(([A-Za-z]{3})", spans[0])
        weekday = WEEKDAYS.get(wd.group(1).lower()) if wd else None
        year = _year_for(month, day, weekday, ld_dates, today)
        if year is None:
            continue  # weekday doesn't fit any nearby year: an old season still on the page
        try:
            gdate = date(year, month, day)
        except ValueError:
            continue

        # spans look like ["Nov 3 (Tue)", "7pm"] or ["Oct 9 (Fri)", "- Oct 10 (Sat)", "3 Sessions"]
        rest = [s for s in spans[1:]
                if not re.fullmatch(r"-?\s*[A-Za-z]{3}[a-z]*\.?\s+\d{1,2}\s*(\([A-Za-z]+\))?", s)]
        time_text = " ".join(rest) if len(spans) > 1 else spans[0][m.end():]
        time_text = re.sub(r"\(.*?\)", "", time_text).strip()  # drop notes like "(New Start Time)"
        parsed = parse_time(time_text)
        start = None
        if parsed:
            h, mi, tz = parsed
            start = datetime(gdate.year, gdate.month, gdate.day, h, mi, tzinfo=ET)
            start += timedelta(hours=TZ_OFFSETS_FROM_ET.get(tz, 0))

        cls = g.get("cls") or ""
        if "home-game" in cls:
            where = "home"
        elif "neutral-game" in cls:
            where = "neutral"
        elif "away-game" in cls:
            where = "away"
        else:
            where = "home" if (g.get("vs") or "").lower().startswith("vs") and "newark" in (g.get("loc") or "").lower() else "away"

        loc = (g.get("loc") or "").strip()
        venue = loc
        if loc.lower().startswith("newark, nj"):
            venue = loc[len("newark, nj"):].strip() or "Newark, NJ"

        opp = re.sub(r"\s+", " ", g.get("opp") or "").strip()
        out.append({
            "uid": f"{sport_key}:{g.get('id') or gdate.isoformat() + ':' + opp}",
            "sport": sport_key,
            "opponent": opp or "TBA",
            "where": where,
            "date": gdate.isoformat(),
            "start": start.isoformat() if start else None,
            "time_text": time_text.strip() or "TBA",
            "location": loc or "TBA",
            "venue": venue or "TBA",
            "tournament": "tourney" in cls,
            "promo": (g.get("promo") or "").strip() or None,
            "stream": detect_stream(g, SITE + raw_page.get("path", "")),
            "schedule_url": SITE + raw_page.get("path", ""),
        })
    return out


# ------------------------------------------------------------------ fetching

def fetch_all(delay_seconds: int = 30) -> dict[str, dict]:
    """Download every schedule page politely. Returns {path: raw_page}."""
    import requests
    from .sports import SITE, SPORTS

    session = requests.Session()
    session.headers["User-Agent"] = (
        "NJIT-Gameday-Discord-Bot/1.0 (fan Discord notifications; once daily)")
    pages, first = {}, True
    for key, cfg in SPORTS.items():
        for path in cfg["paths"]:
            if not first:
                time.sleep(delay_seconds)
            first = False
            try:
                r = session.get(SITE + path, timeout=30)
                r.raise_for_status()
                raw = extract_raw(r.text, path)
                raw["sport"] = key
                pages[path] = raw
                print(f"  {key:22s} {path}: {len(raw['games'])} games")
            except Exception as e:  # keep going; one bad page shouldn't stop the rest
                print(f"  {key:22s} {path}: FAILED ({e})")
    return pages


def build_games(pages: dict[str, dict], today: date | None = None, keep_days_back: int = 2) -> list[dict]:
    today = today or datetime.now(ET).date()
    games, seen = {}, set()
    for raw in pages.values():
        for g in normalize(raw, raw["sport"], today):
            if date.fromisoformat(g["date"]) < today - timedelta(days=keep_days_back):
                continue
            # men's + women's pages listing the same meet (fencing) → one alert
            key = (g["sport"], g["date"], g["start"], re.sub(r"\W", "", g["opponent"].lower()))
            if key in seen:
                continue
            seen.add(key)
            games[g["uid"]] = g
    return sorted(games.values(), key=lambda g: (g["date"], g["start"] or "99", g["sport"]))


# ------------------------------------------------------------------- rosters

def extract_roster(html: str) -> list[dict]:
    """Players on a njithighlanders.com roster page: [{name, num, pos}]."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    def txt(el):
        return re.sub(r"\s+", " ", el.get_text(" ")).strip() if el else ""

    out = []
    for li in soup.select("li.sidearm-roster-player"):
        name = txt(li.select_one(".sidearm-roster-player-name h3"))
        if name:
            out.append({"name": name,
                        "num": txt(li.select_one(".sidearm-roster-player-jersey-number")),
                        "pos": txt(li.select_one(".sidearm-roster-player-position-long-short"))})
    return out


def fetch_rosters(delay_seconds: int = 30) -> dict[str, list[dict]]:
    """Download every roster page politely. Returns {sport_key: [players]}."""
    import requests
    from .sports import SITE, SPORTS

    session = requests.Session()
    session.headers["User-Agent"] = (
        "NJIT-Gameday-Discord-Bot/1.0 (fan Discord notifications; once a week)")
    rosters, first = {}, True
    for key, cfg in SPORTS.items():
        for path in cfg["paths"]:
            path = path.replace("/schedule", "/roster")
            if not first:
                time.sleep(delay_seconds)
            first = False
            try:
                r = session.get(SITE + path, timeout=30)
                r.raise_for_status()
                players = extract_roster(r.text)
                rosters.setdefault(key, []).extend(players)
                print(f"  {key:22s} {path}: {len(players)} players")
            except Exception as e:
                print(f"  {key:22s} {path}: FAILED ({e})")
    return rosters
