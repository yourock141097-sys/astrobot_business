import os
import hashlib
import sqlite3
import threading
import re
from datetime import datetime
from flask import Flask, request, jsonify
import telebot

# ========== ВАШИ ДАННЫЕ (уже вставлены) ==========
BOT_TOKEN = "8846825715:AAFiEmV3oMgNaOw6K98veE8QFZR70oXpynU"
OWNER_ID = 8281259050
YOOMONEY_WALLET = "4100119544367845"
YOOMONEY_SECRET = "4773pMdCn7OykLHjybpEMu3y"
# =================================================

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ----- Инициализация базы данных -----
def init_db():
    conn = sqlite3.connect('payments.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS payments
                 (payment_id TEXT PRIMARY KEY, user_id INTEGER, amount INTEGER, status TEXT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, last_payment_id TEXT)''')
    conn.commit()
    conn.close()
init_db()

# ----- Генерация расклада через GPT (g4f) -----
def get_gpt_reading(user_question="Сделайте развернутый расклад Таро на ближайшее будущее. Напишите 5-7 предложений."):
    try:
        import g4f
        response = g4f.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": user_question}],
        )
        return response
    except Exception as e:
        # Запасной вариант, если GPT недоступен
        return (f"✨ Карты Таро говорят: в ближайшее время вас ждёт неожиданная удача в финансовых делах. "
                f"Постарайтесь не упустить возможность, которая появится в ближайшие три дня. "
                f"Будьте внимательны к знакам судьбы. (Ошибка GPT: {e})")

# ----- Обработчик вебхука от ЮMoney -----
@app.route('/webhook', methods=['POST'])
def yoomoney_webhook():
    data = request.form.to_dict()
    print(f"Webhook received: {data}")  # для логов

    # Проверяем подпись
    notification_type = data.get('notification_type')
    operation_id = data.get('operation_id')
    amount = data.get('amount')
    currency = data.get('currency')
    datetime_info = data.get('datetime')
    sender = data.get('sender')
    codepro = data.get('codepro')
    label = data.get('label')
    sha1_hash = data.get('sha1_hash')

    check_string = f"{notification_type}&{operation_id}&{amount}&{currency}&{datetime_info}&{sender}&{codepro}&{YOOMONEY_SECRET}&{label}"
    calc_hash = hashlib.sha1(check_string.encode()).hexdigest()

    if calc_hash != sha1_hash:
        print("Invalid signature")
        return jsonify({"error": "Invalid signature"}), 400

    # Обрабатываем только успешные входящие переводы ровно на 199 руб.
    if notification_type == "p2p-incoming" and float(amount) == 199.0:
        # Ищем user_id: сначала в label, потом в комментарии
        user_id = None
        if label and label.isdigit():
            user_id = int(label)
        else:
            comment = data.get('comment', '')
            numbers = re.findall(r'\d+', comment)
            if numbers:
                user_id = int(numbers[0])

        if user_id:
            conn = sqlite3.connect('payments.db')
            c = conn.cursor()
            # Проверяем, не был ли уже обработан этот платёж
            c.execute("SELECT * FROM payments WHERE payment_id=?", (operation_id,))
            if not c.fetchone():
                c.execute("INSERT INTO payments (payment_id, user_id, amount, status, timestamp) VALUES (?,?,?,?,?)",
                          (operation_id, user_id, 199, 'succeeded', datetime.now().isoformat()))
                conn.commit()
                # Генерируем расклад через GPT
                reading = get_gpt_reading()
                # Отправляем пользователю
                try:
                    bot.send_message(user_id, f"🔮 *Ваш персональный расклад Таро:*\n\n{reading}", parse_mode="Markdown")
                except Exception as e:
                    print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
                # Уведомляем владельца
                bot.send_message(OWNER_ID, f"💰 *Успешный платёж!*\nПользователь: {user_id}\nСумма: 199 руб.\nРасклад отправлен.")
            conn.close()
        else:
            bot.send_message(OWNER_ID, f"⚠️ Получен платёж на 199 руб., но не удалось определить user_id. Данные: {data}")

    return jsonify({"status": "ok"}), 200

# ----- Команды Telegram-бота -----
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    bot.send_message(user_id,
                     f"✨ *Добро пожаловать в Астробот!* ✨\n\n"
                     f"Я создан на основе искусственного интеллекта и провожу глубокий расклад Таро.\n\n"
                     f"💎 *Стоимость полного расклада:* 199 рублей.\n\n"
                     f"Как получить прогноз:\n"
                     f"1. Переведите 199 руб на кошелёк ЮMoney:\n`{YOOMONEY_WALLET}`\n"
                     f"2. В комментарии к переводу *обязательно укажите ваш Telegram ID*: `{user_id}`\n"
                     f"3. После зачисления денег (обычно 5-30 секунд) я автоматически пришлю вам уникальный расклад, сгенерированный нейросетью.\n\n"
                     f"🔮 *Никаких скрытых подписок, никакого спама.* Только точный прогноз.\n\n"
                     f"Спасибо за доверие!",
                     parse_mode="Markdown")

@bot.message_handler(commands=['report'])
def report(message):
    if message.from_user.id == OWNER_ID:
        conn = sqlite3.connect('payments.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM payments WHERE status='succeeded'")
        count = c.fetchone()[0]
        total = count * 199
        bot.send_message(OWNER_ID,
                         f"📊 *Отчёт по продажам*\n\n"
                         f"✅ Продано раскладов: {count}\n"
                         f"💰 Выручка: {total} руб.\n"
                         f"📅 Последнее обновление: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                         parse_mode="Markdown")
        conn.close()
    else:
        bot.send_message(message.from_user.id, "❌ Недостаточно прав.")

# ----- Запуск Flask и бота в одном процессе -----
if __name__ == "__main__":
    # Удаляем старый вебхук Telegram, чтобы работал polling
    bot.remove_webhook()
    # Запускаем polling в отдельном потоке
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    print("✅ Бот запущен и ждёт команды /start")
    # Запускаем Flask-сервер для приёма вебхуков от ЮMoney
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
