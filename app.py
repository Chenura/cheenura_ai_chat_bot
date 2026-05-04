import os
from flask import Flask, request
import telegram
from google import genai

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

bot = telegram.Bot(token=BOT_TOKEN)
app = Flask(__name__)


def ask_gemini(text):
    try:
        response = client.models.generate_content(
            model="gemini-pro",
            contents=text
        )

        return response.text

    except Exception as e:
        print("GEMINI ERROR:", e)
        return f"❌ Gemini Error:\n{str(e)}"


@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = telegram.Update.de_json(data, bot)

    if update.message and update.message.text:
        reply = ask_gemini(update.message.text)

        bot.send_message(
            chat_id=update.message.chat.id,
            text=reply
        )

    return "ok"


@app.route("/")
def home():
    return "Bot running!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
