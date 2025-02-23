import logging
from telegram import Update
from telegram.ext import ContextTypes
from bot.states import MAIN_MENU
from bot.keyboards import get_main_menu_keyboard
from database.db import Database

logger = logging.getLogger(__name__)
db = Database()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обработчик команды /start.
    Если пользователь уже зарегистрирован, показывает главное меню.
    Если нет – автоматически инициирует процесс регистрации.
    """
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if user:
        await update.message.reply_text(
            f"Добро пожаловать, {user.get('first_name', 'Пользователь')}!",
            reply_markup=get_main_menu_keyboard()
        )
        return MAIN_MENU
    else:
        await update.message.reply_text(
            "Добро пожаловать! Вы не зарегистрированы. Начинаем регистрацию."
        )
        # Импортируем обработчик регистрации из user.py и сразу его вызываем
        from bot.handlers.user import handle_guest_registration
        return await handle_guest_registration(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обработчик команды /cancel.
    Прерывает текущий диалог и возвращает пользователя в главное меню.
    """
    await update.message.reply_text("Диалог прерван. Для начала заново отправьте /start.")
    return MAIN_MENU
