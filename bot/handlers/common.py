import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackContext
from config import ADMIN_ID
from bot.states import MAIN_MENU
from bot.keyboards import get_main_menu_keyboard
from database.db import Database

logger = logging.getLogger(__name__)
db = Database()


async def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    user = db.get_user(user_id)
    # Если пользователь входит в список администраторов, обновляем роль на "admin"
    if user_id in ADMIN_ID:
        db.update_user_role(user_id, "admin")
        keyboard = get_main_menu_keyboard(role="admin")
        await update.message.reply_text("Добро пожаловать, администратор!", reply_markup=keyboard)
        return MAIN_MENU
    else:
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
            from bot.handlers.user import handle_registration
            return await handle_registration(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обработчик команды /cancel.
    Прерывает текущий диалог и возвращает пользователя в главное меню.
    """
    await update.message.reply_text("Диалог прерван. Для начала заново отправьте /start.")
    return MAIN_MENU
