import os
import urllib.parse
import requests
from flask import Flask, request, redirect, render_template_string
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

# load .env if present for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # python-dotenv is optional; environment variables may be set elsewhere
    pass

app = Flask(__name__)
authenticated_users = {}   # { tg_id: {google_sub, email, name} }


# Configuration from environment
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
WEBAPP_BASE = os.environ.get("LOGIN_BASE_URL")
REDIRECT_URI = os.environ.get("REDIRECT_URI", f"{WEBAPP_BASE}/oauth2callback")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

if not CLIENT_ID or not CLIENT_SECRET:
    print("Warning: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET should be set in environment or in a .env file.")
    print("If you created a .env file, ensure it's named '.env' (not '.evn') and placed in the project root.")
    print("You can also set them in PowerShell: $env:GOOGLE_CLIENT_ID='<id>'; $env:GOOGLE_CLIENT_SECRET='<secret>'")

@app.route("/")
def index():
    return "Google OAuth2 Authentication Webapp is running."

@app.route("/hello")
def hello():
    return "<h1>CIAO<h1>"

@app.route("/login")
def login():
    tg_id = request.args.get("tg_id")
    if not tg_id:
        return "Missing tg_id query parameter", 400

    auth_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": REDIRECT_URI,
        "state": tg_id,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = auth_endpoint + "?" + urllib.parse.urlencode(params)
    return redirect(url)

@app.route("/oauth2callback")
def oauth2callback():
    error = request.args.get("error")
    if error:
        return f"Error: {error}", 400

    code = request.args.get("code")
    state = request.args.get("state")
    if not code or not state:
        return "Missing code or state", 400

    token_endpoint = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    resp = requests.post(token_endpoint, data=data)
    if resp.status_code != 200:
        return f"Token exchange failed: {resp.text}", 500

    token_json = resp.json()
    id_token_str = token_json.get("id_token")
    if not id_token_str:
        return "No id_token in token response", 500

    try:
        idinfo = id_token.verify_oauth2_token(id_token_str, grequests.Request(), CLIENT_ID)
    except Exception as e:
        return f"Failed to verify id token: {e}", 500

    # Parse state as tg_id
    try:
        tg_id = int(state)
    except Exception:
        return "Invalid state (tg_id)", 400

    sub = idinfo.get("sub")
    email = idinfo.get("email")
    name = idinfo.get("name")

    # Store authenticated session
    authenticated_users[tg_id] = {
        "google_sub": sub,
        "email": email,
        "name": name,
        "tokens": token_json,  # optional: store access_token, refresh_token, expires_in
    }

    # Notify Telegram bot
    message = f"Login successful!\nYou are authenticated as: {email}"
    requests.post(BOT_API, json={"chat_id": tg_id, "text": message})

    # Return a simple HTML page to the user
    return f"""
        <html>
        <body>
            <h2>Login successful</h2>
            <p>You can now return to Telegram.</p>
        </body>
        </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
