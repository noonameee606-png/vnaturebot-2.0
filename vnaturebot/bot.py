# bot.py
# Основной код бота (адаптирован для запуска как модуль)
# Убедитесь, что ваш .env содержит TELEGRAM_BOT_TOKEN (локально) или Render env var

import os
import time
import asyncio
import logging
import traceback
from collections import defaultdict
from dotenv import load_dotenv

# telegram imports
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatJoinRequest,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    ChatJoinRequestHandler,
)

# ───────────── ЗАГРУЗКА .env ─────────────
load_dotenv()

# ───────────── ЛОГИ ─────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("vnaturebot")

# ───────────── КОНСТАНТЫ / ПЕРЕМЕННЫЕ ─────────────
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set in environment")

# Админ/ID/каналы — подставь свои (мы используем значения, которые обсуждали)
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "8384062951"))
REVIEWS_GROUP_ID = int(os.getenv("REVIEWS_GROUP_ID", "-1002826045128"))
MAIN_CHANNEL_ID = int(os.getenv("MAIN_CHANNEL_ID", "-1003211960449"))
PRIVATE_CHANNEL_ID = int(os.getenv("PRIVATE_CHANNEL_ID", "-1003235414978"))

PRIVATE_CHANNEL_LINK = os.getenv("PRIVATE_CHANNEL_LINK", "https://t.me/+cASc3HVdOb83NzRi")
MAIN_CHANNEL_LINK = os.getenv("MAIN_CHANNEL_LINK", "https://t.me/+cNyLU0-g_CowNDky")
REVIEWS_CHANNEL_LINK = os.getenv("REVIEWS_CHANNEL_LINK", "https://t.me/vnature_reviews")

# Conversation state
REVIEW_TEXT = range(1)

# anti-spam storage (simple)
user_requests = defaultdict(list)

def rate_limit(user_id: int, limit: int = 3, period: int = 60) -> bool:
    now = time.time()
    user_requests[user_id] = [t for t in user_requests[user_id] if now - t < period]
    if len(user_requests[user_id]) >= limit:
        return False
    user_requests[user_id].append(now)
    return True

# ---------- Keyboards ----------
async def get_main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [["📝 Оставить отзыв", "⭐ Посмотреть отзывы"], ["ℹ️ Помощь"]],
        resize_keyboard=True,
    )

async def notify_admin(context: ContextTypes.DEFAULT_TYPE, text: str):
    try:
        await context.bot.send_message(chat_id=ADMIN_USER_ID, text=text)
    except Exception:
        logger.exception("Failed to notify admin")

# ---------- Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        await update.message.reply_text(
            f"Привет, {user.first_name}! 💎\n\n"
            "Добро пожаловать в официальный бот канала VNATUREBABKI!\n\n"
            "Выберите действие:",
            reply_markup=await get_main_menu_keyboard(),
        )
    except Exception as e:
        logger.error("Error in start: %s", e)
        await notify_admin(context, f"❌ Error in start: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Действие отменено.",
        reply_markup=await get_main_menu_keyboard(),
    )
    return ConversationHandler.END

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user

    if not rate_limit(user.id):
        await update.message.reply_text(
            "⚠️ Слишком частые действия. Попробуйте через минуту.",
            reply_markup=await get_main_menu_keyboard(),
        )
        return

    if text == "📝 Оставить отзыв":
        await update.message.reply_text(
            "Поделись своим опытом! 💬\n\n"
            "Напиши отзыв о нашем канале:\n"
            "• Что понравилось больше всего?\n"
            "• Какие результаты получил?\n"
            "• Что можно улучшить?",
            reply_markup=ReplyKeyboardRemove(),
        )
        return REVIEW_TEXT
    elif text == "⭐ Посмотреть отзывы":
        # отправляем сообщение с кнопкой "Смотреть отзывы"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Смотреть отзывы", url=REVIEWS_CHANNEL_LINK)]])
        await update.message.reply_text(
            "📢 Все отзывы публикуются здесь:",
            reply_markup=kb,
        )
        # не отправляем "выберите действие"
    elif text == "ℹ️ Помощь":
        await help_command(update, context)
    else:
        await update.message.reply_text(
            "Выберите действие из меню 👇",
            reply_markup=await get_main_menu_keyboard(),
        )

async def handle_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    if len(text) < 10:
        await update.message.reply_text(
            "❌ Отзыв слишком короткий. Напишите хотя бы 10 символов.",
            reply_markup=await get_main_menu_keyboard(),
        )
        return ConversationHandler.END
    if len(text) > 1000:
        await update.message.reply_text(
            "❌ Отзыв слишком длинный. Максимум 1000 символов.",
            reply_markup=await get_main_menu_keyboard(),
        )
        return ConversationHandler.END

    msg = f"⭐ Новый отзыв ⭐\n\nОт: @{user.username or user.first_name} (ID: {user.id})\n\n{text}"

    try:
        await context.bot.send_message(chat_id=REVIEWS_GROUP_ID, text=msg)
        logger.info("Review sent to group")
        await update.message.reply_text(
            "✅ Спасибо за отзыв! 💬\nАдмин проверяет твой отзыв перед публикацией 🔍",
            reply_markup=await get_main_menu_keyboard(),
        )
    except Exception as e:
        logger.exception("Error sending review to group: %s", e)
        await notify_admin(context, f"❌ Error publishing review:\n{e}\n\n{traceback.format_exc()}")
        await update.message.reply_text(
            "⚠️ Не удалось опубликовать отзыв. Он отправлен администратору вручную.",
            reply_markup=await get_main_menu_keyboard(),
        )
    return ConversationHandler.END

