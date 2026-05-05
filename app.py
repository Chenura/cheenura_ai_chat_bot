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

# ✅ Store unique users
users = set()


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
        user_id = message["from"]["id"]
        text = message.get("text", "")

        # ✅ Track user
        users.add(user_id)
        print("Total users:", len(users))

        if text.lower() == "/start":
            reply = f"Hello! I'm your Gemini 2.5 AI assistant 🚀\nUsers: {len(users)}"

        elif text.lower() == "/users":
            reply = f"👥 Total users: {len(users)}"

        elif "hi" in text.lower() or "hello" in text.lower():
            reply = "Hi there! How can I help you?"

        else:
            reply = get_gemini_response(text)

        send_message(chat_id, reply)

    return "OK", 200


# ✅ Gemini with retry + fallback
def get_gemini_response(user_message):
    models = [
        "gemini-2.5-flash",
        "gemini-pro"
    ]

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"

        try:
            response = requests.post(
                url,
                json={
                    "contents": [{"parts": [{"text": user_message}]}]
                },
                timeout=20
            )

            print(f"Trying model: {model}")
            print("Status:", response.status_code)

            if response.status_code == 200:
                result = response.json()

                if "candidates" in result:
                    return result["candidates"][0]["content"]["parts"][0]["text"]

            elif response.status_code == 503:
                print(f"{model} overloaded, trying next...")

            elif response.status_code == 429:
                return "⚠️ Daily limit reached. Try again tomorrow."

        except Exception as e:
            print("Error:", str(e))

    return "⚠️ AI is busy right now. Please try again in a moment."


# ✅ Send message
def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"

    try:
        requests.post(url, json={
            "chat_id": chat_id,
            "text": text
        })
    except Exception as e:
        print("Telegram send error:", str(e))


# ✅ Health check
@app.route("/", methods=["GET"])
def home():
    return f"Bot is running | Users: {len(users)}", 200


# ✅ Run app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
