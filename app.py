import os
import subprocess
import threading
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 VNATUREBOT is running!"

@app.route('/health')
def health():
    return "OK"

def run_bot():
    """Запускаем основной файл бота"""
    subprocess.run(["python", "bot.py"])

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()

    # Flask сервер (для Render)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)