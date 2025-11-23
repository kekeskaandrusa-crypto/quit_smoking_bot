import logging
import os
import random
from datetime import datetime, time

import sqlite3
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler, JobQueue
)

# ==================== НАСТРОЙКИ ====================
TOKEN = os.getenv("TOKEN", "8494695438:AAGhWgVDDfXf3eRkxpbOcyYd9Yc956ZPgcU")
# ===================================================

QUIT_DATE, CIGS_PER_DAY, PRICE_PER_PACK, PACK_SIZE = range(4)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================== БАЗА =======================
def init_db():
    conn = sqlite3.connect('quit_smoking.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    quit_date TEXT,
                    cigs_per_day INTEGER,
                    price_per_pack REAL,
                    pack_size INTEGER,
                    reminders INTEGER DEFAULT 1)''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('quit_smoking.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def save_user(user_id, quit_date, cigs, price, pack, reminders=1):
    conn = sqlite3.connect('quit_smoking.db')
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO users 
                 (user_id, quit_date, cigs_per_day, price_per_pack, pack_size, reminders)
                 VALUES (?,?,?,?,?,?)""",
              (user_id, quit_date, cigs, price, pack, reminders))
    conn.commit()
    conn.close()

# ===================== КОМАНДЫ =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if get_user(user_id):
        await show_stats(update, context)
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton("Я бросил курить!", callback_data="setup")]]
    await update.message.reply_text(
        "Привет! Я — твой личный помощник в борьбе с курением\n\n"
        "Я посчитаю:\n"
        "• Сколько сигарет ты НЕ выкурил\n"
        "• Сколько денег и жизни сэкономил\n"
        "• Когда получишь ачивки и вернёшь здоровье\n\n"
        "Нажми кнопку и начнём →",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return QUIT_DATE

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "setup":
        await query.edit_message_text("Когда ты бросил курить?\nНапиши дату ДД.ММ.ГГГГ или «сегодня»")
        return QUIT_DATE
    if query.data == "stats":
        await show_stats(update, context)
    if query.data == "share":
        await share_stats(update, context)
    if query.data == "toggle_reminders":
        await toggle_reminders(update, context)

async def quit_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lower() == "сегодня":
        date = datetime.now().strftime("%d.%m.%Y")
    else:
        try:
            date = datetime.strptime(text, "%d.%m.%Y").strftime("%d.%m.%Y")
        except:
            await update.message.reply_text("Неправильный формат. Пример: 23.11.2025 или «сегодня»")
            return QUIT_DATE
    context.user_data["quit_date"] = date
    await update.message.reply_text("Сколько сигарет в день ты курил в среднем?")
    return CIGS_PER_DAY

async def cigs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        n = int(update.message.text)
        if not 1 <= n <= 200:
            raise ValueError
        context.user_data["cigs"] = n
        await update.message.reply_text("Сколько стоит пачка в евро? (например 7.50)")
        return PRICE_PER_PACK
    except:
        await update.message.reply_text("Напиши число от 1 до 200")
        return CIGS_PER_DAY

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        p = float(update.message.text.replace(",", "."))
        if p <= 0: raise ValueError
        context.user_data["price"] = p
        await update.message.reply_text("Сколько сигарет в пачке? (обычно 20)")
        return PACK_SIZE
    except:
        await update.message.reply_text("Напиши цену правильно (например 7.80)")
        return PRICE_PER_PACK

async def pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ps = int(update.message.text)
        if ps < 1: raise ValueError
        user_id = update.effective_user.id
        save_user(user_id,
                  context.user_data["quit_date"],
                  context.user_data["cigs"],
                  context.user_data["price"],
                  ps)
        await update.message.reply_text("Всё сохранено! Ежедневно в 9:00 буду присылать мотивацию")
        await show_stats(update, context)
        return ConversationHandler.END
    except:
        await update.message.reply_text("Напиши число (например 20)")
        return PACK_SIZE

# ===================== СТАТИСТИКА =====================
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if not update.callback_query else update.callback_query.from_user.id
    data = get_user(user_id)
    if not data:
        text = "Сначала настрой бота — /start"
        if update.callback_query:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    quit_date_str, cigs_day, price_pack, pack_size = data[1], data[2], data[3], data[4]
    quit_date = datetime.strptime(quit_date_str, "%d.%m.%Y").date()
    days = (datetime.now().date() - quit_date).days + 1

    saved_cigs = cigs_day * days
    saved_money = (saved_cigs / pack_size) * price_pack
    saved_minutes = saved_cigs * 11
    saved_days_life = saved_minutes // 1440
    saved_hours_life = (saved_minutes % 1440) // 60

    # Прогресс к году
    progress = min(days / 365, 1.0)
    bar = "█" * int(progress * 10) + "░" * (10 - int(progress * 10))

    # Ачивки
    achievements = []
    if days >= 7: achievements.append("7 дней — неделя свободы!")
    if days >= 30: achievements.append("30 дней — месяц без дыма!")
    if days >= 90: achievements.append("90 дней — лёгкие очищаются!")
    if days >= 365: achievements.append("ГОД БЕЗ СИГАРЕТ! ТЫ ЛЕГЕНДА")

    ach_text = "\n".join(achievements) if achievements else ""

    text = f"""Твоя победа над курением

Бросил: <b>{quit_date_str}</b>
Дней без сигарет: <b>{days}</b> дней

НЕ выкурено: <b>{saved_cigs:,}</b> сигарет
СЭКОНОМИЛ: <b>{saved_money:.2f} €</b>

Вернул жизни: <b>{saved_days_life} дн. {saved_hours_life} ч.</b>

Прогресс к году:\n{bar} <b>{int(progress*100)}%</b>

{ach_text}"""

    keyboard = [
        [InlineKeyboardButton("Обновить", callback_data="stats"),
         InlineKeyboardButton("Поделиться", callback_data="share")],
        [InlineKeyboardButton("Напоминания: ВКЛ", callback_data="toggle_reminders")],
        [InlineKeyboardButton("Сбросить всё", callback_data="reset")]
    ]

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# ===================== ДОПОЛНИТЕЛЬНО =====================
async def share_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_stats(update, context)
    await context.bot.send_message(
        update.effective_chat.id,
        "Моя статистика бросания курить! Кто со мной?"
    )

async def toggle_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    new_state = 0 if user[5] else 1
    conn = sqlite3.connect('quit_smoking.db')
    conn.execute("UPDATE users SET reminders = ? WHERE user_id = ?", (new_state, user_id))
    conn.commit()
    conn.close()
    status = "ВКЛ" if new_state else "ВЫКЛ"
    await query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Обновить", callback_data="stats"),
             InlineKeyboardButton("Поделиться", callback_data="share")],
            [InlineKeyboardButton(f"Напоминания: {status}", callback_data="toggle_reminders")],
            [InlineKeyboardButton("Сбросить всё", callback_data="reset")]
        ])
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    conn = sqlite3.connect('quit_smoking.db')
    conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    await query.edit_message_text("Данные сброшены! Жми /start, чтобы начать заново")

# Ежедневные напоминания
async def daily_motivation(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('quit_smoking.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE reminders = 1")
    users = c.fetchall()
    conn.close()

    for (user_id,) in users:
        try:
            data = get_user(user_id)
            if not data: continue
            quit_date_str = data[1]
            days = (datetime.now().date() - datetime.strptime(quit_date_str, "%d.%m.%Y").date()).days + 1
            motivation = random.choice([
                "Ты уже {days} дней без сигарет! Это победа!",
                "Держись, бро! {days} дней — ты сильнее зависимости!",
                "Каждый день без курева — это +здоровье и +деньги!",
                "Ты крут! Ещё один день в копилку свободы!"
            ]).format(days=days)
            await context.bot.send_message(user_id, motivation)
        except: pass

# ===================== ЗАПУСК =====================
async def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    # Хендлеры
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            QUIT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, quit_date)],
            CIGS_PER_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, cigs)],
            PRICE_PER_PACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, price)],
            PACK_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, pack)],
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("stats", show_stats))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CallbackQueryHandler(button, pattern="^(setup|stats|share|toggle_reminders)$"))
    app.add_handler(CallbackQueryHandler(reset, pattern="^reset$"))

    # Ежедневные напоминания в 9:00
    app.job_queue.run_daily(daily_motivation, time=time(9, 0))

    # Webhook для Render / Railway / Fly.io
    port = int(os.environ.get("PORT", 8443))
    await app.initialize()
    await app.start()
    await app.updater.start_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}{os.environ.get('RENDER_EXTERNAL_URL_PATH', '') or ''}/{TOKEN}" 
                   if os.environ.get("RENDER_EXTERNAL_HOSTNAME") else
                   f"https://{os.environ['RAILWAY_STATIC_URL']}/{TOKEN}" if os.environ.get("RAILWAY_STATIC_URL") else
                   f"https://your-domain.onrender.com/{TOKEN}"  # ← замени при необходимости
    )
    print("Бот запущен через webhook!")
    await app.updater.bot.set_webhook(url=f"https://your-domain.onrender.com/{TOKEN}")  # ← поменяй при деплое
    await asyncio.Event().wait()  # держит бота живым

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
