from flask import Flask, request
import requests
import os
from pymongo import MongoClient

app = Flask(__name__)

# 🔐 Environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MONGO_URI = os.environ.get("MONGO_URI")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not set")

if not MONGO_URI:
    raise ValueError("MONGO_URI not set")

# 🤖 Telegram API
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# 🗄️ MongoDB connection
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
users_collection = db["users"]

# 👤 Replace with YOUR Telegram ID
ADMIN_ID = 1294323193


# ✅ Save user to database
def save_user(user):
    if not user.get("id"):
        return

    existing = users_collection.find_one({"id": user["id"]})

    if not existing:
        users_collection.insert_one(user)


# ✅ Count users
def get_user_count():
    return users_collection.count_documents({})


# ✅ Gemini 2.5 AI function
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
            return "Error: AI not working"

        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        print("Exception:", str(e))
        return "Error: AI crashed"


# ✅ Send message to Telegram
def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"

    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })


# ✅ Webhook (main logic)
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

        # 👤 Extract user info
        user_info = message.get("from", {})
        user_data = {
            "id": user_info.get("id"),
            "name": user_info.get("first_name"),
            "username": user_info.get("username")
        }

        # 💾 Save user
        save_user(user_data)

        # 🤖 Bot logic
        if text == "/start":
            reply = "Hello! I'm your Chenura Ai Chat Bot Powered By Shadow Technologies. Ask me anything."

        elif text == "/users":
            if chat_id == ADMIN_ID:
                count = get_user_count()
                reply = f"Total users: {count}"
            else:
                reply = "Not allowed"

        elif "hi" in text or "hello" in text:
            reply = "Hi there! How can I help you?"

        else:
            reply = get_gemini_response(text)

        send_message(chat_id, reply)

    return "OK", 200


# ✅ Health check route
@app.route("/", methods=["GET"])
def home():
    return "Bot is running", 200


# ✅ Run app (Render compatible)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
