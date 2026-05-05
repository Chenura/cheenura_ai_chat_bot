from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not set")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


# ✅ Webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if not data:
        return "No data", 400

    print("Incoming:", data)

    message = data.get("message")
    if message:
        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        if text.lower() == "/start":
            reply = "Hello! I'm your Gemini 2.5 AI assistant. Ask me anything."

        elif "hi" in text.lower() or "hello" in text.lower():
            reply = "Hi there! How can I help you?"

        else:
            reply = get_gemini_response(text)

        send_message(chat_id, reply)

    return "OK", 200


# ✅ Gemini 2.5 function (UPDATED)
def get_gemini_response(user_message):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "contents": [
            {
                "parts": [
                    {"text": user_message}
                ]
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)

        print("Gemini status:", response.status_code)
        print("Gemini response:", response.text)

        if response.status_code != 200:
            return "Error: Gemini API failed. Check logs."

        result = response.json()

        return result["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        print("Exception:", str(e))
        return "Error: Gemini crashed."


# ✅ Send message
def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })


# ✅ Health check
@app.route("/", methods=["GET"])
def home():
    return "Bot is running", 200


# ✅ Render port
if name == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
