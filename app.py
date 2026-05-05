from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
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
        text = message.get("text", "").lower()

        # ✅ Command handling
        if text == "/start":
            reply = "Hello! I'm your AI assistant bot. Ask me anything."

        elif text == "hi" or text == "hello":
            reply = "Hi there! How can I help you?"

        elif "name" in text:
            reply = "I'm your AI chatbot built with Python and Flask."

        else:
            reply = "I understand your message, but I'm not fully trained yet."

        send_message(chat_id, reply)

    return "OK", 200


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
