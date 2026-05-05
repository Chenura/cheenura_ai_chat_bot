from flask import Flask, request
import requests
import os
import time
from pymongo import MongoClient

app = Flask(__name__)

# =========================
# 🔐 ENV VARIABLES
# =========================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MONGO_URI = os.environ.get("MONGO_URI")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not set")
if not MONGO_URI:
    raise ValueError("MONGO_URI not set")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# =========================
# 🗄️ DATABASE
# =========================
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
users_collection = db["users"]

ADMIN_ID = 1294323193


# =========================
# 👤 USER FUNCTIONS
# =========================
def save_user(user):
    if not user.get("id"):
        return
    if not users_collection.find_one({"id": user["id"]}):
        users_collection.insert_one(user)


def get_user_count():
    return users_collection.count_documents({})


# =========================
# 🤖 GEMINI (2.5 + FALLBACK)
# =========================
def get_gemini_response(user_message):
    models = [
        "gemini-2.5-flash",   # primary
        "gemini-1.5-flash"    # fallback
    ]

    data = {
        "contents": [
            {
                "parts": [{"text": user_message}]
            }
        ]
    }

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"

        for attempt in range(2):
            try:
                response = requests.post(url, json=data)

                print(f"Model: {model}, Status:", response.status_code)

                if response.status_code == 200:
                    result = response.json()

                    if "candidates" in result:
                        return result["candidates"][0]["content"]["parts"][0]["text"]

                elif response.status_code == 503:
                    time.sleep(2)

                else:
                    break

            except Exception as e:
                print("Error:", e)
                break

    return "⚠️ AI is currently overloaded. Please try again in a moment."


# =========================
# 📤 TELEGRAM FUNCTIONS
# =========================
def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })


def send_typing(chat_id):
    url = f"{TELEGRAM_API_URL}/sendChatAction"
    requests.post(url, json={
        "chat_id": chat_id,
        "action": "typing"
    })


# =========================
# 🚀 WEBHOOK
# =========================
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

        # 👤 Save user
        user_info = message.get("from", {})
        user_data = {
            "id": user_info.get("id"),
            "name": user_info.get("first_name"),
            "username": user_info.get("username")
        }
        save_user(user_data)

        # ⏳ Typing indicator
        send_typing(chat_id)

        # 🤖 Commands
        if text == "/start":
            reply = "Hello! I'm Chenura AI Chat Bot 🤖\nPowered by Gemini 2.5.\nAsk me anything."

        elif text == "/users":
            if chat_id == ADMIN_ID:
                reply = f"👥 Total users: {get_user_count()}"
            else:
                reply = "❌ Not allowed"

        elif text in ["hi", "hello"]:
            reply = "Hi there! How can I help you?"

        else:
            reply = get_gemini_response(text)

        send_message(chat_id, reply)

    return "OK", 200


# =========================
# ❤️ HEALTH CHECK
# =========================
@app.route("/", methods=["GET"])
def home():
    return "Bot is running", 200


# =========================
# ▶️ RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
