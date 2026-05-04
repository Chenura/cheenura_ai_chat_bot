import os
from flask import Flask, request
import telegram
import google.generativeai as genai

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro")

bot = telegram.Bot(token=BOT_TOKEN)
app = Flask(__name__)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = telegram.Update.de_json(data, bot)

    if update.message and update.message.text:
    user_text = update.message.text

        response = model.generate_content(user_text)
        reply = response.text

        bot.send_message(chat_id=update.message.chat.id, text=reply)

    return "ok"

@app.route("/")
def home():
    return "Bot running!"

