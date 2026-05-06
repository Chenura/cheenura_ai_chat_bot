from flask import Flask, request
import requests
import os
from pymongo import MongoClient
from cryptography.fernet import Fernet

app = Flask(__name__)

# =========================
# 🔐 ENV VARIABLES
# =========================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI")
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")

if not BOT_TOKEN or not MONGO_URI or not ENCRYPTION_KEY:
    raise ValueError("Missing environment variables")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# 👉 YOUR TELEGRAM ID
ADMIN_ID = 1294323193

# =========================
# 🔐 ENCRYPTION
# =========================
cipher = Fernet(ENCRYPTION_KEY.encode())

def encrypt_key(key):
    return cipher.encrypt(key.encode()).decode()

def decrypt_key(key):
    return cipher.decrypt(key.encode()).decode()

# =========================
# 🗄 DATABASE
# =========================
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
users = db["users"]

# =========================
# 👤 USER SYSTEM
# =========================
def save_user(user_id):
    users.update_one(
        {"user_id": user_id},
        {"$setOnInsert": {
            "requests": 0
        }},
        upsert=True
    )

def save_api_key(user_id, api_key):
    encrypted = encrypt_key(api_key)

    users.update_one(
        {"user_id": user_id},
        {"$set": {"gemini_key": encrypted}},
        upsert=True
    )

def get_user_api_key(user_id):
    user = users.find_one({"user_id": user_id})

    if user and user.get("gemini_key"):
        return decrypt_key(user["gemini_key"])

    return None

def increment_usage(user_id):
    users.update_one(
        {"user_id": user_id},
        {"$inc": {"requests": 1}}
    )

# =========================
# 🤖 GEMINI AI
# =========================
def get_gemini_response(text, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    try:
        response = requests.post(
            url,
            json={
                "contents": [{"parts": [{"text": text}]}]
            },
            timeout=20
        )

        if response.status_code == 200:
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]

        elif response.status_code == 429:
            return "⚠️ Your API limit reached."

        elif response.status_code == 503:
            return "⚠️ AI is busy. Try again."

        else:
            return "⚠️ AI error."

    except Exception as e:
        print("AI error:", e)
        return "⚠️ Failed to connect AI."

# =========================
# 📤 TELEGRAM
# =========================
def send_message(chat_id, text):
    requests.post(
        f"{TELEGRAM_API_URL}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )

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
    user_id = message["from"]["id"]
    text = message.get("text", "")

    save_user(user_id)

    # =========================
    # COMMANDS
    # =========================
    if text == "/start":
        reply = """🤖 Welcome to Chenura AI Bot

🔑 Set your API key:
/setkey

📊 Check usage:
/myusage
"""

    elif text == "/setkey":
        reply = (
            "🔑 Get your Gemini API key:\n"
            "https://aistudio.google.com/app/apikey\n\n"
            "Then send:\nkey: YOUR_API_KEY"
        )

    elif text.lower().startswith("key:"):
        key = text.split("key:")[1].strip()
        save_api_key(user_id, key)
        reply = "✅ API key saved securely 🔐"

    elif text == "/myusage":
        user = users.find_one({"user_id": user_id})
        used = user.get("requests", 0) if user else 0
        reply = f"📊 Total requests: {used}"

    elif text == "/users":
        if user_id == ADMIN_ID:
            count = users.count_documents({})
            reply = f"👥 Total users: {count}"
        else:
            reply = "❌ Not allowed"

    else:
        api_key = get_user_api_key(user_id)

        if not api_key:
            reply = "🔑 Please set your API key first using /setkey"
        else:
            reply = get_gemini_response(text, api_key)
            increment_usage(user_id)

    send_message(chat_id, reply)
    return "OK", 200

# =========================
# 📊 DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():
    if request.args.get("admin") != str(ADMIN_ID):
        return "❌ Unauthorized"

    total_users = users.count_documents({})
    total_requests = sum(u.get("requests", 0) for u in users.find())

    html = f"""
    <h1>📊 Dashboard</h1>
    <p>Users: {total_users}</p>
    <p>Total Requests: {total_requests}</p>
    <h3>Users:</h3><ul>
    """

    for u in users.find().limit(20):
        html += f"<li>{u['user_id']} - {u.get('requests',0)} requests</li>"

    html += "</ul>"
    return html

# =========================
# ❤️ HEALTH
# =========================
@app.route("/")
def home():
    return "Bot running"

# =========================
# ▶ RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
