from flask import Flask
import threading
import requests
import time
import os

# Создаём Flask-приложение
app = Flask(__name__)

# Главная страница (Render проверяет, что сервис жив)
@app.route('/')
def index():
    return "VNATUREBOT is alive!"

# Путь для пинга с cron-job.org
@app.route('/ping')
def ping():
    return "pong", 200

# Функция для запуска Telegram-бота в отдельном потоке
def run_bot():
    os.system("python bot.py")

# Функция для периодического пинга Render (дополнительно)
def keep_alive():
    while True:
        try:
            url = os.getenv("RENDER_URL", "https://vnaturebot-2-0.onrender.com")
            requests.get(url)
        except Exception as e:
            print(f"Ping failed: {e}")
        time.sleep(600)  # каждые 10 минут

if __name__ == '__main__':
    # Запускаем бота в отдельном потоке
    threading.Thread(target=run_bot).start()

    # Запускаем фоновый пинг, чтобы Render не «засыпал»
    threading.Thread(target=keep_alive).start()

    # Запускаем Flask-сервер
    app.run(host='0.0.0.0', port=10000)