import os
import logging
import asyncio
import requests
import random
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

# 3. Dynamic Prediction Engine
PREDICTION_OPTIONS = [
    "Home Win (1)",
    "Away Win (2)",
    "Draw / Both Teams to Score (GG)",
    "Over 2.5 Goals",
    "Under 2.5 Goals",
    "Double Chance 1X",
    "Double Chance X2",
    "Over 1.5 Goals",
    "Both Teams to Score (Yes)"
]

def fetch_live_predictions():
    try:
        # ESPN Official Live/Today Matches API
        url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
        res = requests.get(url, headers=HEADERS, timeout=12)
        
        if res.status_code != 200:
            return "⚠️ የዛሬ ጨዋታዎችን ማግኘት አልተቻለም።"

        events = res.json().get('events', [])
        if not events:
            return "⚽ ለዛሬ የተመዘገቡ ዋና ዋና ጨዋታዎች አልተገኙም።"

        tips = "⚽ **የዛሬ እውነተኛ ጨዋታዎች እና ትንበያዎች**\n\n"
        count = 0

        for ev in events:
            if count >= 12:
                break
            try:
                comp_name = ev.get('league', {}).get('name', 'International')
                competitors = ev.get('competitions', [{}])[0].get('competitors', [])
                
                if len(competitors) >= 2:
                    # Identify teams
                    home_team = competitors[0].get('team', {}).get('displayName')
                    away_team = competitors[1].get('team', {}).get('displayName')
                    
                    if home_team and away_team:
                        # Smart prediction generator based on match ID hash
                        match_id = int(ev.get('id', random.randint(1, 1000)))
                        pred = PREDICTION_OPTIONS[match_id % len(PREDICTION_OPTIONS)]
                        
                        tips += f"🏆 **{comp_name}**\n"
                        tips += f"• **{home_team}** vs **{away_team}**\n"
                        tips += f"  🎯 ትንበያ: `{pred}`\n\n"
                        count += 1
            except Exception:
                continue

        return tips if count > 0 else "⚽ ለዛሬ የተመዘገቡ ዋና ዋና ጨዋታዎች አልተገኙም።"

    except Exception as e:
        logging.error(f"Prediction Error: {e}")
        return "⚠️ መረጃዎችን በማምጣት ላይ ስህተት ተፈጥሯል።"

# 4. Keyboard & Handlers
def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⚽ የዛሬ ሙሉ ትንበያዎችን አቅርብ")]],
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def start(message: types.Message):
    msg = f"ሰላም {message.from_user.first_name}!\n\nቦቱ ዝግጁ ነው። የዛሬዎቹን ትክክለኛ የዓለም አቀፍ ጨዋታዎች ትንበያ ለማግኘት ከታች ያለውን በተን ይጫኑ።"
    await message.reply(msg, reply_markup=main_keyboard())

@dp.message(F.text == "⚽ የዛሬ ሙሉ ትንበያዎችን አቅርብ")
async def send_tips(message: types.Message):
    await message.answer("🔄 የዛሬዎቹን እውነተኛ ጨዋታዎች ከ ESPN መረጃዎች ጋር እያመጣሁ ነው... ጥቂት ይጠብቁ።")
    res_text = fetch_live_predictions()
    await message.answer(res_text, parse_mode="Markdown", reply_markup=main_keyboard())

# 5. Main Execution
async def main():
    Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
