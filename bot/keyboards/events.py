from telegram import ReplyKeyboardMarkup
from bot.constants import TAGS
from bot.constants import CITIES

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
    buttons.append(["🔍 Регионы", "❌ Выход"])

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_events_filter_keyboard(selected_tag=None):
    """Создает клавиатуру для фильтрации мероприятий по тегам."""
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

def get_events_city_filter_keyboard(selected_city=None):
    buttons = []
    for city in CITIES:
        text = f"{city} {'✓' if city == selected_city else ''}"
        buttons.append([text])
    buttons.append(["❌ Отмена"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)