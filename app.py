from flask import Flask, request
import requests
import os
import time
from pymongo import MongoClient

app = Flask(__name__)

# =========================
# 🔐 ENV
# =========================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MONGO_URI = os.environ.get("MONGO_URI")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# =========================
# 🗄️ DATABASE
# =========================
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
users_collection = db["users"]

ADMIN_ID = 1294323193


# =========================
# 👤 USER SYSTEM
# =========================
def save_user(user):
    if user.get("id") and not users_collection.find_one({"id": user["id"]}):
        users_collection.insert_one(user)


def get_user_count():
    return users_collection.count_documents({})


# =========================
# 📢 BROADCAST
# =========================
def broadcast_message(text):
    users = users_collection.find()
    success = 0

    for user in users:
        try:
            send_message(user["id"], text)
            success += 1
            time.sleep(0.05)
        except Exception as e:
            print("Broadcast error:", e)

    return success


# =========================
# 🤖 GEMINI (STRICT)
# =========================
def get_gemini_response(user_message):
    models = ["gemini-2.5-flash", "gemini-1.5-flash"]

    data = {
        "contents": [{"parts": [{"text": user_message}]}]
    }

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"

        for attempt in range(2):
            try:
                response = requests.post(url, json=data)

                print(f"{model}:", response.status_code)

                if response.status_code == 200:
                    result = response.json()

                    # ✅ STRICT VALIDATION
                    if (
                        "candidates" in result and
                        len(result["candidates"]) > 0 and
                        "content" in result["candidates"][0] and
                        "parts" in result["candidates"][0]["content"]
                    ):
                        text = result["candidates"][0]["content"]["parts"][0].get("text", "")

                        if text and text.strip():
                            return text.strip()

                elif response.status_code == 503:
                    time.sleep(2)

            except Exception as e:
                print("AI error:", e)

    return None  # force fallback


# =========================
# 🧠 FALLBACK (SMART)
# =========================
def fallback_response(text):
    text = text.lower()

    if "python" in text:
        return """💻 Simple Python Code:

print("Happy Birthday 🎉")
"""

    elif "website" in text or "scan" in text:
        return "🔍 Basic check: Ensure the site uses HTTPS and is trusted."

    elif "phishing" in text:
        return "⚠️ Avoid suspicious links. Never enter passwords on unknown sites."

    elif "hi" in text or "hello" in text:
        return "Hello! 👋 I'm still here even if AI is busy."

    else:
        return "⚠️ AI is currently overloaded, but I can still help with basic tasks."


# =========================
# 📤 TELEGRAM
# =========================
def send_message(chat_id, text, reply_markup=None):
    url = f"{TELEGRAM_API_URL}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    requests.post(url, json=payload)


def send_typing(chat_id):
    url = f"{TELEGRAM_API_URL}/sendChatAction"
    requests.post(url, json={
        "chat_id": chat_id,
        "action": "typing"
    })


# =========================
# 🎛 UI MENUS
# =========================
def main_menu():
    return {
        "keyboard": [
            ["💬 Ask AI"],
            ["🛠 Tools"],
            ["ℹ️ Help"]
        ],
        "resize_keyboard": True
    }


def tools_menu():
    return {
        "keyboard": [
            ["🔍 Phishing Check"],
            ["🛡 Vulnerability Scan"],
            ["🔙 Back"]
        ],
        "resize_keyboard": True
    }


# =========================
# 🚀 WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    message = data.get("message")
    if not message:
        return "OK", 200

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # 👤 Save user
    user = message.get("from", {})
    save_user({
        "id": user.get("id"),
        "name": user.get("first_name"),
        "username": user.get("username")
    })

    send_typing(chat_id)

    # =========================
    # 📢 BROADCAST
    # =========================
    if text.startswith("/broadcast"):
        if chat_id != ADMIN_ID:
            send_message(chat_id, "❌ Not allowed")
        else:
            msg = text.replace("/broadcast", "").strip()
            if not msg:
                send_message(chat_id, "⚠️ Usage: /broadcast message")
            else:
                send_message(chat_id, "📢 Sending...")
                count = broadcast_message(msg)
                send_message(chat_id, f"✅ Sent to {count} users")

    # =========================
    # 🎛 UI
    # =========================
    elif text == "/start":
        send_message(chat_id, "Welcome to Chenura AI Bot 🤖", main_menu())

    elif text == "💬 Ask AI":
        send_message(chat_id, "Ask me anything 🤖")

    elif text == "🛠 Tools":
        send_message(chat_id, "Select a tool:", tools_menu())

    elif text == "ℹ️ Help":
        send_message(chat_id, "I can help with coding, AI, cybersecurity.")

    elif text == "🔙 Back":
        send_message(chat_id, "Back to menu", main_menu())

    # =========================
    # 🛡 TOOLS
    # =========================
    elif text == "🔍 Phishing Check":
        send_message(chat_id, "Send a URL to check.")

    elif text == "🛡 Vulnerability Scan":
        send_message(chat_id, "Send a website.")

    # =========================
    # 📊 ADMIN
    # =========================
    elif text == "/users":
        if chat_id == ADMIN_ID:
            send_message(chat_id, f"👥 Users: {get_user_count()}")
        else:
            send_message(chat_id, "❌ Not allowed")

    # =========================
    # 🤖 AI + FALLBACK (FIXED)
    # =========================
    else:
        ai_reply = get_gemini_response(text)

        if ai_reply is not None and ai_reply.strip() != "":
            send_message(chat_id, ai_reply)
        else:
            send_message(chat_id, fallback_response(text))

    return "OK", 200


# =========================
# ❤️ HEALTH
# =========================
@app.route("/")
def home():
    return "Bot is running"


# =========================
# ▶️ RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
