from flask import Flask, request, redirect, session
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
SECRET_KEY = os.environ.get("SECRET_KEY")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

if not BOT_TOKEN or not MONGO_URI or not ENCRYPTION_KEY or not SECRET_KEY:
    raise ValueError("Missing environment variables")

app.secret_key = SECRET_KEY

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

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
# 👤 USER FUNCTIONS
# =========================
def save_user(user_id):
    users.update_one(
        {"user_id": user_id},
        {"$setOnInsert": {"requests": 0}},
        upsert=True
    )

def save_api_key(user_id, api_key):
    users.update_one(
        {"user_id": user_id},
        {"$set": {"gemini_key": encrypt_key(api_key)}}
    )

def get_api_key(user_id):
    user = users.find_one({"user_id": user_id})
    if user and user.get("gemini_key"):
        return decrypt_key(user["gemini_key"])
    return None

def increment_usage(user_id):
    users.update_one({"user_id": user_id}, {"$inc": {"requests": 1}})

# =========================
# 🤖 GEMINI AI
# =========================
def get_gemini_response(text, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    try:
        res = requests.post(
            url,
            json={"contents": [{"parts": [{"text": text}]}]},
            timeout=20
        )

        if res.status_code == 200:
            data = res.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

        elif res.status_code == 429:
            return "⚠️ API limit reached."

        elif res.status_code == 503:
            return "⚠️ AI is busy. Try again."

        else:
            return "⚠️ AI error."

    except Exception as e:
        print("AI error:", e)
        return "⚠️ Connection failed."

# =========================
# 📤 TELEGRAM
# =========================
def send_message(chat_id, text):
    try:
        requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text}
        )
    except Exception as e:
        print("Telegram error:", e)

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
        reply = f"📊 Your usage: {used}"

    else:
        api_key = get_api_key(user_id)

        if not api_key:
            reply = "🔑 Please set your API key using /setkey"
        else:
            reply = get_gemini_response(text, api_key)
            increment_usage(user_id)

    send_message(chat_id, reply)
    return "OK", 200

# =========================
# 🔐 LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/dashboard")

        return "❌ Invalid credentials"

    return """
    <h2>🔐 Admin Login</h2>
    <form method="POST">
        Username:<br><input name="username"><br><br>
        Password:<br><input name="password" type="password"><br><br>
        <button type="submit">Login</button>
    </form>
    """

# =========================
# 📊 DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect("/login")

    total_users = users.count_documents({})
    total_requests = sum(u.get("requests", 0) for u in users.find())

    return f"""
    <h1>📊 Admin Dashboard</h1>
    <p>👥 Users: {total_users}</p>
    <p>⚡ Total Requests: {total_requests}</p>
    <br>
    <a href="/logout">Logout</a>
    """

# =========================
# 🚪 LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# =========================
# ❤️ HOME
# =========================
@app.route("/")
def home():
    return "Bot running", 200

# =========================
# ▶ RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
