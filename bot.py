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

# 1. Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# 2. Setup
API_TOKEN = "8409943297:AAEGWcOV1vQFKJMxIM0irVjoXHpY5RibPHk"
app = Flask(__name__)

@app.route('/')
def home():
    return "Global Betting Tips Bot is Live!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

# 3. Fixed Forebet Scraper
def fetch_forebet():
    try:
        url = "https://www.forebet.com/en/football-tips-and-predictions-for-today"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        tips = "📈 **Forebet: የዛሬ ትንበያዎች**\n\n"
        rows = soup.select('.tr_0, .tr_1, .schema_row')
        count = 0
        
        for row in rows:
            if count >= 15:
                break
            try:
                home_elem = row.select_one('.homeTeam span, .homeTeam')
                away_elem = row.select_one('.awayTeam span, .awayTeam')
                pred_elem = row.select_one('.forebet_pred span, .predict-score, .forebet_pred')
                
                if home_elem and away_elem:
                    home = home_elem.text.strip()
                    away = away_elem.text.strip()
                    pred = pred_elem.text.strip() if pred_elem else "1X2"
                    
                    if home and away:
                        tips += f"• **{home}** vs **{away}** ➡️ `{pred}`\n"
                        count += 1
            except Exception:
                continue
                
        return tips if count > 0 else "Forebet: ለዛሬ አዲስ መረጃ ማግኘት አልተቻለም።"
    except Exception as e:
        logging.error(f"Forebet error: {e}")
        return "⚠️ Forebet መረጃ ማምጣት አልተቻለም።"

# 4. Fixed Predicd Scraper
def fetch_predicd():
    try:
        url = "https://www.predicd.com/en/football/"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        tips = "🎯 **Predicd: የዛሬ ትንበያዎች**\n\n"
        matches = soup.select('.match-item, .match-row, tr[class*="match"]')
        count = 0
        
        for match in matches:
            if count >= 15:
                break
            try:
                home_elem = match.select_one('.team-home, .home-team-name, td.home')
                away_elem = match.select_one('.team-away, .away-team-name, td.away')
                pred_elem = match.select_one('.prediction, .pred-val, td.prediction-box')
                
                if home_elem and away_elem:
                    home = home_elem.text.strip()
                    away = away_elem.text.strip()
                    pred = pred_elem.text.strip() if pred_elem else "N/A"
                    
                    if home and away and not home.endswith('%'):
                        tips += f"• **{home}** vs **{away}** ➡️ `{pred}`\n"
                        count += 1
            except Exception:
                continue
                
        return tips if count > 0 else "Predicd: ለዛሬ መረጃ አልተገኘም።"
    except Exception as e:
        logging.error(f"Predicd error: {e}")
        return "⚠️ Predicd መረጃ ማምጣት አልተቻለም።"

# 5. Handlers & Keyboard
def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⚽ የዛሬ ሙሉ ትንበያዎችን አቅርብ")]],
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def start(message: types.Message):
    msg = f"ሰላም {message.from_user.first_name}!\n\nቦቱ ዝግጁ ነው። የዛሬዎቹን ትንበያዎች ለማግኘት ከታች ያለውን በተን ይጫኑ።"
    await message.reply(msg, reply_markup=main_keyboard())

@dp.message(F.text == "⚽ የዛሬ ሙሉ ትንበያዎችን አቅርብ")
async def send_tips(message: types.Message):
    await message.answer("🔄 ትኩስ መረጃዎችን ከ Forebet እና Predicd እያመጣሁ ነው... ጥቂት ይጠብቁ።")
    
    forebet_res = fetch_forebet()
    predicd_res = fetch_predicd()
    
    await message.answer(forebet_res, parse_mode="Markdown")
    await message.answer(predicd_res, parse_mode="Markdown", reply_markup=main_keyboard())

# 6. Run Server
async def main():
    Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
