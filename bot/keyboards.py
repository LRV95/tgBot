"""Клавиатуры для бота."""

from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard(role="user"):
    """Возвращает основную клавиатуру в зависимости от роли пользователя."""
    if role == "admin":
        return ReplyKeyboardMarkup([["🏠 Дом Волонтера", "🤖 ИИ Волонтера"],
                                  ["/load_excel", "/set_admin", "/set_moderator"],
                                  ["/delete_user", "/find_user_id"],
                                  ["/find_users_name", "/find_users_email", "/load_csv", "/load_events_csv"]],
                                 resize_keyboard=True)
    elif role == "moderator":
        return ReplyKeyboardMarkup([["🏠 Дом Волонтера", "🤖 ИИ Волонтера"],
                                  ["/delete_user", "/find_user_id"],
                                  ["/load_csv", "/load_events_csv"]],
                                 resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([["🏠 Дом Волонтера", "🤖 ИИ Волонтера", "Мероприятия"]],
                                 resize_keyboard=True)

def get_volunteer_home_keyboard():
    """Возвращает клавиатуру домашнего экрана волонтера."""
    return ReplyKeyboardMarkup([["Профиль", "Текущие мероприятия"],
                              ["Бонусы", "Информация", "Выход."]],
                             resize_keyboard=True)

def get_profile_menu_keyboard():
    """Возвращает клавиатуру меню профиля."""
    return ReplyKeyboardMarkup([["Информация", "Изменить информацию", "Выход"]],
                             resize_keyboard=True)


from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_tag_selection_keyboard(selected_tags=None):
    """Возвращает inline-клавиатуру выбора тегов с отметкой выбранных тегов."""
    if selected_tags is None:
        selected_tags = []

    # Список доступных тегов
    tags = ["социальное", "медицина", "экология", "культура", "спорт"]

    # Создаем кнопки с отметками для выбранных тегов
    buttons = []
    for tag in tags:
        text = f"{tag} {'✓' if tag in selected_tags else ''}"
        buttons.append(InlineKeyboardButton(text, callback_data=f"tag:{tag}"))

    # Разбиваем кнопки по строкам (например, по 2 кнопки в строке)
    keyboard = []
    keyboard.append(buttons[:2])
    keyboard.append(buttons[2:4])
    keyboard.append([buttons[4]])
    # Кнопка "Готово"
    keyboard.append([InlineKeyboardButton("Готово", callback_data="done")])

    return InlineKeyboardMarkup(keyboard)


def get_city_selection_keyboard(selected_cities=None, page=0, page_size=2):
    """Возвращает inline клавиатуру для выбора городов."""
    if selected_cities is None:
        selected_cities = []

    CITIES = ["СПБ", "Москва", "Владивосток", "Казань"]

    total_pages = (len(CITIES) + page_size - 1) // page_size
    start = page * page_size
    end = start + page_size
    cities_on_page = CITIES[start:end]

    buttons = []
    for city in cities_on_page:
        text = f"{city} {'✓' if city in selected_cities else ''}"
        buttons.append(InlineKeyboardButton(text, callback_data=f"city:{city}"))

    navigation = []
    if page > 0:
        navigation.append(InlineKeyboardButton("<<", callback_data=f"city_prev:{page}"))
    if page < total_pages - 1:
        navigation.append(InlineKeyboardButton(">>", callback_data=f"city_next:{page}"))

    keyboard = []
    if buttons:
        keyboard.append(buttons)
    if navigation:
        keyboard.append(navigation)
    keyboard.append([InlineKeyboardButton("Готово", callback_data="done_cities")])

    return InlineKeyboardMarkup(keyboard)

def get_events_keyboard(events, page=0, page_size=5, total_count=0):
    """
    Возвращает inline‑клавиатуру для списка мероприятий.
    Каждая кнопка позволяет зарегистрироваться на мероприятие.
    """
    buttons = []
    for event in events:
        # Извлекаем название мероприятия из tags, если возможно
        name = ""
        if event.get("tags"):
            parts = event["tags"].split(";")
            for part in parts:
                if "Название:" in part:
                    name = part.split("Название:")[1].strip()
                    break
        if not name:
            name = f"Мероприятие #{event['id']}"
        text = f"{name} ({event['event_date']} {event['start_time']})"
        buttons.append(InlineKeyboardButton(text, callback_data=f"register_event:{event['id']}"))

    keyboard = [[btn] for btn in buttons]

    # Навигация по страницам
    total_pages = (total_count + page_size - 1) // page_size
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("<<", callback_data=f"events_prev:{page}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(">>", callback_data=f"events_next:{page}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    # Кнопка возврата в главное меню
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])

    return InlineKeyboardMarkup(keyboard)
