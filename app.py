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
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
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
# 🤖 GEMINI AI
# =========================
def get_gemini_response(user_message):
    models = ["gemini-2.5-flash", "gemini-1.5-pro"]

    data = {
        "contents": [{"parts": [{"text": user_message}]}]
    }

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"

        for attempt in range(3):
            try:
                response = requests.post(url, json=data, timeout=15)

                print(f"{model}:", response.status_code)

                if response.status_code == 200:
                    result = response.json()

                    if "candidates" in result:
                        text = result["candidates"][0]["content"]["parts"][0].get("text", "")
                        if text:
                            return text.strip()

                elif response.status_code == 429:
                    time.sleep(5)

            except Exception as e:
                print("Gemini error:", e)

    return None


# =========================
# 🤖 OPENAI BACKUP
# =========================
def get_openai_response(user_message):
    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": user_message}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)

        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()

        else:
            print("OpenAI error:", response.text)

    except Exception as e:
        print("OpenAI exception:", e)

    return None


# =========================
# 🧠 AI ROUTER
# =========================
def get_ai_response(text):
    # Try Gemini
    gemini = get_gemini_response(text)
    if gemini:
        return gemini

    print("⚠️ Gemini failed → trying OpenAI")

    # Try OpenAI
    openai = get_openai_response(text)
    if openai:
        return openai

    return None


# =========================
# 🧠 FALLBACK SYSTEM
# =========================
def fallback_response(text):
    t = text.lower()

    if any(w in t for w in ["hi", "hello", "hey"]):
        return "Hello 👋 I'm Chenura AI Bot. How can I help?"

    elif "who are you" in t:
        return "🤖 I'm Chenura AI Chat Bot, built for coding, AI, and cybersecurity."

    elif "what can you do" in t:
        return """🤖 I can help with:

💻 Python code
🛡 Cybersecurity tips
🌐 Website checks

Try:
• python code
• phishing tips
• check website"""

    elif "python" in t or "code" in t:
        return """💻 Example:

print("Hello World")
for i in range(3):
    print(i)"""

    elif "phishing" in t:
        return """⚠️ Phishing tips:

• Don't click unknown links  
• Check sender  
• Never share passwords"""

    elif "website" in t:
        return """🔍 Website safety:

✔ HTTPS  
✔ Trusted domain  
✔ No suspicious popups"""

    else:
        return f"""⚠️ AI is busy right now.

You said: "{text}"

Try:
• python code
• phishing tips
• check website"""


# =========================
# 🔁 BACKGROUND RETRY
# =========================
def retry_ai(chat_id, text):
    def task():
        time.sleep(3)

        ai_reply = get_ai_response(text)
        if ai_reply:
            send_message(chat_id, f"🤖 Update:\n\n{ai_reply}")

    threading.Thread(target=task).start()


# =========================
# 📤 TELEGRAM
# =========================
def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})


def send_typing(chat_id):
    url = f"{TELEGRAM_API_URL}/sendChatAction"
    requests.post(url, json={"chat_id": chat_id, "action": "typing"})


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

    # AI + fallback
    else:
        ai_reply = get_ai_response(text)

        if ai_reply:
            send_message(chat_id, ai_reply)
        else:
            send_message(chat_id, fallback_response(text))
            retry_ai(chat_id, text)

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
