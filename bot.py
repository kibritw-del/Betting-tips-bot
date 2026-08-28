import os
import math
import time
import logging
import asyncio
from html import escape

import requests
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ============================================================
# 1. Setup
# ============================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

API_TOKEN = os.environ.get("BOT_TOKEN")
FOOTBALL_DATA_API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY")

if not API_TOKEN or not FOOTBALL_DATA_API_KEY:
    raise RuntimeError(
        "Missing BOT_TOKEN or FOOTBALL_DATA_API_KEY environment variables. "
        "Set them in your hosting dashboard before starting the bot."
    )

app = Flask(__name__)


@app.route('/')
def home():
    return "Real Match Predictions Bot is Running!"


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)


bot = Bot(token=API_TOKEN)
dp = Dispatcher()

FOOTBALL_API_BASE = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}

_standings_cache = {}
CACHE_TTL_SECONDS = 6 * 60 * 60


# ============================================================
# 2. Poisson prediction model
# ============================================================
def poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        lam = 0.01
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def compute_markets(lambda_home: float, lambda_away: float, max_goals: int = 6) -> dict:
    home_win = draw = away_win = over25 = btts_yes = 0.0
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = poisson_pmf(h, lambda_home) * poisson_pmf(a, lambda_away)
            if h > a:
                home_win += p
            elif h == a:
                draw += p
            else:
                away_win += p
            if h + a > 2.5:
                over25 += p
            if h > 0 and a > 0:
                btts_yes += p

    return {
        "Home Win (1)": home_win,
        "Draw (X)": draw,
        "Away Win (2)": away_win,
        "Double Chance (1X)": home_win + draw,
        "Double Chance (X2)": draw + away_win,
        "Over 2.5 Goals": over25,
        "Under 2.5 Goals": 1 - over25,
        "Both Teams to Score (GG)": btts_yes,
    }


def get_competition_standings(competition_id: int):
    cached = _standings_cache.get(competition_id)
    if cached and (time.time() - cached["ts"]) < CACHE_TTL_SECONDS:
        return cached["data"]

    url = f"{FOOTBALL_API_BASE}/competitions/{competition_id}/standings"
    res = requests.get(url, headers=HEADERS, timeout=10)
    if res.status_code != 200:
        return None

    payload = res.json()
    table = []
    for group in payload.get("standings", []):
        if group.get("type") != "TOTAL":
            continue
        table.extend(group.get("table", []))

    if not table:
        return None

    team_stats = {}
    total_goals = 0
    total_games = 0
    for row in table:
        played = row.get("playedGames", 0)
        gf = row.get("goalsFor", 0)
        ga = row.get("goalsAgainst", 0)
        team_id = row["team"]["id"]
        team_stats[team_id] = {"played": played, "gf": gf, "ga": ga}
        total_goals += gf
        total_games += played

    if total_games == 0:
        return None

    league_avg_goals_per_game = total_goals / total_games

    data = {"teams": team_stats, "league_avg": league_avg_goals_per_game}
    _standings_cache[competition_id] = {"data": data, "ts": time.time()}
    return data


def predict_match(competition_id: int, home_id: int, away_id: int, min_games: int = 3):
    standings = get_competition_standings(competition_id)
    if not standings:
        return None

    home_stats = standings["teams"].get(home_id)
    away_stats = standings["teams"].get(away_id)
    league_avg = standings["league_avg"]

    if not home_stats or not away_stats:
        return None
    if home_stats["played"] < min_games or away_stats["played"] < min_games:
        return None

    home_attack = (home_stats["gf"] / home_stats["played"]) / league_avg
    home_defense = (home_stats["ga"] / home_stats["played"]) / league_avg
    away_attack = (away_stats["gf"] / away_stats["played"]) / league_avg
    away_defense = (away_stats["ga"] / away_stats["played"]) / league_avg

    HOME_ADV = 1.15

    lambda_home = home_attack * away_defense * league_avg * HOME_ADV
    lambda_away = away_attack * home_defense * league_avg

    markets = compute_markets(lambda_home, lambda_away)
    top_market = max(markets, key=markets.get)
    return markets, top_market, markets[top_market]


