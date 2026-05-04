import os
from flask import Flask, request
import telegram
import google.generativeai as genai

BOT_TOKEN = os.getenv("8705990042:AAHEGU2Fb1hFaOFD5Lihr8gAwpcGR8NgUUY")
GEMINI_API_KEY = os.getenv("AIzaSyBUk8vPeU24c1Hgr2_CoGYswseoGR36jAo")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

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

        bot.send_message(
            chat_id=update.message.chat.id,
            text=reply
        )

    return "ok"

@app.route("/")
def home():
    return "Bot running!"

