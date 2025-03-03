from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from bot.constants import CITIES, TAGS


def get_main_menu_keyboard(role="user"):
    if role == "admin":
        return ReplyKeyboardMarkup([
            ["🏠 Дом Волонтера", "🤖 ИИ Волонтера"],
            ["Модерация"],
            ["/load_excel", "/set_admin", "/set_moderator"],
            ["/delete_user", "/find_user_id"],
            ["/find_users_name", "/find_users_email", "/load_projects_csv", "/load_events_csv"]
        ], resize_keyboard=True)
    elif role == "moderator":
        return ReplyKeyboardMarkup([
            ["🏠 Дом Волонтера", "🤖 ИИ Волонтера"],
            ["Модерация"],
            ["/delete_user", "/find_user_id"],
            ["/load_projects_csv", "/load_events_csv"]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            ["🏠 Дом Волонтера", "🤖 ИИ Волонтера", "Мероприятия"]
        ], resize_keyboard=True)


def get_volunteer_home_keyboard():
    return ReplyKeyboardMarkup([
        ["Профиль", "Текущие мероприятия"],
        ["Бонусы", "Ввести код", "Информация"],
        ["Выход"]
    ], resize_keyboard=True)


def get_profile_menu_keyboard():
    return ReplyKeyboardMarkup([["Изменить имя", "Изменить интересы", "Изменить город"], ["Выход"]],
                               resize_keyboard=True)


def get_tag_selection_keyboard(selected_tags=None):
    if selected_tags is None:
        selected_tags = []
    buttons = []
    # Добавляем кнопки для каждого тега
    for tag in TAGS:
        text = f"{tag} {'✓' if tag in selected_tags else ''}"
        buttons.append([text])
    
    # Добавляем кнопку "Готово" и "Отмена"
    buttons.append(["✅ Готово", "❌ Отмена"])
    
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def get_city_selection_keyboard(selected_cities=None, page=0, page_size=3):
    if selected_cities is None:
        selected_cities = []
    buttons = []
    start_idx = page * page_size
    end_idx = start_idx + page_size
    cities_slice = CITIES[start_idx:end_idx]

    # Добавляем кнопки для каждого города
    for city in cities_slice:
        text = f"{city} {'✔️' if city in selected_cities else ''}"
        buttons.append([text])

    # Добавляем навигационные кнопки
    nav_buttons = []
    if page > 0:
        nav_buttons.append("⬅️ Назад")
    if end_idx < len(CITIES):
        nav_buttons.append("Вперед ➡️")
    if nav_buttons:
        buttons.append(nav_buttons)

    # Добавляем кнопку отмены
    buttons.append(["❌ Отмена"])

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_events_keyboard(events, page=0, page_size=4, total_count=0, registered_events=None):
    if registered_events is None:
        registered_events = []
    buttons = []
    
    # Добавляем кнопки для каждого мероприятия
    for event in events:
        name = event.get("name")
        # Добавляем статус регистрации к названию
        text = f"✨ {name}"
        if str(event['id']) in registered_events:
            text += " ✅"
        buttons.append([text])

    # Добавляем кнопки навигации на отдельной строке
    nav_buttons = []
    if page > 0:
        nav_buttons.append("⬅️ Назад")
    if page < (total_count + page_size - 1) // page_size - 1:
        nav_buttons.append("Вперед ➡️")
    if nav_buttons:
        buttons.append(nav_buttons)

    # Добавляем фильтры и выход на последней строке
    buttons.append(["🔍 Фильтры", "❌ Выход"])

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_events_filter_keyboard(selected_tag=None):
    """Создает клавиатуру для фильтрации мероприятий по тегам."""
    from bot.constants import TAGS

    buttons = []
    # Добавляем кнопки для каждого тега
    for tag in TAGS:
        text = f"{tag} {'✓' if tag == selected_tag else ''}"
        buttons.append([text])

    # Добавляем кнопку "Все мероприятия"
    buttons.append(["Все мероприятия"])
    buttons.append(["❌ Отмена"])

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def get_event_details_keyboard(event_id, is_registered=False):
    """Создает клавиатуру для детального просмотра мероприятия."""
    buttons = []

    # Кнопка регистрации/отмены регистрации
    if is_registered:
        buttons.append(["❌ Отменить регистрацию"])
    else:
        buttons.append(["✅ Зарегистрироваться"])

    buttons.append(["⬅️ Назад к списку"])
    buttons.append(["❌ Выход"])

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def get_ai_chat_keyboard():
    return ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True)


def get_moderation_menu_keyboard():
    return ReplyKeyboardMarkup([
        ["Создать мероприятие", "Просмотреть мероприятия"],
        ["Удалить мероприятие", "Найти пользователей"],
        ["Список мероприятий", "Вернуться в главное меню"]
    ], resize_keyboard=True)
