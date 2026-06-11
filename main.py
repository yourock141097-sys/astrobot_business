import os
import hashlib
import json
import sqlite3
from flask import Flask, request, jsonify
import telebot
from datetime import datetime

BOT_TOKEN = "8846825715:AAFiEmV3oMgNaOw6K98veE8QFZR70oXpynU"
OWNER_ID = 8281259050
YOOMONEY_SECRET = "ВАШ_СЕКРЕТНЫЙ_КЛЮЧ"  # Вставьте сюда полученный секрет

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

def init_db():
    conn = sqlite3.connect('payments.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS payments
                 (payment_id TEXT PRIMARY KEY, user_id INTEGER, amount INTEGER, 
                  status TEXT, timestamp TEXT, notification_text TEXT)''')
    conn.commit()
    conn.close()
init_db()

@app.route('/webhook/yoomoney', methods=['POST'])
def yoomoney_webhook():
    notification_data = request.form.to_dict()
    print(f"Получены данные: {notification_data}")

    # Проверка подписи (базовая защита)
    notification_type = notification_data.get('notification_type')
    operation_id = notification_data.get('operation_id')
    amount = notification_data.get('amount')
    currency = notification_data.get('currency')
    datetime_info = notification_data.get('datetime')
    sender = notification_data.get('sender')
    codepro = notification_data.get('codepro')
    label = notification_data.get('label')
    sha1_hash = notification_data.get('sha1_hash')
    
    # Проверяем хэш для подтверждения, что уведомление от ЮMoney
    secret = YOOMONEY_SECRET
    check_string = f"{notification_type}&{operation_id}&{amount}&{currency}&{datetime_info}&{sender}&{codepro}&{secret}&{label}"
    calculated_hash = hashlib.sha1(check_string.encode()).hexdigest()
    
    if calculated_hash != sha1_hash:
        return jsonify({"error": "Invalid signature"}), 400

    # Проверяем, что это уведомление о входящем переводе
    if notification_type == "p2p-incoming" and float(amount) == 199.0:
        user_id = None
        # Ищем user_id в label (метке платежа) или в истории
        # Если label заполнен user_id, используем его
        if label and label.isdigit():
            user_id = int(label)
        else:
            # Временно: ищем по комментарию или оповещаем владельца
            bot.send_message(OWNER_ID, f"⚠️ Получен платёж на {amount} руб., но user_id не определён. Данные: {notification_data}")

        if user_id:
            # Сохраняем платёж в БД
            conn = sqlite3.connect('payments.db')
            c = conn.cursor()
            c.execute("INSERT INTO payments (payment_id, user_id, amount, status, timestamp) VALUES (?, ?, ?, ?, ?)",
                      (operation_id, user_id, 199, 'succeeded', datetime.now().isoformat()))
            conn.commit()
            conn.close()
            
            # Отправляем расклад пользователю (функцию get_gpt_reading нужно добавить)
            reading = get_gpt_reading()
            bot.send_message(user_id, f"🔮 Ваш расклад Таро:\n\n{reading}")
            bot.send_message(OWNER_ID, f"💰 Платёж от user {user_id} на 199 руб. Расклад отправлен.")
    
    return jsonify({"status": "ok"}), 200

def get_gpt_reading():
    # Здесь ваш код для генерации расклада через GPT
    return "✨ Карты говорят: в ближайшее время вас ждёт неожиданная удача."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
