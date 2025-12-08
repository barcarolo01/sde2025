import sys
from telegram import Update
from telegram.ext import ContextTypes,ContextTypes
from PostgreSQL_DB.db_utilities import connect_db
sys.dont_write_bytecode = True  # Prevent .pyc files generation

async def IsUserAuthorized(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    return True # TEMPORARY
    conn = connect_db()
    cur = conn.cursor()
    user_id = 9999

    # TODO: Once authentication is completed, complete this query
    cur.execute(
        "SELECT user_id, username, role "
        "FROM users WHERE user_id = %s ",
        (user_id)
    )
    rows = cur.fetch()
    user_id_fetched, username, role = rows[0]
    cur.close()
    conn.close()

    return (role == 'admin' or role == 'leader')