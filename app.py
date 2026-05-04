import os
from flask import Flask, request
import telegram
import google.generativeai as genai

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# ✅ Use a current working model
model = genai.GenerativeModel("gemini-1.5-flash")

# Telegram bot
bot = telegram.Bot(token=BOT_TOKEN)

# Flask app
app = Flask(__name__)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = telegram.Update.de_json(data, bot)

        if update.message and update.message.text:
            user_text = update.message.text

            try:
                # 🔥 Gemini request
                response = model.generate_content(
                    user_text,
                    generation_config={
                        "temperature": 0.7,
                        "max_output_tokens": 300
                    }
                )

                # ✅ Safe extraction
                reply = response.text if hasattr(response, "text") else "No response from AI."

            except Exception as e:
                print("Gemini ERROR:", e)
                reply = "AI is currently unavailable. Try again later."

            # Send reply to user
            bot.send_message(
                chat_id=update.message.chat.id,
                text=reply
            )

    except Exception as e:
        print("Webhook ERROR:", e)

    return "ok"


@app.route("/")
def home():
    return "Bot running!"


# Run server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
