# SDE Project - Webapp Deployment

## Deployment to Render.com

### Steps:

1. **Create a Render.com account** at https://render.com

2. **Push your code to GitHub** (make sure `.env` is in `.gitignore` so secrets are never exposed)

3. **Connect your GitHub repo to Render**:
   - Go to Render Dashboard → New Web Service
   - Connect your GitHub repository
   - Select this repo

4. **Configure environment variables** in Render dashboard:
   - `GOOGLE_CLIENT_ID` → Your Google OAuth Client ID
   - `GOOGLE_CLIENT_SECRET` → Your Google OAuth Client Secret
   - `BOT_TOKEN` → Your Telegram Bot Token
   - `WEBAPP_BASE` → Your Render URL (e.g., `https://your-app.onrender.com`)
   - `REDIRECT_URI` → `https://your-app.onrender.com/oauth2callback`

5. **Deploy** - Render will automatically:
   - Install dependencies from `requirements.txt`
   - Run the app using `gunicorn` (specified in `Procfile`)

### Important Security Notes:

- ✅ All secrets are stored as **environment variables in Render** (never in code)
- ✅ `.env` file is in `.gitignore` (never committed to Git)
- ✅ `BOT_TOKEN` is now retrieved from `os.environ.get()` instead of hardcoded
- ✅ Your credentials are safe and not exposed in the repository

### Local Development:

Create a `.env` file locally (Git ignores it):
```
GOOGLE_CLIENT_ID=your_id_here
GOOGLE_CLIENT_SECRET=your_secret_here
BOT_TOKEN=your_token_here
WEBAPP_BASE=http://localhost:5000
```

Then run: `python webapp.py`
