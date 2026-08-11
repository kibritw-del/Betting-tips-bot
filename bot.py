import os
import logging
import asyncio
import requests
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# 1. Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

API_TOKEN = "8409943297:AAEGWcOV1vQFKJMxIM0irVjoXHpY5RibPHk"
FOOTBALL_DATA_API_KEY = "420f2371822d4ffaac96b16ddbec23a6"

app = Flask(__name__)

@app.route('/')
def home():
    return "Real Match Predictions Bot is Running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

PREDICTION_OPTIONS = [
    "Home Win (1)",
    "Away Win (2)",
    "Both Teams to Score (GG)",
    "Over 2.5 Goals",
    "Under 2.5 Goals",
    "Double Chance (1X)",
    "Double Chance (X2)",
    "Over 1.5 Goals"
]

def fetch_today_real_matches():
    try:
        url = "https://api.football-data.org/v4/matches"
        headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}
        
        res = requests.get(url, headers=headers, timeout=10)
        
        if res.status_code != 200:
            return "⚠️ መረጃዎችን ማምጣት አልተቻለም። እባክዎ ጥቂት ቆይተው ድጋሚ ይሞክሩ።"

        matches = res.json().get('matches', [])
        if not matches:
            return "⚽ ለዛሬ የተመዘገቡ ዋና ዋና ጨዋታዎች የሉም ወይም የዛሬዎቹ ጨዋታዎች አልቀዋል።"

        tips = "⚽ **የዛሬ እውነተኛ ጨዋታዎች እና ትንበያዎች**\n\n"
        count = 0

        for match in matches:
            if count >= 12:
                break
            comp_name = match.get('competition', {}).get('name', 'Football Match')
            home_team = match.get('homeTeam', {}).get('name')
            away_team = match.get('awayTeam', {}).get('name')

            if home_team and away_team:
                pred_idx = (hash(home_team + away_team) & 0x7FFFFFFF) % len(PREDICTION_OPTIONS)
                pred = PREDICTION_OPTIONS[pred_idx]

                tips += f"🏆 **{comp_name}**\n"
                tips += f"• **{home_team}** vs **{away_team}**\n"
                tips += f"  🎯 ትንበያ: `{pred}`\n\n"
                count += 1

        return tips if count > 0 else "⚽ ለዛሬ የተመዘገቡ ዋና ዋና ጨዋታዎች የሉም።"

    except Exception as e:
        logging.error(f"Error fetching matches: {e}")
        return "⚠️ መረጃ በማምጣት ላይ ስህተት አጋጥሟል።"

def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⚽ የዛሬ ሙሉ ትንበያዎችን አቅርብ")]],
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def start(message: types.Message):
    msg = f"ሰላም {message.from_user.first_name}!\n\nቦቱ ዝግጁ ነው። የዛሬዎቹን ትክክለኛ ጨዋታዎች ለማግኘት ከታች ያለውን በተን ይጫኑ።"
    await message.reply(msg, reply_markup=main_keyboard())

@dp.message(F.text == "⚽ የዛሬ ሙሉ ትንበያዎችን አቅርብ")
async def send_tips(message: types.Message):
    await message.answer("🔄 የዛሬዎቹን ጨዋታዎች ቀጥታ ከመረጃ ቋት እያመጣሁ ነው...")
    res_text = fetch_today_real_matches()
    await message.answer(res_text, parse_mode="Markdown", reply_markup=main_keyboard())

async def main():
    Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
