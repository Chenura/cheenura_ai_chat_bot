import os
from flask import Flask, request
import telegram
import google.generativeai as genai

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Safety check (prevents silent misconfig issues)
if not BOT_TOKEN:
    raise Exception("BOT_TOKEN is missing")
if not GEMINI_API_KEY:
    raise Exception("GEMINI_API_KEY is missing")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Use modern model
model = genai.GenerativeModel("gemini-1.5-flash")

# Telegram bot
bot = telegram.Bot(token=BOT_TOKEN)

# Flask app
app = Flask(__name__)


def get_gemini_reply(user_text):
    try:
        response = model.generate_content(user_text)

        print("\n===== GEMINI RAW RESPONSE =====")
        print(response)
        print("================================\n")

        # Primary response method
        if hasattr(response, "text") and response.text:
            return response.text

        # Fallback method
        try:
            return response.candidates[0].content.parts[0].text
        except Exception:
            return "⚠️ Gemini returned empty response (no text found)."

    except Exception as e:
        # 🔥 IMPORTANT: show real error in logs
        print("\n===== GEMINI ERROR =====")
        print(str(e))
        print("========================\n")

        # 🔥 Also return real error to Telegram for debugging
        return f"❌ Gemini Error:\n{str(e)}"


@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = telegram.Update.de_json(data, bot)

        if update.message and update.message.text:
            user_text = update.message.text

            print(f"\n📩 USER: {user_text}")

            reply = get_gemini_reply(user_text)

            print(f"🤖 BOT: {reply}\n")

            bot.send_message(
                chat_id=update.message.chat.id,
                text=reply
            )

    except Exception as e:
        print("\n===== WEBHOOK ERROR =====")
        print(str(e))
        print("========================\n")

    return "ok"


@app.route("/")
def home():
    return "Bot is running!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
