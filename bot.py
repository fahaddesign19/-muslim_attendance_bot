import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# Logging qindeessuu
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token Bot-ichaa fi Admin Username
TOKEN = "8705327940:AAGwg5zyZj2TSrmjPmuEalxzLz_0-ziAT3w"
ADMIN_USERNAME = "fahad_demha"

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    
    # Table hojiilee (Tasks)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            task_type TEXT NOT NULL,
            target_count TEXT,
            schedule_info TEXT
        )
    """)
    
    # Table galmee (Check-ins)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            task_id INTEGER,
            status TEXT,
            date TEXT
        )
    """)
    
    # Hojiilee bu'uuraa jalqabaa galchuun (Yoo duwwaa ta'e)
    cursor.execute("SELECT COUNT(*) FROM tasks")
    if cursor.fetchone()[0] == 0:
        initial_tasks = [
            ("Fajir", "Daily", "1", "Ganama sa'aa 11:04"),
            ("Zuhur", "Daily", "1", "Waaree booda sa'aa 6:15"),
            ("Asir", "Daily", "1", "Waaree booda sa'aa 9:32"),
            ("Magrib", "Daily", "1", "Galgala sa'aa 12:16"),
            ("Isha", "Daily", "1", "Halkan sa'aa 1:22"),
            ("Zikr: يَا مُقَلِّبَ الْقُلُوبِ ثَبِّتْ قَلْبِي عَلى دِيِنِكَ / يَا مُصَرِّفَ الْقُلُوبِ صَرِّفُ قُلُوبِنَا عَلى طَاعَتِكَ", "Daily", "3", "Ganama 2:00 irraa eegalee"),
            ("Du'aa': أَسْتَغْفِرُ اللَّهَ", "Daily", "100", "Ganama 2:00 irraa eegalee"),
            ("Salawat: اَللَّهُمَّ صَلِّ عَلَى مُحَمَّدٍ وَعَلَى آلِ مُحَمَّدٍ", "Weekly (Friday)", "10", "Ganama 2:00 irraa eegalee")
        ]
        cursor.executemany(
            "INSERT INTO tasks (task_name, task_type, target_count, schedule_info) VALUES (?, ?, ?, ?)", 
            initial_tasks
        )
    
    conn.commit()
    conn.close()

init_db()

# Admin States (Hojiilee dabaluuf)
ADD_TASK_NAME = 1
admin_states = {}

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"Nagayaan dhuftan, {user.first_name}!\n"
        "Garee MUSLIM - Bot Hordoffii Salaataa, Zikrii fi Du'aa'ii.\n\n"
        "Ajajoota jiran:\n"
        "📋 /tasks - Hojiilee har'aa ilaaluuf fi galmeessuuf\n"
        "🏆 /leaderboard - Qabxii waligalaa ilaaluuf\n"
        "⚙️ /admin - Hojiilee dabaluuf (Admin qofaaf)"
    )
    await update.message.reply_text(welcome_text)

async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, task_name, target_count, schedule_info FROM tasks")
    tasks = cursor.fetchall()
    conn.close()

    if not tasks:
        await update.message.reply_text("Hojiileen amma galmeeffaman hin jiran.")
        return

    keyboard = []
    for task_id, task_name, target, s_time in tasks:
        btn_text = f"✅ {task_name} (Baay'ina: {target})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"done_{task_id}")])
    
    keyboard.append([InlineKeyboardButton("📊 Qabxii Ilaali", callback_data="show_leaderboard")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("Hojiilee raawwattan as tuquun galmeessaa:", reply_markup=reply_markup)

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT username, COUNT(*) as score 
        FROM checkins 
        GROUP BY user_id 
        ORDER BY score DESC
    """)
    results = cursor.fetchall()
    conn.close()

    text = "🏆 **Qabxii Waliigalaa (Leaderboard)** 🏆\n\n"
    if not results:
        text += "Hanga ammaatti namni galmeesse hin jiru."
    else:
        for idx, (uname, score) in enumerate(results, 1):
            text += f"{idx}. @{uname or 'Maqaa_hinqabu'} - Qabxii: {score}\n"

    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, parse_mode="Markdown")

# --- ADMIN PANEL ---
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.username != ADMIN_USERNAME:
        await update.message.reply_text("Hayyamni ajaja kanaa Admin (@fahad_demha) qofaaf kenname.")
        return

    keyboard = [
        [InlineKeyboardButton("➕ Hojiin Haaraa Dabali", callback_data="admin_add_task")],
        [InlineKeyboardButton("🗑 Hojiilee Haquu", callback_data="admin_delete_task")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Sajoo Admin (Admin Panel):", reply_markup=reply_markup)

# --- CALLBACK QUERY HANDLER ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    if data.startswith("done_"):
        task_id = int(data.split("_")[1])
        today = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM checkins WHERE user_id = ? AND task_id = ? AND date = ?", 
                       (user.id, task_id, today))
        existing = cursor.fetchone()

        if existing:
            await query.message.reply_text(f"@{user.username or user.first_name}, hojiin kun guyyaa har'aa galmeeffameera!")
        else:
            cursor.execute("INSERT INTO checkins (user_id, username, task_id, status, date) VALUES (?, ?, ?, ?, ?)",
                           (user.id, user.username or user.first_name, task_id, "Approved", today))
            conn.commit()
            await query.message.reply_text(f"Galatoomaa! @{user.username or user.first_name}, hojiin kee milkaa'inaan galmeeffameera.")
        conn.close()

    elif data == "show_leaderboard":
        await leaderboard_command(update, context)

    elif data == "admin_add_task":
        if user.username != ADMIN_USERNAME:
            return
        admin_states[user.id] = ADD_TASK_NAME
        await query.message.reply_text("Maqaa hojiichaa haaraa barreessaa ergaa:")

    elif data == "admin_delete_task":
        if user.username != ADMIN_USERNAME:
            return
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, task_name FROM tasks")
        tasks = cursor.fetchall()
        conn.close()

        if not tasks:
            await query.message.reply_text("Hojiin haqamu jiru hin jiru.")
            return

        keyboard = [[InlineKeyboardButton(f"❌ Haqi: {tname}", callback_data=f"del_{tid}")] for tid, tname in tasks]
        await query.message.reply_text("Hojii haqamuu qabu filadhaa:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("del_"):
        if user.username != ADMIN_USERNAME:
            return
        tid = int(data.split("_")[1])
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (tid,))
        conn.commit()
        conn.close()
        await query.message.reply_text("Hojiin sun milkaa'inaan haqameera!")

# --- TEXT HANDLER FOR WIZARD ---
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.username != ADMIN_USERNAME:
        return

    state = admin_states.get(user.id)
    text = update.message.text

    if state == ADD_TASK_NAME:
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (task_name, task_type, target_count, schedule_info) VALUES (?, ?, ?, ?)", 
                       (text, "Daily", "1", "Yeroo hundaa"))
        conn.commit()
        conn.close()

        del admin_states[user.id]
        await update.message.reply_text(f"Hojiin haaraan '{text}' milkaa'inaan dabaleera! 🎉")

# --- MAIN FUNCTION ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tasks", tasks_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    app.add_handler(CommandHandler("admin", admin_command))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), text_handler))

    print("Bot-ichi @MUSLIM hojjechaa jira...")
    app.run_polling()