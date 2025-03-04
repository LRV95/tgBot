import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackContext
from config import ADMIN_ID
from bot.states import ADMIN_MENU, MAIN_MENU
from bot.keyboards import get_main_menu_keyboard
from database import UserModel, EventModel
from bot.constants import CITIES, TAGS

logger = logging.getLogger(__name__)

user_db = UserModel()
event_db = EventModel()

def escape_markdown_v2(text):
    """Экранирует специальные символы для Markdown V2."""
    if not text:
        return ""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in str(text))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /start."""
    user = update.effective_user
    user_record = user_db.get_user(user.id)
    first_name = user.first_name
    telegram_tag = user.username if user.username else ""
    employee_number = None
    role = "admin" if user.id in ADMIN_ID else "user"

    # Если пользователь входит в список администраторов
    if role == "admin":
        if not user_record:
            # Создаем нового пользователя-администратора с дефолтными значениями
            user_db.save_user(id=user.id, first_name=first_name, telegram_tag=telegram_tag, role=role)
            # Устанавливаем город по умолчанию
            user_db.update_user_city(user.id, CITIES[0])
            # Устанавливаем все теги по умолчанию
            user_db.update_user_tags(user.id, ",".join(TAGS))
            logger.info(f"Создан новый администратор: id={user.id}, город={CITIES[0]}, теги={TAGS}")
        else:
            # Если пользователь уже существует, просто обновляем его роль
            user_db.update_user_role(user.id, role)
            logger.info(f"Обновлена роль администратора: id={user.id}, роль={role}")
        
        keyboard = get_main_menu_keyboard(role=role)
        await update.message.reply_text(f"Добро пожаловать, администратор {first_name}!", reply_markup=keyboard)
        logger.info(f"Администратор {first_name} приветствуется в главном меню")
        return MAIN_MENU
    # Если пользователь не администратор
    else:
        # Если пользователь уже существует
        if user_record:
            await update.message.reply_text(
                f"Добро пожаловать, {user_record.get('first_name', 'Пользователь')}!",
                reply_markup=get_main_menu_keyboard()
            )
            
            # Показываем ближайшие мероприятия
            upcoming_events = event_db.get_upcoming_events(limit=3)
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
