On windows: 
launch the start.bat script. It will open few terminals with the following services:
* Telegram Bot
* Internal service to manage the payments
* Tunnelling to make the internal payment service accessible by PayPal


On Telegram, search for "@SDE_barcarolograziadei_bot" and type /start.



NB: CREATE YOUR OWM .env FILE! It must contain:
# Telegram Bot Token (from @BotFather on Telegram)
BOT_TOKEN="YOUR_NEW_BOT_TOKEN_HERE"
# Database Credentials (after installing PostgreSQL 18 and starting your own server)
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="name_db_telegram_bot"
DB_USER="your_user_db"
DB_PASSWORD="your_password_db"

