from flask import Flask, request
import requests
import os

app = Flask(__name__)

# Load bot token from environment
BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


# ✅ Webhook route (must match your Telegram webhook)
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if not data:
        return "No data", 400

    print("Incoming update:", data)

    message = data.get("message")
    if message:
        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        reply = f"You said: {text}"
        send_message(chat_id, reply)

    return "OK", 200


# ✅ Send message function
def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)


# ✅ Health check route (Render uses this)
@app.route("/", methods=["GET"])
def home():
    return "Bot is running", 200


# ✅ IMPORTANT: Use Render's dynamic port
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
