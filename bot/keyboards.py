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
    return ReplyKeyboardMarkup([["Изменить информацию", "Выход"]],
                               resize_keyboard=True)

def get_tag_selection_keyboard(selected_tags=None):
    if selected_tags is None:
        selected_tags = []
    buttons = []
    for tag in TAGS:
        text = f"{tag} {'✓' if tag in selected_tags else ''}"
        buttons.append(InlineKeyboardButton(text, callback_data=f"tag:{tag}"))
    keyboard = []
    # Разбиваем кнопки по 2 в ряд
    for i in range(0, len(buttons), 2):
        keyboard.append(buttons[i:i + 2])
    keyboard.append([InlineKeyboardButton("Готово", callback_data="done_tags")])
    return InlineKeyboardMarkup(keyboard)

def get_city_selection_keyboard(selected_cities=None, page=0, page_size=3):
    if selected_cities is None:
        selected_cities = []
    buttons = []
    start_idx = page * page_size
    end_idx = start_idx + page_size
    cities_slice = CITIES[start_idx:end_idx]
    
    for city in cities_slice:
        text = f"{city} {'✔️' if city in selected_cities else ''}"
        buttons.append(InlineKeyboardButton(text, callback_data=f"city:{city}"))
    
    keyboard = []
    # Разбиваем кнопки по одной в ряд для лучшей читаемости
    for button in buttons:
        keyboard.append([button])
    
    # Добавляем кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"city_prev:{page}"))
    if end_idx < len(CITIES):
        nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"city_next:{page}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Добавляем кнопку "Готово"
    keyboard.append([InlineKeyboardButton("Готово", callback_data="done_cities")])
    
    return InlineKeyboardMarkup(keyboard)

def get_events_keyboard(events, page=0, page_size=2, total_count=0, registered_events=None):
    if registered_events is None:
        registered_events = []
    buttons = []
    for event in events:
        name = ""
        if event.get("tags"):
            parts = event["tags"].split(";")
            for part in parts:
                if "Название:" in part:
                    name = part.split("Название:")[1].strip()
                    break
        if not name:
            name = f"Мероприятие #{event['id']}"
        
        # Название мероприятия на отдельной кнопке - всегда ведет к просмотру деталей
        text = f"✨ {name}"
        if str(event['id']) in registered_events:
            text += " ✅"
        buttons.append([InlineKeyboardButton(text, callback_data=f"view_event:{event['id']}")])
        
        # Время на отдельной кнопке - всегда ведет к просмотру деталей
        time_text = f"🕒 {event['event_date']} {event['start_time']}"
        buttons.append([InlineKeyboardButton(time_text, callback_data=f"view_event:{event['id']}")])
        
        # Место на отдельной кнопке - всегда ведет к просмотру деталей
        location_text = f"📍 {event['city']}"
        buttons.append([InlineKeyboardButton(location_text, callback_data=f"view_event:{event['id']}")])
        
        # Кнопка регистрации или отмены регистрации
        if str(event['id']) in registered_events:
            buttons.append([InlineKeyboardButton("❌ Отменить регистрацию", callback_data=f"unregister_event:{event['id']}")])
        else:
            buttons.append([InlineKeyboardButton("✅ Зарегистрироваться", callback_data=f"register_event:{event['id']}")])
    
    keyboard = buttons
    total_pages = (total_count + page_size - 1) // page_size
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("<<", callback_data=f"events_prev:{page}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(">>", callback_data=f"events_next:{page}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Добавляем кнопку фильтров
    keyboard.append([InlineKeyboardButton("🔍 Фильтры", callback_data="show_filters")])
    
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_events_filter_keyboard(selected_tag=None):
    """Создает клавиатуру для фильтрации мероприятий по тегам."""
    from bot.constants import TAGS
    
    keyboard = []
    # Добавляем кнопки для каждого тега
    for tag in TAGS:
        text = f"{tag} {'✓' if tag == selected_tag else ''}"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"filter_tag:{tag}")])
    
    # Добавляем кнопку "Все мероприятия"
    keyboard.append([InlineKeyboardButton("Все мероприятия", callback_data="filter_tag:all")])
    
    # Добавляем кнопку возврата
    keyboard.append([InlineKeyboardButton("Назад к списку", callback_data="back_to_events")])
    
    return InlineKeyboardMarkup(keyboard)

def get_profile_update_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Имя", callback_data="update:name"), InlineKeyboardButton("Интересы", callback_data="update:tags")],
        [InlineKeyboardButton("Город", callback_data="update:city")],
        [InlineKeyboardButton("❌ Отмена", callback_data="update:cancel")]
    ])

def get_event_details_keyboard(event_id, is_registered=False):
    """Создает клавиатуру для детального просмотра мероприятия."""
    keyboard = []
    
    # Кнопка регистрации/отмены регистрации
    if is_registered:
        keyboard.append([InlineKeyboardButton("❌ Отменить регистрацию", callback_data=f"unregister_event:{event_id}")])
    else:
        keyboard.append([InlineKeyboardButton("✅ Зарегистрироваться", callback_data=f"register_event:{event_id}")])
    
    # Кнопка для того, чтобы поделиться мероприятием
    keyboard.append([InlineKeyboardButton("📤 Поделиться", callback_data=f"share_event:{event_id}")])
    
    # Кнопка возврата к списку мероприятий
    keyboard.append([InlineKeyboardButton("🔙 Назад к списку", callback_data="back_to_events")])
    
    return InlineKeyboardMarkup(keyboard)

def get_ai_chat_keyboard():
    return ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True)

def get_moderation_menu_keyboard():
    return ReplyKeyboardMarkup([
        ["Создать мероприятие", "Просмотреть мероприятия"],
        ["Удалить мероприятие", "Найти пользователей"],
        ["Список мероприятий", "Вернуться в главное меню"]
    ], resize_keyboard=True)

