"""Which sports the bot follows, and how to talk about each one.

The `key` of each entry must match the key you use in the DISCORD_WEBHOOKS
secret (see README). A sport with no webhook is still tracked, just never posted.
`role_id` is that sport's "<Sport> Fans" Discord role; game-day alerts @mention it.
"""

ESPN_PLUS_URL = "https://www.espn.com/search/_/appearance/dark/o/watch/q/njit"
SITE = "https://njithighlanders.com"

SPORTS = {
    "mens-baseball": {
        "name": "Men's Baseball", "emoji": "⚾", "noun": "game", "role_id": "1561873891956105328",
        "start_word": "first pitch", "paths": ["/sports/baseball/schedule"],
    },
    "mens-basketball": {
        "name": "Men's Basketball", "emoji": "🏀", "noun": "game", "role_id": "1561874079961579600",
        "start_word": "tip-off", "paths": ["/sports/mens-basketball/schedule"],
    },
    "mens-soccer": {
        "name": "Men's Soccer", "emoji": "⚽", "noun": "match", "role_id": "1561874097594564669",
        "start_word": "kickoff", "paths": ["/sports/mens-soccer/schedule"],
    },
    "mens-cross-country": {
        "name": "Men's Cross Country", "emoji": "🏃", "noun": "meet", "role_id": "1561874115508576267",
        "start_word": "the gun", "paths": ["/sports/mens-cross-country/schedule"],
    },
    "mens-lacrosse": {
        "name": "Men's Lacrosse", "emoji": "🥍", "noun": "game", "role_id": "1561874155765370882",
        "start_word": "faceoff", "paths": ["/sports/mens-lacrosse/schedule"],
    },
    "mens-swimming-diving": {
        "name": "Men's Swimming & Diving", "emoji": "🏊", "noun": "meet", "role_id": "1561874173968515183",
        "start_word": "the first race", "paths": ["/sports/mens-swimming-and-diving/schedule"],
    },
    "mens-track-field": {
        "name": "Men's Track & Field", "emoji": "👟", "noun": "meet", "role_id": "1561874191655903282",
        "start_word": "the first event", "paths": ["/sports/mens-track-and-field/schedule"],
    },
    "mens-tennis": {
        "name": "Men's Tennis", "emoji": "🎾", "noun": "match", "role_id": "1561874209519439904",
        "start_word": "first serve", "paths": ["/sports/mens-tennis/schedule"],
    },
    "mens-volleyball": {
        "name": "Men's Volleyball", "emoji": "🏐", "noun": "match", "role_id": "1561874227395567657",
        "start_word": "first serve", "paths": ["/sports/mens-volleyball/schedule"],
    },
    "womens-basketball": {
        "name": "Women's Basketball", "emoji": "🏀", "noun": "game", "role_id": "1561874268336291881",
        "start_word": "tip-off", "paths": ["/sports/womens-basketball/schedule"],
    },
    "womens-cross-country": {
        "name": "Women's Cross Country", "emoji": "🏃", "noun": "meet", "role_id": "1561874286140981278",
        "start_word": "the gun", "paths": ["/sports/womens-cross-country/schedule"],
    },
    "womens-soccer": {
        "name": "Women's Soccer", "emoji": "⚽", "noun": "match", "role_id": "1561874304134553700",
        "start_word": "kickoff", "paths": ["/sports/womens-soccer/schedule"],
    },
    "womens-tennis": {
        "name": "Women's Tennis", "emoji": "🎾", "noun": "match", "role_id": "1561874321859936386",
        "start_word": "first serve", "paths": ["/sports/womens-tennis/schedule"],
    },
    "womens-track-field": {
        "name": "Women's Track & Field", "emoji": "👟", "noun": "meet", "role_id": "1561874362611540019",
        "start_word": "the first event", "paths": ["/sports/womens-track-and-field/schedule"],
    },
    "womens-volleyball": {
        "name": "Women's Volleyball", "emoji": "🏐", "noun": "match", "role_id": "1561874380198387844",
        "start_word": "first serve", "paths": ["/sports/womens-volleyball/schedule"],
    },
    "fencing": {
        "name": "Fencing", "emoji": "🤺", "noun": "meet", "role_id": "1561874398116319282",
        "start_word": "the first bout",
        "paths": ["/sports/mens-fencing/schedule", "/sports/womens-fencing/schedule"],
    },
    "bowling": {
        "name": "Bowling", "emoji": "🎳", "noun": "event",
        "start_word": "the first frame", "paths": ["/sports/womens-bowling/schedule"],
    },
    "ice-hockey": {
        "name": "Ice Hockey", "emoji": "🏒", "noun": "game",
        "start_word": "puck drop", "paths": ["/sports/mens-ice-hockey/schedule"],
    },
}
