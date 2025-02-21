"""Состояния для ConversationHandler бота."""

# Основные состояния диалога
MAIN_MENU = 0
WAIT_FOR_CSV = 1
AI_CHAT = 2
VOLUNTEER_HOME = 3
PROFILE_MENU = GUEST_HOME = 4
GUEST_REGISTRATION = 5
PROFILE_MENU = 6
WAIT_FOR_PROFILE_UPDATE = 7         # для обновления контактной информации
GUEST_TAG_SELECTION = 8             # для выбора тегов при регистрации
PROFILE_TAG_SELECTION = 9           # для изменения тегов при обновлении профиля
PROFILE_UPDATE_SELECTION = 10       # выбор, что обновлять: контакты или теги
WAIT_FOR_EVENTS_CSV = 11            # новое состояние для загрузки CSV с мероприятиями
