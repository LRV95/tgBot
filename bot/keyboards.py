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

def get_tag_selection_keyboard(selected_tags=None):
    """Возвращает клавиатуру выбора тегов."""
    if selected_tags is None:
        selected_tags = []
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("социальное", callback_data="tag:социальное"),
         InlineKeyboardButton("медицина", callback_data="tag:медицина")],
        [InlineKeyboardButton("экология", callback_data="tag:экология"),
         InlineKeyboardButton("культура", callback_data="tag:культура")],
        [InlineKeyboardButton("спорт", callback_data="tag:спорт")],
        [InlineKeyboardButton("Готово", callback_data="done")]
    ])


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
