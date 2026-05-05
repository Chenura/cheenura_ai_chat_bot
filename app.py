from flask import Flask, request
import requests
import os

app = Flask(__name__)

# 🔐 ENV VARIABLES (SET THESE IN RENDER)
TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

# 🤖 Gemini AI function (UPDATED)
def ask_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()

        return result["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        print("Gemini Error:", e)
        return "⚠️ AI is busy, try again later."

# 🏠 Home route (for Render check)
@app.route('/')
def home():
    return "🤖 Bot is running!"

# 📩 Telegram webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"].get("text", "")

        # ⏳ Optional: typing effect
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendChatAction", json={
            "chat_id": chat_id,
            "action": "typing"
        })

        # 🤖 Get AI reply
        reply = ask_gemini(user_text)

        # 🛑 Fallback if error
        if not reply or "error" in reply.lower():
            reply = "🤖 I'm having trouble right now. Try again later."

        # 📤 Send message
        requests.post(TELEGRAM_URL, json={
            "chat_id": chat_id,
            "text": reply
        })

    return "ok"


# 🚀 Run locally (Render uses gunicorn)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
