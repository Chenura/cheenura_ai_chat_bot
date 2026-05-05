from flask import Flask, request
import requests
import os
import time
import threading
from pymongo import MongoClient

app = Flask(__name__)

# =========================
# 🔐 ENV VARIABLES
# =========================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MONGO_URI = os.environ.get("MONGO_URI")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# =========================
# 🗄 DATABASE
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
# 🤖 GEMINI AI (SAFE)
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
                response = requests.post(url, json=data, timeout=10)

                print(f"{model}:", response.status_code)

                if response.status_code == 200:
                    result = response.json()

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

    return None


# =========================
# 🧠 INTELLIGENT FALLBACK
# =========================
def fallback_response(text):
    text = text.lower()

    # Greeting
    if any(word in text for word in ["hi", "hello", "hey"]):
        return "Hello 👋 I’m running in smart basic mode. Try:\n• python code\n• phishing tips\n• website check"

    # Help / capability
    elif "help" in text or "what can you do" in text:
        return """🤖 Available features:

💻 Coding
- Simple Python scripts

🛡 Cybersecurity
- Phishing detection tips
- Website safety checks

🔧 Tools
- Basic vulnerability scan

⚠️ AI is temporarily busy, but core features are active."""

    # Python
    elif "python" in text:
        return """💻 Example Python Code:

print("Happy Birthday 🎉")

for i in range(5):
    print(i)
"""

    # Website / scan
    elif "website" in text or "scan" in text or "url" in text:
        return """🔍 Website Safety Check:

✔ HTTPS enabled?
✔ Trusted domain?
✔ No suspicious popups?

⚠️ Never enter passwords on unknown sites."""

    # Phishing
    elif "phishing" in text:
        return """⚠️ Phishing Tips:

• Check sender carefully  
• Avoid unknown links  
• Never share passwords  
• Look for HTTPS 🔒"""

    # Default
    else:
        return """⚠️ AI is busy right now.

Try:
👉 python code
👉 phishing tips
👉 check website"""


# =========================
# 🔁 BACKGROUND RETRY
# =========================
def retry_ai_later(chat_id, text):
    def task():
        for _ in range(2):  # retry twice
            time.sleep(3)

            ai_reply = get_gemini_response(text)
            if ai_reply and ai_reply.strip():
                send_message(chat_id, f"🤖 Update:\n\n{ai_reply}")
                return

    threading.Thread(target=task).start()


# =========================
# 📤 TELEGRAM
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

    message = data.get("message")
    if not message:
        return "OK", 200

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # Save user
    user = message.get("from", {})
    save_user({
        "id": user.get("id"),
        "name": user.get("first_name"),
        "username": user.get("username")
    })

    send_typing(chat_id)

    # Commands
    if text == "/start":
        send_message(chat_id, "Welcome to Chenura AI Bot 🤖")

    elif text == "/users":
        if chat_id == ADMIN_ID:
            send_message(chat_id, f"👥 Users: {get_user_count()}")
        else:
            send_message(chat_id, "❌ Not allowed")

    # =========================
    # 🤖 AI + FALLBACK + RETRY
    # =========================
    else:
        ai_reply = get_gemini_response(text)

        if ai_reply and ai_reply.strip():
            send_message(chat_id, ai_reply)
        else:
            # ⚡ instant fallback
            send_message(chat_id, fallback_response(text))

            # 🔁 retry in background
            retry_ai_later(chat_id, text)

    return "OK", 200


# =========================
# ❤️ HEALTH CHECK
# =========================
@app.route("/")
def home():
    return "Bot is running"


# =========================
# ▶ RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
