# Aquality Heat-Loss Telegram Bot

A Telegram-bot copy of **aqualityheatloss.netlify.app** — the heat-loss
(теплопотери) calculator for **Aquality | WaterPro** (Fergana, Uzbekistan).

It reproduces the website's calculation engine **exactly** (KMK 2.01.04-18 /
KMK 2.01.01-94, parameter B): the per-enclosure formula `Q = (ΔT/R)·S·n·(1+Σβ)·k_corner`,
the zonal ground-floor method, and infiltration `0.28·1.005·V·ρ(t)·ΔT·ACH`.
The engine self-test matches the site's pinned reference of **4198.1 W** for the
canonical 4×5×3 room.

Owner / admin: **@ibrokh1movv7**.

## Features

- 🌐 Trilingual UI — RU / UZ / EN (per-user, persisted)
- 🏙 13 Uzbek cities with design winter temperatures (parameter B)
- 🧱 All **324** construction presets from the site (walls / windows / doors / floor / ceiling), browsable by group with pagination
- 🏢 Multi-floor, multi-room objects; ground-floor & top-floor handling, attic type, airtightness, heating regime, λ moisture mode A/B, door β surcharges, corner & orientation surcharges
- 📊 Results: total kW, boiler kW (+25%), recommended boiler model, loss breakdown with bars, radiator sections + model, pipe Ø, monthly fuel-cost comparison (gas/coal/electric, UZ tariffs)
- 🏡 One-tap demo (example house)
- ✍️ Lead capture → forwarded to the owner + stored in SQLite
- 👑 Owner panel: funnel stats, recent leads, broadcast

## 1. Create the bot

In Telegram open **@BotFather** → `/newbot` → choose a name and username →
copy the token (looks like `123456789:ABCdef...`).

## 2. Run locally

```bash
cd bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export BOT_TOKEN='123456789:ABCdef...'
export OWNER_USERNAME='ibrokh1movv7'
python -m app.bot
```

Open your bot in Telegram and press **Start**.

To receive leads as the owner: start the bot once, send **/myid**, then set
`OWNER_ID=<that number>` in the environment and restart. (Telegram bots can only
message users who have started them, so the numeric id is required for push.)

## 3. Deploy 24/7

### Railway (Docker, free tier)
1. Push this `bot/` folder to a GitHub repo.
2. Railway → *New Project* → *Deploy from repo*. It auto-detects `Dockerfile`.
3. Add variables `BOT_TOKEN`, `OWNER_USERNAME`, `OWNER_ID`.
4. (Optional) Add a volume mounted at `/data` and set `DB_PATH=/data/aquality_bot.db`
   so leads survive redeploys.

### Render (Background Worker)
- New → *Background Worker* → Docker. Set the same env vars. Start command:
  `python -m app.bot`. Add a disk at `/data` + `DB_PATH=/data/aquality_bot.db`.

### Any VPS (Docker)
```bash
docker build -t aquality-bot .
docker run -d --restart unless-stopped \
  -e BOT_TOKEN=... -e OWNER_USERNAME=ibrokh1movv7 -e OWNER_ID=... \
  -e DB_PATH=/data/bot.db -v aq_data:/data --name aquality-bot aquality-bot
```

### Bare VPS (systemd, no Docker)
```bash
pip install -r requirements.txt
# /etc/systemd/system/aquality-bot.service → ExecStart=python -m app.bot (WorkingDirectory=/path/to/bot)
```

## Tests

```bash
cd bot && python -m pytest tests/      # or: python tests/run.py
python -m app.engine                   # prints the pinned self-test
```

## Layout

```
bot/
├── app/
│   ├── bot.py        # entry: dispatcher + polling
│   ├── config.py     # env vars, contact
│   ├── engine.py     # ported heat-loss engine (+ self_test)
│   ├── presets.py    # AUTO-GENERATED 324 presets / cities / room types
│   ├── i18n.py       # RU/UZ/EN strings
│   ├── keyboards.py  # inline keyboards
│   ├── states.py     # FSM states
│   ├── storage.py    # SQLite: leads, funnel, languages
│   └── handlers/     # menu, wizard, results, admin
├── scripts/extract_presets.py   # regenerates presets.py from ../index.html
├── tests/test_engine.py
├── Dockerfile · Procfile · railway.json · requirements.txt · .env.example
```

To refresh the material library after the website changes:
`python scripts/extract_presets.py`.
