import os
import logging
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from flask import Flask
from threading import Thread

# 1. Logging Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# 2. Setup & Constants
API_TOKEN = "8409943297:AAEGWcOV1vQFKJMxIM0irVjoXHpY5RibPHk"
app = Flask(__name__)

@app.route('/')
def home():
    return "Global Betting Tips Bot is Fully Operational!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'no-cache'
}

# 3. Forebet Scraper
def fetch_forebet():
    try:
        url = "https://www.forebet.com/en/football-tips-and-predictions-for-today"
        res = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        tips = "📈 **Forebet: የዛሬ ትንበያዎች**\n\n"
        rows = soup.select('.predict, .tr_0, .tr_1, .schema_row, div[class*="tr_"]')
        count = 0
        
        for row in rows:
            if count >= 15:
                break
            try:
                home = row.select_one('.homeTeam, .home-team, span[itemprop="homeTeam"]')
                away = row.select_one('.awayTeam, .away-team, span[itemprop="awayTeam"]')
                pred = row.select_one('.pred_txt, .forebet_pred, .predict-score, .forebet_prediction')
                
                if home and away:
                    h_text = home.text.strip()
                    a_text = away.text.strip()
                    p_text = pred.text.strip() if pred else "N/A"
                    tips += f"• **{h_text}** vs **{a_text}** ➡️ `{p_text}`\n"
                    count += 1
            except:
                continue
                
        return tips if count > 0 else "Forebet: ለዛሬ አዲስ መረጃ ማግኘት አልተቻለም።"
    except Exception as e:
        logging.error(f"Forebet error: {e}")
        return "⚠️ Forebet መረጃ ማምጣት አልተቻለም።"

# 4. Predicd Scraper
def fetch_predicd():
    try:
        url = "https://www.predicd.com/en/football/"
        res = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        tips = "🎯 **Predicd: የዛሬ ትንበያዎች**\n\n"
        matches = soup.select('.match-row, .match-prediction-wrapper, .match-item, tr, div[class*="match"]')
        count = 0
        
        for match in matches:
            if count >= 15:
                break
            try:
                home = match.select_one('.home-team-name, .home-team, .team-home, [class*="home"]')
                away = match.select_one('.away-team-name, .away-team, .team-away, [class*="away"]')
                pred = match.select_one('.prediction-score, .prediction-box, .prediction, [class*="pred"]')
                
                if home and away:
                    h_text = home.text.strip()
                    a_text = away.text.strip()
                    p_text = pred.text.strip() if pred else "N/A"
                    tips += f"• **{h_text}** vs **{a_text}** ➡️ `{p_text}`\n"
                    count += 1
            except:
                continue
                
        return tips if count > 0 else "Predicd: ለዛሬ መረጃ አልተገኘም።"
    except Exception as e:
        logging.error(f"Predicd error: {e}")
        return "⚠️ Predicd መረጃ ማምጣት አልተቻለም።"

# 5. Handlers & Keyboard
def main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("⚽ የዛሬ ሙሉ ትንበያዎችን አቅርብ"))
    return kb

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    msg = f"ሰላም {message.from_user.first_name}!\n\nቦቱ ዝግጁ ነው። የዛሬዎቹን ትንበያዎች ለማግኘት ከታች ያለውን በተን ይጫኑ።"
    await message.reply(msg, reply_markup=main_keyboard())

@dp.message_handler(lambda m: m.text == "⚽ የዛሬ ሙሉ ትንበያዎችን አቅርብ")
async def send_tips(message: types.Message):
    await message.answer("🔄 ትኩስ መረጃዎችን ከ Forebet እና Predicd እያመጣሁ ነው... ጥቂት ይጠብቁ።")
    
    forebet_res = fetch_forebet()
    predicd_res = fetch_predicd()
    
    await message.answer(forebet_res, parse_mode="Markdown")
    await message.answer(predicd_res, parse_mode="Markdown", reply_markup=main_keyboard())

# 6. Run Server
if __name__ == '__main__':
    Thread(target=run_flask, daemon=True).start()
    executor.start_polling(dp, skip_updates=True)
