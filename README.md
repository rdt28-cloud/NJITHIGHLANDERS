# NJIT Gameday Bot 🔴⚪

Automatic game-day alerts for the **NJIT Athletics Updates** Discord. It reads every
NJIT Highlanders schedule from njithighlanders.com each morning and posts to each
sport's own channel:

| | Morning of game day (9 AM ET) | Before the game |
|---|---|---|
| **Away / neutral** | "Game day!" with time, place and stream | **15 min before:** "We're live on ESPN+ (link)" |
| **Home** | "We're hosting today!" (+ promos like Senior Night) | **45 min before:** "Pull up and fill the stands!" |

* Games with a **TBA/TBD** time get the morning alert only.
* Every alert type has **8 different formats** (plain posts, headlines, embeds, lists,
  countdown cards…) and the bot never reuses a recent format for the same sport.
* It never pings @everyone.
* #📅-athletic-events is **not** used by the bot. Keep it for pep rallies and big inter-sport events.

---

## One-time setup (about 15 minutes)

### 1. Create a webhook in each sport channel (Discord)

For **each** sport channel (⚾-mens-baseball, 🏀-mens-basketball, …):

1. Hover the channel → ⚙️ **Edit Channel** → **Integrations** → **Webhooks** → **New Webhook**.
2. Name it **NJIT Gameday**. Optionally upload the NJIT logo as its picture.
3. Click **Copy Webhook URL** and paste it into the template below.

> Webhook URLs work like passwords: anyone with one can post in that channel.
> Only paste them into GitHub Secrets (step 3), never into a file or chat.

Fill in this template (delete lines for channels you don't have):

```json
{
  "mens-baseball":        "https://discord.com/api/webhooks/...",
  "mens-basketball":      "https://discord.com/api/webhooks/...",
  "mens-soccer":          "https://discord.com/api/webhooks/...",
  "mens-cross-country":   "https://discord.com/api/webhooks/...",
  "mens-lacrosse":        "https://discord.com/api/webhooks/...",
  "mens-swimming-diving": "https://discord.com/api/webhooks/...",
  "mens-track-field":     "https://discord.com/api/webhooks/...",
  "mens-tennis":          "https://discord.com/api/webhooks/...",
  "mens-volleyball":      "https://discord.com/api/webhooks/...",
  "womens-basketball":    "https://discord.com/api/webhooks/...",
  "womens-cross-country": "https://discord.com/api/webhooks/...",
  "womens-soccer":        "https://discord.com/api/webhooks/...",
  "womens-tennis":        "https://discord.com/api/webhooks/...",
  "womens-track-field":   "https://discord.com/api/webhooks/...",
  "womens-volleyball":    "https://discord.com/api/webhooks/...",
  "fencing":              "https://discord.com/api/webhooks/..."
}
```

(`bowling` and `ice-hockey` are also supported if you bring those channels back.)

### 2. Put the code on GitHub

1. On github.com click **New repository**, name it `njit-gameday-bot`, and choose **Public**.
   It must be public: the bot checks for alerts every 5 minutes, which is free and
   unlimited on public repos but would use up a private repo's free minutes in days.
   Your webhook URLs stay secret either way (step 3).
2. Click **uploading an existing file**, then drag in **everything inside** the
   `njit-gameday-bot` folder, including the `.github` folder. Click **Commit changes**.

   *Tip: on a Mac, press Cmd + Shift + . in Finder to show the hidden `.github` folder.*
   If GitHub skips that folder, use **Add file → Create new file**, type
   `.github/workflows/alerts.yml` as the name, paste that file's contents, and repeat
   for `refresh.yml` and `test.yml`.

### 3. Add your webhooks as a secret

Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

* **Name:** `DISCORD_WEBHOOKS`
* **Secret:** paste the whole filled-in JSON from step 1

### 4. Turn it on

1. Repo → **Settings** → **Actions** → **General** → under *Workflow permissions*,
   pick **Read and write permissions** → **Save**. This lets the bot save its schedule and log.
2. Go to the **Actions** tab. If asked, click **I understand my workflows, go ahead and enable them**.
3. Run **Test Discord connection** (→ *Run workflow*). Every channel should get a
   "bot is connected" message.
4. Run **Refresh schedules** once to pull the latest games (it takes about 10 minutes
   because it waits 30 seconds between pages, as njithighlanders.com asks).

That's it. From now on:

* **Refresh schedules** runs every morning around 6 AM ET and picks up new games and time changes.
* **Game-day alerts** runs every 5 minutes and posts whatever is due.

---

## Good to know

* **Timing:** GitHub sometimes starts scheduled jobs a few minutes late. The bot
  handles that: if it's late, the message says the real time left ("live in 7 minutes"),
  and it never double-posts.
* **Stream link:** the bot uses the TV/stream logo or link NJIT lists for each game
  (usually ESPN+). If NJIT hasn't listed one, it links that sport's schedule page instead.
* **Season breaks:** GitHub pauses scheduled workflows in repos with no activity for
  60 days. If you get an email saying a workflow was disabled, open the Actions tab and
  click **Enable workflow**.
* **See what's coming:** `data/preview.md` lists every alert for the next two weeks
  with its message. To regenerate it locally: `python -m bot preview 14`.
* **Change the wording:** edit `bot/messages.py`. Each alert type is a list of
  templates, and you can add as many as you like.
* **Change timings:** `MORNING_HOUR`, `AWAY_LEAD_MIN` and `HOME_LEAD_MIN` at the top of `bot/alerts.py`.

## Files

```
bot/sports.py      sports, channel keys, emojis, schedule pages
bot/schedule.py    reads njithighlanders.com schedule pages → data/games.json
bot/messages.py    all the message templates + format rotation
bot/alerts.py      decides what's due and posts to Discord
data/games.json    the loaded schedule (updated daily by the bot)
data/state.json    which alerts were already sent (updated by the bot)
.github/workflows  refresh (daily), alerts (every 5 min), test (manual)
```
