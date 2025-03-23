from telegram import ReplyKeyboardMarkup
from bot.constants import CITIES, TAGS

def get_mod_menu_keyboard():
    return ReplyKeyboardMarkup([
        ["Создать мероприятие", "Редактировать мероприятие", "Удалить мероприятие"],
        ["Мои мероприятия", "Все мероприятия"],
        ["Посмотреть участников", "Выгрузить CSV"],
        ["Создать отчет", "Просмотреть отчет"],
        ["Вернуться в главное меню"]
    ], resize_keyboard=True)

def get_csv_export_menu_keyboard():
    return ReplyKeyboardMarkup([
        ["Выгрузка данных пользователя"],
        ["Выгрузка мероприятий"],
        ["Выгрузка отчётов"],
        ["Назад"]
    ], resize_keyboard=True)

def get_admin_menu_keyboard():
    return ReplyKeyboardMarkup([
        ["Установить админа", "Установить модератора"],
        ["Удалить пользователя", "Найти пользователя по ID"],
        ["Найти пользователя по имени", "Загрузить мероприятия из CSV"],
        ["Загрузить проекты из CSV", "Вернуться в главное меню"]
    ], resize_keyboard=True)

def get_city_selection_keyboard_with_cancel():
    """Возвращает клавиатуру выбора города с кнопкой отмены."""
    buttons = []
    for city in CITIES:
        text = f"{city}"
        buttons.append([text])
    buttons.append(["❌ Отмена"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_tag_selection_keyboard_with_cancel(selected_tags=None):
    """Возвращает клавиатуру выбора тегов с кнопками отмены и готово."""
    if selected_tags is None:
        selected_tags = []
    buttons = []
    for tag in TAGS:
        text = f"{tag} {'✔️' if tag in selected_tags else ''}"
        buttons.append([text])
    buttons.extend([["✅ Готово"], ["❌ Отмена"]])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True) 