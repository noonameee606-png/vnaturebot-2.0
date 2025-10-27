# -*- coding: utf-8 -*-
import os
import threading
import time
import logging
import asyncio
from flask import Flask, jsonify
import requests

# ───────────── НАСТРОЙКА ЛОГОВ ─────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("app")

# ───────────── FLASK ─────────────
app = Flask(name)

@app.route("/")
def home():
    return jsonify({"status": "online", "service": "VNATUREBOT"})

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

@app.route("/ping")
def ping():
    return "pong"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port)

# ───────────── ФУНКЦИЯ ДЛЯ ЗАПУСКА БОТА ─────────────
def run_bot():
    import bot
    logger.info("Import of bot module successful, starting bot.main() in async loop")

    async def main_async():
        await bot.main_async()  # вызываем асинхронную функцию из bot.py

    asyncio.run(main_async())

# ───────────── АВТО-ПИНГ ─────────────
def auto_ping():
    while True:
        try:
            render_url = os.environ.get("RENDER_URL")
            if render_url:
                requests.get(f"{render_url}/ping", timeout=10)
        except Exception as e:
            logger.warning(f"Ping failed: {e}")
        time.sleep(300)

# ───────────── ЗАПУСК ─────────────
if name == "main":
    logger.info("App initializing...")

    # Flask
    threading.Thread(target=run_flask, daemon=True).start()

    # Авто-пинг
    threading.Thread(target=auto_ping, daemon=True).start()

    # Бот
    run_bot()