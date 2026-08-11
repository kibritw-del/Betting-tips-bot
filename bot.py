import os
import logging
import asyncio
import requests
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# 1. Logging Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# 2. Setup
API_TOKEN = "8409943297:AAEGWcOV1vQFKJMxIM0irVjoXHpY5RibPHk"
app = Flask(__name__)

@app.route('/')
def home():
    return "Real Football Predictions Bot is Live!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

# 3. Dynamic Prediction Options
PREDICTION_OPTIONS = [
    "Home Win (1)",
    "Away Win (2)",
    "Both Teams to Score (GG)",
    "Over 2.5 Goals",
    "Under 2.5 Goals",
    "Double Chance (1X)",
    "Double Chance (X2)",
    "Over 1.5 Goals",
    "Home or Draw (1X)"
]

def fetch_live_predictions():
    matches_found = []
    
    # Primary Source: ESPN Football Scoreboard
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
        res = requests.get(url, headers=HEADERS, timeout=12)
        if res.status_code == 200:
            events = res.json().get('events', [])
            for ev in events:
                comp_name = ev.get('league', {}).get('name', 'International Football')
                competitors = ev.get('competitions', [{}])[0].get('competitors', [])
                if len(competitors) >= 2:
                    home = competitors[0].get('team', {}).get('displayName')
                    away = competitors[1].get('team', {}).get('displayName')
                    if home and away:
                        matches_found.append((comp_name, home, away))
    except Exception as e:
        logging.error(f"ESPN Fetch Error: {e}")

    # Fallback Source: OpenLigaDB API
    if len(matches_found) < 3:
        try:
            url_backup = "https://api.openligadb.de/getmatchdata/bl1"
            res_b = requests.get(url_backup, timeout=12)
            if res_b.status_code == 200:
                data = res_b.json()
                for m in data:
                    home = m.get('team1', {}).get('teamName')
                    away = m.get('team2', {}).get('teamName')
                    if home and away:
                        matches_found.append(("Bundesliga / European Football", home, away))
        except Exception as e:
            logging.error(f"Backup API Fetch Error: {e}")

    if not matches_found:
        return "⚠️ ለዛሬ የተመዘገቡ ጨዋታዎችን ማግኘት አልተቻለም። እባክዎ ጥቂት ቆይተው ድጋሚ ይሞክሩ።"

    tips = "⚽ **የዛሬ እውነተኛ ጨዋታዎች እና ትንበያዎች**\n\n"
    count = 0

    for comp, home, away in matches_found[:12]:
        # Generate predictable unique prediction per match
        pred_idx = (hash(home + away) & 0x7FFFFFFF) % len(PREDICTION_OPTIONS)
        pred = PREDICTION_OPTIONS[pred_idx]
        
        tips += f"🏆 **{comp}**\n"
        tips += f"• **{home}** vs **{away}**\n"
        tips += f"  🎯 ትንበያ: `{pred}`\n\n"
        count += 1

    return tips

# 4. Keyboard & Handlers
def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⚽ የዛሬ ሙሉ ትንበያዎችን አቅርብ")]],
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def start(message: types.Message):
    msg = f"ሰላም {message.from_user.first_name}!\n\nቦቱ ዝግጁ ነው። የዛሬዎቹን ትክክለኛ ጨዋታዎች እና ትንበያዎች ለማግኘት ከታች ያለውን በተን ይጫኑ።"
    await message.reply(msg, reply_markup=main_keyboard())

@dp.message(F.text == "⚽ የዛሬ ሙሉ ትንበያዎችን አቅርብ")
async def send_tips(message: types.Message):
    await message.answer("🔄 የዛሬዎቹን እውነተኛ ጨዋታዎች እያመጣሁ ነው... ጥቂት ይጠብቁ።")
    res_text = fetch_live_predictions()
    await message.answer(res_text, parse_mode="Markdown", reply_markup=main_keyboard())

# 5. Main Execution
async def main():
    Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
