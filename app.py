import os
from flask import Flask, request
import telegram
import google.generativeai as genai

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Use a modern model
model = genai.GenerativeModel("gemini-1.5-flash")

# Telegram bot
bot = telegram.Bot(token=BOT_TOKEN)

# Flask app
app = Flask(__name__)


def get_gemini_reply(user_text):
    try:
        response = model.generate_content(user_text)

        print("\n=== GEMINI RAW RESPONSE ===")
        print(response)
        print("===========================\n")

        # ✅ Method 1: direct text
        if hasattr(response, "text") and response.text:
            return response.text

        # ✅ Method 2: fallback parsing
        try:
            return response.candidates[0].content.parts[0].text
        except Exception:
            return "⚠️ Gemini returned an empty response."

    except Exception as e:
        print("\n=== GEMINI ERROR ===")
        print(e)
        print("====================\n")

        return "❌ AI is currently unavailable. Please try again later."


@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = telegram.Update.de_json(data, bot)

        if update.message and update.message.text:
            user_text = update.message.text

            print(f"\n📩 User message: {user_text}")

            reply = get_gemini_reply(user_text)

            print(f"🤖 Bot reply: {reply}\n")

            bot.send_message(
                chat_id=update.message.chat.id,
                text=reply
            )

    except Exception as e:
        print("\n=== WEBHOOK ERROR ===")
        print(e)
        print("====================\n")

    return "ok"


@app.route("/")
def home():
    return "Bot running!"


# Run server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
