import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackContext
from config import ADMIN_ID
from bot.states import MAIN_MENU
from bot.keyboards import get_main_menu_keyboard
from database.db import Database
from bot.constants import CITIES, TAGS

logger = logging.getLogger(__name__)
db = Database()


async def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    # Если пользователь входит в список администраторов
    if user_id in ADMIN_ID:
        if not user:
            # Создаем нового пользователя-администратора с дефолтными значениями
            db.save_user(user_id, update.effective_user.first_name, "admin")
            # Устанавливаем Москву как город по умолчанию
            db.update_user_city(user_id, CITIES[0])
            # Устанавливаем все теги по умолчанию
            db.update_user_tags(user_id, ",".join(TAGS))
            logger.info(f"Создан новый администратор: id={user_id}, город={CITIES[0]}, теги={TAGS}")
        else:
            # Если пользователь уже существует, просто обновляем его роль
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