# ---------- Join requests / subscription flow ----------
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request: ChatJoinRequest = update.chat_join_request
    user = request.from_user
    logger.info(f"New join request from {user.id} ({user.username})")

    context.user_data["pending_request"] = {"chat_id": request.chat.id, "user_id": user.id}

    keyboard = [
        [InlineKeyboardButton("📢 Подписаться на приватный канал", url=PRIVATE_CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Я подписался", callback_data="check_sub")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"💎 Привет, {user.first_name}!\n\n"
        "Ты подал заявку на вступление в канал *VNATUREBABKI*.\n\n"
        "Перед одобрением заявки подпишись на наш приватный канал 👇"
    )

    try:
        await context.bot.send_message(chat_id=user.id, text=text, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        logger.exception("Failed to send join-request message: %s", e)

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    # edit message to show checking
    try:
        await query.edit_message_text("⏳ Проверяем подписку...")
    except Exception:
        pass

    await asyncio.sleep(0.6)

    try:
        member = await context.bot.get_chat_member(PRIVATE_CHANNEL_ID, user.id)
        status = member.status
    except Exception as e:
        logger.exception("Error checking subscription: %s", e)
        try:
            await query.edit_message_text("⚠️ Ошибка проверки подписки. Попробуйте позже.")
        except Exception:
            pass
        return

    if status in ("member", "administrator", "creator"):
        try:
            await query.edit_message_text(
                "✅ Отлично, вы подписаны на наш приватный канал! 💎🔥\n\n"
                "Теперь можете продолжить 👇",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Продолжить", callback_data="confirm_join")]]),
            )
        except Exception:
            pass
    else:
        try:
            await query.edit_message_text(
                "❌ Вы ещё не подписались на наш приватный канал!\n"
                "Подпишитесь по ссылке и нажмите «✅ Я подписался».",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("📢 Подписаться", url=PRIVATE_CHANNEL_LINK)],
                        [InlineKeyboardButton("✅ Я подписался", callback_data="check_sub")],
                    ]
                ),
            )
        except Exception:
            pass

async def confirm_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()
    try:
        await query.edit_message_text(
            "Ты сделал главное — теперь очередь за нами!\n"
            "Дождись одобрения и получи доступ к тому, о чём другие только мечтают.\n\n"
            "Скоро всё изменится... 🤫💎"
        )
    except Exception:
        pass

    if "pending_request" in context.user_data:
        data = context.user_data.pop("pending_request")
        chat_id = data["chat_id"]
        user_id = data["user_id"]

        async def approve_later():
            await asyncio.sleep(5)
            try:
                await context.bot.approve_chat_join_request(chat_id, user_id)
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "💎 Ваша заявка одобрена!\nДобро пожаловать в VNATUREBABKI 🎉\n\n"
                        "Нажмите /start, чтобы далее взаимодействовать с ботом 💬"
                    ),
                    reply_markup=await get_main_menu_keyboard(),
                )
            except Exception as e:
                logger.exception("Error approving join request: %s", e)
                await notify_admin(context, f"⚠️ Ошибка автоодобрения: {e}")

        # запускаем задачу для approve_later
        context.application.create_task(approve_later())

# ---------- Other helpers ----------
async def show_reviews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Смотреть отзывы", url=REVIEWS_CHANNEL_LINK)]])
    await update.message.reply_text(
        "📢 Все отзывы публикуются здесь:",
        reply_markup=kb,
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"💎 VNATUREBABKI — официальный бот\n\n"
        f"📢 Основной канал: {MAIN_CHANNEL_LINK}\n"
        f"🔒 Приватный: {PRIVATE_CHANNEL_LINK}\n"
        f"⭐ Отзывы: {REVIEWS_CHANNEL_LINK}\n\n"
        f"📩 По вопросам: @CreatorVnaturebabki",
        reply_markup=await get_main_menu_keyboard(),
    )

# ---------- MAIN ----------
def main() -> None:
    logger.info("Initializing VNATUREBOT...")

    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📝 Оставить отзыв$"), handle_main_menu)],
        states={
            REVIEW_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_review),
                CommandHandler("cancel", cancel),
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # add handlers
    application.add_handler(conv_handler)
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
    application.add_handler(CallbackQueryHandler(check_subscription, pattern="^check_sub$"))
    application.add_handler(CallbackQueryHandler(confirm_join, pattern="^confirm_join$"))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu))

    async def after_startup(app: Application):
        logger.info("VNATUREBOT started")
        try:
            await app.bot.send_message(chat_id=ADMIN_USER_ID, text="🤖 Бот успешно запущен!")
        except Exception:
            logger.debug("Failed to notify admin on startup", exc_info=True)

    application.post_init = after_startup

    logger.info("Starting polling loop")
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True, close_loop=False)
    except Exception as e:
        logger.exception("Critical error in polling: %s", e)
        time.sleep(30)
        main()

if __name__ == "__main__":
    main()