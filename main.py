import os
import time
import sqlite3
import threading
import requests
import telebot
from datetime import datetime, timedelta

# ========== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID", 0))
YOOMONEY_WALLET = os.environ.get("YOOMONEY_WALLET")
YOOMONEY_TOKEN = os.environ.get("YOOMONEY_TOKEN")   # OAuth-токен для проверки платежей
# =========================================

if not BOT_TOKEN or not OWNER_ID or not YOOMONEY_WALLET or not YOOMONEY_TOKEN:
    print("❌ Ошибка: не все переменные окружения заданы!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# База данных для отслеживания оплат
def init_db():
    conn = sqlite3.connect('payments.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, waiting INTEGER, last_payment_id TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments
                 (payment_id TEXT PRIMARY KEY, user_id INTEGER, amount INTEGER, status TEXT, timestamp TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Генерация расклада через g4f (GPT)
def get_gpt_reading():
    try:
        import g4f
        response = g4f.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Сделай расклад Таро на ближайшее будущее. Напиши 3-5 предложений."}],
        )
        return response
    except Exception as e:
        return f"✨ Карты говорят: в ближайшее время вас ждёт неожиданная удача. Будьте открыты новым возможностям. (Ошибка GPT: {e})"

# Проверка новых платежей через API ЮMoney
def check_payments():
    headers = {"Authorization": f"Bearer {YOOMONEY_TOKEN}"}
    from_ts = int((datetime.now() - timedelta(minutes=15)).timestamp())
    url = f"https://api.yoomoney.ru/v2/operations?type=in&records=20&from={from_ts}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for op in data.get('operations', []):
                if op['status'] == 'success' and op['amount'] == 199:
                    comment = op.get('comment', '')
                    payment_id = op['operation_id']
                    conn = sqlite3.connect('payments.db')
                    c = conn.cursor()
                    c.execute("SELECT * FROM payments WHERE payment_id=?", (payment_id,))
                    if not c.fetchone():
                        # Извлекаем user_id из комментария
                        user_id = None
                        # Ищем число в комментарии
                        import re
                        numbers = re.findall(r'\d+', comment)
                        if numbers:
                            user_id = int(numbers[0])
                        if user_id:
                            c.execute("INSERT INTO payments (payment_id, user_id, amount, status, timestamp) VALUES (?,?,?,?,?)",
                                      (payment_id, user_id, 199, 'succeeded', datetime.now().isoformat()))
                            conn.commit()
                            # Отправляем расклад
                            reading = get_gpt_reading()
                            bot.send_message(user_id, f"🔮 Ваш расклад Таро:\n\n{reading}")
                            bot.send_message(OWNER_ID, f"💰 Платёж от user {user_id} на 199 руб. Расклад отправлен.")
                            # Сбрасываем флаг ожидания, если есть
                            c.execute("UPDATE users SET waiting=0 WHERE user_id=?", (user_id,))
                            conn.commit()
                    conn.close()
    except Exception as e:
        print(f"Ошибка проверки платежей: {e}")

# Фоновый поток проверки (раз в 30 секунд)
def background_worker():
    while True:
        check_payments()
        time.sleep(30)

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('payments.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, waiting) VALUES (?, 1)", (user_id,))
    conn.commit()
    conn.close()
    bot.send_message(user_id,
                     f"✨ Привет! Полный расклад Таро — 199 руб.\n\n"
                     f"Переведите на кошелёк ЮMoney: `{YOOMONEY_WALLET}`\n"
                     f"В комментарии **обязательно** укажите ваш Telegram ID: `{user_id}`\n\n"
                     f"После перевода бот автоматически проверит платёж в течение 1-2 минут и пришлёт расклад.\n"
                     f"Спасибо за доверие! 🔮",
                     parse_mode="Markdown")

@bot.message_handler(commands=['report'])
def report(message):
    if message.from_user.id == OWNER_ID:
        conn = sqlite3.connect('payments.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM payments WHERE status='succeeded'")
        count = c.fetchone()[0]
        bot.send_message(OWNER_ID, f"📊 Статистика:\nПродано раскладов: {count}\nВыручка: {count*199} руб.")
        conn.close()

# Запуск бота и фонового потока
def start_bot():
    print("✅ Бот запущен. Ожидание сообщений...")
    # Удаляем вебхук на всякий случай
    bot.remove_webhook()
    # Запускаем фоновый поток
    threading.Thread(target=background_worker, daemon=True).start()
    # Запускаем polling
    bot.infinity_polling()

if __name__ == "__main__":
    start_bot()
