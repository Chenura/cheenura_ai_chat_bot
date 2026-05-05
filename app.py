from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


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

        # Basic commands
        if text.lower() == "/start":
            reply = "Hello! I'm your Gemini AI bot. Ask me anything."

        elif "hi" in text.lower() or "hello" in text.lower():
            reply = "Hi there! How can I help you?"

        else:
            reply = get_gemini_response(text)

        send_message(chat_id, reply)

    return "OK", 200


# ✅ Gemini API function
def get_gemini_response(user_message):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

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

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        print("Gemini Error:", response.text)
        return "Error: Gemini AI not working."

    result = response.json()

    try:
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "Error: Unexpected Gemini response."


# Send message to Telegram
def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })


@app.route("/", methods=["GET"])
def home():
    return "Bot is running", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
