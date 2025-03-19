from telegram import ReplyKeyboardMarkup

def get_cancel_keyboard():
    """Возвращает клавиатуру с одной кнопкой отмены."""
    return ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True)

def get_confirm_keyboard():
    """Возвращает клавиатуру с кнопками подтверждения."""
    return ReplyKeyboardMarkup([
        ["✅ Да", "❌ Нет"]
    ], resize_keyboard=True) 