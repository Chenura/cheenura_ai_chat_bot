# Fixed app.py

```python
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

# Safe admin telegram id
ADMIN_TELEGRAM_ID = os.environ.get("ADMIN_TELEGRAM_ID", "0")

app.secret_key = SECRET_KEY or "supersecret"

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
# 👤 USER SYSTEM
# =========================
def save_user(user_id, username):
    users.update_one(
        {"user_id": user_id},
        {
            "$set": {"username": username},
            "$setOnInsert": {"requests": 0}
        },
        upsert=True
    )



def save_api_key(user_id, api_key):
    users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "gemini_key": encrypt_key(api_key)
            }
        }
    )



def get_api_key(user_id):
    user = users.find_one({"user_id": user_id})

    if user and user.get("gemini_key"):
        try:
            return decrypt_key(user["gemini_key"])
        except Exception as e:
            print("Decrypt error:", e)
            return None

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

    models = [
        "gemini-2.5-flash",
        "gemini-1.5-flash"
    ]

    for model in models:

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )

        try:
            response = requests.post(
                url,
                json={
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": text
                                }
                            ]
                        }
                    ]
                },
                timeout=30
            )

            print("====================")
            print("MODEL:", model)
            print("STATUS:", response.status_code)
            print("BODY:", response.text)
            print("====================")

            # Success
            if response.status_code == 200:

                data = response.json()

                if (
                    "candidates" in data
                    and len(data["candidates"]) > 0
                ):

                    parts = data["candidates"][0]["content"]["parts"]

                    if len(parts) > 0:
                        return parts[0].get("text", "⚠️ Empty AI response")

            # Fallback errors
            elif response.status_code in [429, 500, 503]:
                print(f"{model} failed. Trying fallback...")
                continue

            # Invalid key
            elif response.status_code == 400:
                return "⚠️ Invalid API request or API key."

            elif response.status_code == 401:
                return "⚠️ Unauthorized API key."

            elif response.status_code == 403:
                return "⚠️ API access denied."

            elif response.status_code == 404:
                print(f"{model} not found. Trying fallback...")
                continue

        except Exception as e:
            print(f"{model} ERROR:", str(e))
            continue

    return "⚠️ All Gemini models are currently unavailable."


# =========================
# 📤 TELEGRAM
# =========================
def send_message(chat_id, text):

    try:
        requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": str(text)
            },
            timeout=20
        )

    except Exception as e:
        print("Telegram send error:", e)


# =========================
# 🚀 WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():

    try:

        data = request.get_json()

        if not data:
            return "OK", 200

        message = data.get("message")

        if not message:
            return "OK", 200

        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        username = message["from"].get("username", "NoUsername")
        text = message.get("text", "")

        save_user(user_id, username)

        # =========================
        # COMMANDS
        # =========================
        if text == "/start":

            reply = (
                "🤖 Welcome to Chenura AI Bot\n\n"
                "🔑 Set your Gemini API key:\n"
                "/setkey\n\n"
                "📊 Check usage:\n"
                "/myusage"
            )

        elif text == "/setkey":

            reply = (
                "🔑 Get your Gemini API key:\n"
                "https://aistudio.google.com/app/apikey\n\n"
                "Send like this:\n\n"
                "key: YOUR_API_KEY"
            )

        elif text.lower().startswith("key:"):

            key = text.split("key:", 1)[1].strip()

            if len(key) < 10:
                reply = "❌ Invalid API key format."
            else:
                save_api_key(user_id, key)
                reply = "✅ API key saved securely 🔐"

        elif text == "/myusage":

            user = users.find_one({"user_id": user_id})

            used = user.get("requests", 0) if user else 0

            reply = f"📊 Your usage: {used}"

        elif text == "/users":

            if str(user_id) != str(ADMIN_TELEGRAM_ID):
                reply = "❌ Admin only command."
            else:
                total_users = users.count_documents({})
                reply = f"👥 Total users using bot: {total_users}"

        # =========================
        # AI CHAT
        # =========================
        else:

            api_key = get_api_key(user_id)

            if not api_key:
                reply = "🔑 Please set your API key first using /setkey"
            else:
                reply = get_gemini_response(text, api_key)
                increment_usage(user_id)

        send_message(chat_id, reply)

        return "OK", 200

    except Exception as e:
        print("Webhook error:", e)
        return "OK", 200


# =========================
# 🔐 LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        if (
            request.form.get("username") == ADMIN_USERNAME
            and request.form.get("password") == ADMIN_PASSWORD
        ):

            session["admin"] = True
            return redirect("/dashboard")

        return "❌ Invalid credentials"

    return """
    <h2>🔐 Admin Login</h2>

    <form method="POST">
        Username:<br>
        <input name="username"><br><br>

        Password:<br>
        <input type="password" name="password"><br><br>

        <button>Login</button>
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

    total_requests = sum(
        u.get("requests", 0)
        for u in users.find()
    )

    rows = ""

    for u in users.find().sort("requests", -1).limit(20):

        rows += f"""
        <tr>
            <td>{u.get('user_id')}</td>
            <td>{u.get('username')}</td>
            <td>{u.get('requests', 0)}</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>

        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

        <style>
            body {{
                background:#0f172a;
                color:white;
                font-family:Arial;
                padding:20px;
            }}

            .card {{
                background:#1e293b;
                padding:20px;
                border-radius:10px;
                margin-bottom:20px;
            }}

            table {{
                width:100%;
                border-collapse:collapse;
            }}

            th, td {{
                padding:10px;
                border-bottom:1px solid #334155;
            }}

            tr:hover {{
                background:#334155;
            }}

            a {{
                color:cyan;
            }}
        </style>

    </head>

    <body>

        <h1>📊 Dashboard</h1>

        <div class="card">
            <p>👥 Users: {total_users}</p>
            <p>⚡ Requests: {total_requests}</p>
        </div>

        <div class="card">
            <canvas id="chart"></canvas>
        </div>

        <div class="card">

            <h2>Top Users</h2>

            <table>
                <tr>
                    <th>ID</th>
                    <th>Username</th>
                    <th>Requests</th>
                </tr>

                {rows}

            </table>

        </div>

        <a href="/logout">Logout</a>

        <script>
            new Chart(document.getElementById("chart"), {{
                type: "bar",
                data: {{
                    labels: ["Users", "Requests"],
                    datasets: [{{
                        label: "Stats",
                        data: [{total_users}, {total_requests}]
                    }}]
                }}
            }});
        </script>

    </body>
    </html>
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
    return "Bot running successfully 🚀", 200


# =========================
# ▶ RUN
# =========================
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
```

# IMPORTANT ENV VARIABLES

Add these in Render/Railway:

```env
BOT_TOKEN=your_bot_token
MONGO_URI=your_mongodb_url
ENCRYPTION_KEY=your_fernet_key
SECRET_KEY=your_secret_key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_TELEGRAM_ID=your_telegram_numeric_id
```

# MOST COMMON REASON BOT BREAKS

Usually this line crashes:

```python
ADMIN_TELEGRAM_ID = int(os.environ.get("ADMIN_TELEGRAM_ID"))
```

if the env variable is missing.

The fixed version avoids that crash.