# ============================================================
# 3. Fetch today's matches and build the message
# ============================================================
def fetch_today_real_matches() -> str:
    try:
        url = f"{FOOTBALL_API_BASE}/matches"
        res = requests.get(url, headers=HEADERS, timeout=10)

        if res.status_code == 429:
            return "⚠️ በጣም ብዙ ጥያቄዎች ተልከዋል። እባክዎ ከጥቂት ደቂቃዎች በኋላ ይሞክሩ።"
        if res.status_code != 200:
            return "⚠️ መረጃዎችን ማምጣት አልተቻለም። እባክዎ ጥቂት ቆይተው ድጋሚ ይሞክሩ።"

        matches = res.json().get('matches', [])
        if not matches:
            return "⚽ ለዛሬ የተመዘገቡ ዋና ዋና ጨዋታዎች የሉም ወይም የዛሬዎቹ ጨዋታዎች አልቀዋል።"

        header = (
            "⚽ <b>የዛሬ ጨዋታዎች እና ስታትስቲካዊ ትንበያዎች</b>\n"
            "<i>ትንበያዎቹ በPoisson ስታትስቲክስ ሞዴል (የቡድን አማካይ ውጤቶች መሰረት) የተሰሉ ግምቶች ናቸው፤ "
            "ዋስትና አይደሉም። እባክዎ በኃላፊነት ይወራረዱ።</i>\n\n"
        )

        body_parts = []
        count = 0

        for match in matches:
            if count >= 12:
                break

            competition = match.get('competition', {})
            comp_id = competition.get('id')
            comp_name = competition.get('name', 'Football Match')
            home = match.get('homeTeam', {})
            away = match.get('awayTeam', {})
            home_name = home.get('name')
            away_name = away.get('name')
            home_id = home.get('id')
            away_id = away.get('id')

            if not (home_name and away_name and comp_id and home_id and away_id):
                continue

            result = predict_match(comp_id, home_id, away_id)

            block = f"🏆 <b>{escape(comp_name)}</b>\n"
            block += f"• <b>{escape(home_name)}</b> vs <b>{escape(away_name)}</b>\n"

            if result is None:
                block += "  ℹ️ በቂ የስታትስቲክስ መረጃ የለም (ወቅቱ ገና ጀምሯል ወይም ውድድሩ አይደገፍም)።\n\n"
            else:
                markets, top_market, top_prob = result
                second = sorted(markets.items(), key=lambda kv: kv[1], reverse=True)[1]
                block += f"  🎯 ትንበያ: <b>{escape(top_market)}</b> ({top_prob*100:.0f}% እድል)\n"
                block += f"  📈 ሁለተኛ አማራጭ: {escape(second[0])} ({second[1]*100:.0f}%)\n\n"

            body_parts.append(block)
            count += 1

        if count == 0:
            return "⚽ ለዛሬ የተመዘገቡ ዋና ዋና ጨዋታዎች የሉም።"

        return header + "".join(body_parts)

    except requests.exceptions.RequestException as e:
        log.error(f"Network error fetching matches: {e}")
        return "⚠️ ከመረጃ ቋቱ ጋር መገናኘት አልተቻለም። እባክዎ ጥቂት ቆይተው ይሞክሩ።"
    except Exception as e:
        log.error(f"Error fetching matches: {e}")
        return "⚠️ መረጃ በማምጣት ላይ ስህተት አጋጥሟል።"


# ============================================================
# 4. Telegram handlers
# ============================================================
def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⚽ የዛሬ ሙሉ ትንበያዎችን አቅርብ")]],
        resize_keyboard=True
    )


@dp.message(Command("start"))
async def start(message: types.Message):
    msg = (
        f"ሰላም {escape(message.from_user.first_name)}!\n\n"
        "ቦቱ ዝግጁ ነው። የዛሬዎቹን ጨዋታዎች ከስታትስቲክስ ሞዴል ትንበያ ጋር ለማግኘት ከታች ያለውን በተን ይጫኑ።"
    )
    await message.reply(msg, reply_markup=main_keyboard())


@dp.message(F.text == "⚽ የዛሬ ሙሉ ትንበያዎችን አቅርብ")
async def send_tips(message: types.Message):
    await message.answer("🔄 የዛሬዎቹን ጨዋታዎች እና ስታትስቲክስ እያሰላሁ ነው...")
    res_text = fetch_today_real_matches()
    await message.answer(res_text, parse_mode="HTML", reply_markup=main_keyboard())


async def main():
    Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
