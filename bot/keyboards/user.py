from telegram import ReplyKeyboardMarkup
from bot.constants import CITIES, TAGS

def get_main_menu_keyboard(role="user"):
    if role == "admin":
        return ReplyKeyboardMarkup([
            ["🏠 Дом Волонтера", "🤖 ИИ Волонтер"],
            ["Модерация"],
            ["Администрация"]
        ], resize_keyboard=True)
    elif role == "moderator":
        return ReplyKeyboardMarkup([
            ["🏠 Дом Волонтера", "🤖 ИИ Волонтер"],
            ["Модерация"]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            ["🏠 Дом Волонтера", "🤖 ИИ Волонтер"]
        ], resize_keyboard=True)

def get_volunteer_dashboard_keyboard():
    return ReplyKeyboardMarkup([
        ["Профиль", "Текущие мероприятия"],
        ["Бонусы", "Ввести код", "Лидерборд"],
        ["Информация", "Выход"]
    ], resize_keyboard=True)

def get_leaderboard_region_keyboard():
    buttons = []
    for city in CITIES:
        buttons.append([city])
    buttons.append(["❌ Отмена"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_profile_menu_keyboard():
    return ReplyKeyboardMarkup(
        [["Изменить имя", "Изменить табельный", "Изменить интересы", "Изменить регион"],
         ["Выход"]],
        resize_keyboard=True
    )

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

def get_city_selection_keyboard(selected_cities=None):
    if selected_cities is None:
        selected_cities = []
    buttons = []
    for city in CITIES:
        text = f"{city} {'✔️' if city in selected_cities else ''}"
        buttons.append([text])
    buttons.append(["❌ Отмена"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_ai_chat_keyboard():
    return ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True)

def get_tag_filter_keyboard_for_region(selected_tag=None):
    buttons = []
    for tag in TAGS:
        text = f"{tag} {'✓' if tag == selected_tag else ''}"
        buttons.append([text])
    buttons.append(["Все мероприятия в этом регионе"])
    buttons.append(["↩️ Назад к выбору региона", "❌ Отмена"])

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)