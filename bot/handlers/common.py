import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackContext
from config import ADMIN_ID
from bot.states import ADMIN_MENU, MAIN_MENU
from bot.keyboards import get_main_menu_keyboard
from database.db import Database
from bot.constants import CITIES, TAGS

logger = logging.getLogger(__name__)
db = Database()

def escape_markdown_v2(text):
    """Экранирует специальные символы для Markdown V2."""
    if not text:
        return ""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in str(text))

async def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    first_name = update.effective_user.first_name
    telegram_tag = update.effective_user.username if update.effective_user.username else ""
    employee_number = None
    role = "admin" if user_id in ADMIN_ID else "user"

    # Если пользователь входит в список администраторов
    if role == "admin":
        if not user:
            # Создаем нового пользователя-администратора с дефолтными значениями
            db.save_user(id=user_id, first_name=first_name, telegram_tag=telegram_tag, employee_number=employee_number, role=role)
            # Устанавливаем город по умолчанию
            db.update_user_city(user_id, CITIES[0])
            # Устанавливаем все теги по умолчанию
            db.update_user_tags(user_id, ",".join(TAGS))
            logger.info(f"Создан новый администратор: id={user_id}, город={CITIES[0]}, теги={TAGS}")
        else:
            # Если пользователь уже существует, просто обновляем его роль
            db.update_user_role(user_id, role)
        
        keyboard = get_main_menu_keyboard(role=role)
        await update.message.reply_text("Добро пожаловать, администратор!", reply_markup=keyboard)
        return ADMIN_MENU
    # Если пользователь не администратор
    else:
        # Если пользователь уже существует
        if user:
            await update.message.reply_text(
                f"Добро пожаловать, {user.get('first_name', 'Пользователь')}!",
                reply_markup=get_main_menu_keyboard()
            )
            
            # Показываем ближайшие мероприятия
            upcoming_events = db.get_upcoming_events(limit=3)
            if upcoming_events:
                events_text = "📅 *Ближайшие мероприятия:*\n\n"
                for event in upcoming_events:
                    name = event.get("name")
                    
                    # Экранируем специальные символы для Markdown V2
                    name_escaped = escape_markdown_v2(name)
                    city_escaped = escape_markdown_v2(event['city'])
                    date_escaped = escape_markdown_v2(event['event_date'])
                    time_escaped = escape_markdown_v2(event['start_time'])
                    
                    events_text += f"• *{name_escaped}*\n  📆 {date_escaped} в {time_escaped}\n  📍 {city_escaped}\n\n"
                await update.message.reply_markdown_v2(events_text)
            
            return MAIN_MENU
        # Если пользователь не существует
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
