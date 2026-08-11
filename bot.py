import os
import logging
import asyncio
import requests
from bs4 import BeautifulSoup
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
    return "Today Matches Prediction Bot is Live!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

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

def fetch_today_matches():
    try:
        # Scrape ESPN directly for today's real fixtures
        url = "https://www.espn.com/soccer/fixtures"
        res = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        matches_found = []
        
        # Parse table contents
        tables = soup.select('.Table')
        for table in tables:
            caption = table.select_one('.Table__Title')
            comp_name = caption.text.strip() if caption else "Today Football Match"
            
            rows = table.select('tbody tr')
            for row in rows:
                teams = row.select('.Table__TD .AnchorLink span')
                if len(teams) >= 2:
                    home = teams[0].text.strip()
                    away = teams[1].text.strip()
                    if home and away and home != away:
                        matches_found.append((comp_name, home, away))
        
        # Fallback to ESPN API if web structure changes
        if not matches_found:
            api_url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
            api_res = requests.get(api_url, headers=HEADERS, timeout=10)
            if api_res.status_code == 200:
                events = api_res.json().get('events', [])
                for ev in events:
                    comp = ev.get('league', {}).get('name', 'Soccer')
                    comps = ev.get('competitions', [{}])[0].get('competitors', [])
                    if len(comps) >= 2:
                        h = comps[0].get('team', {}).get('displayName')
                        a = comps[1].get('team', {}).get('displayName')
                        if h and a:
                            matches_found.append((comp, h, a))

        if not matches_found:
            return "⚽ ለዛሬ የተመዘገቡ ዋና ዋና የዓለም አቀፍ ጨዋታዎች የሉም ወይም ጨዋታዎቹ አልቀዋል።"

        tips = "⚽ **የዛሬ እውነተኛ ጨዋታዎች እና ትንበያዎች**\n\n"
        count = 0

        for comp, home, away in matches_found[:12]:
            pred_idx = (hash(home + away) & 0x7FFFFFFF) % len(PREDICTION_OPTIONS)
            pred = PREDICTION_OPTIONS[pred_idx]
            
            tips += f"🏆 **{comp}**\n"
            tips += f"• **{home}** vs **{away}**\n"
            tips += f"  🎯 ትንበያ: `{pred}`\n\n"
            count += 1

        return tips

    except Exception as e:
        logging.error(f"Fetch Error: {e}")
        return "⚠️ መረጃዎችን በማምጣት ላይ ስህተት ተፈጥሯል።"

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
    await message.answer("🔄 የዛሬዎቹን እውነተኛ ጨዋታዎች ከ ESPN እያመጣሁ ነው... ጥቂት ይጠብቁ።")
    res_text = fetch_today_matches()
    await message.answer(res_text, parse_mode="Markdown", reply_markup=main_keyboard())

# 5. Main Execution
async def main():
    Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
