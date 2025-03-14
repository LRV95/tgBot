# Основные состояния (0-9)
MAIN_MENU = 0                  # Главное меню бота
AI_CHAT = 1                    # Диалог с ИИ-ассистентом
VOLUNTEER_DASHBOARD = 2        # Личный кабинет волонтера
GUEST_DASHBOARD = 3            # Интерфейс для незарегистрированных пользователей

# Состояния регистрации и профиля (10-19)
PROFILE_MENU = 10              # Меню управления профилем
PROFILE_UPDATE_NAME = 11       # Изменение имени пользователя
PROFILE_EMPLOYEE_NUMBER = 12   # Ввод табельного номера сотрудника
PROFILE_TAG_SELECT = 13        # Выбор интересов в профиле
PROFILE_CITY_SELECT = 14       # Выбор региона в профиле
REGISTRATION_TAG_SELECT = 15   # Выбор интересов при регистрации
REGISTRATION_CITY_SELECT = 16  # Выбор региона при регистрации

# Состояния для работы с мероприятиями (20-29)
EVENT_DETAILS = 20            # Просмотр деталей мероприятия
EVENT_CODE_REDEEM = 21        # Ввод кода подтверждения участия
EVENT_CSV_IMPORT = 22         # Обработка импорта CSV с мероприятиями
EVENT_CSV_UPLOAD = 23         # Загрузка CSV файла с мероприятиями

# Состояния администратора (30-39)
ADMIN_MENU = 30               # Меню администратора
ADMIN_SET_ADMIN = 31          # Назначение нового администратора
ADMIN_SET_MODERATOR = 32      # Назначение нового модератора
ADMIN_DELETE_USER = 33        # Удаление пользователя из системы
ADMIN_FIND_USER_ID = 34       # Поиск пользователя по ID
ADMIN_FIND_USER_NAME = 35     # Поиск пользователя по имени

# Состояния модерации мероприятий (40-59)
MOD_MENU = 40                 # Меню модератора
MOD_EVENT_NAME = 41           # Ввод названия мероприятия
MOD_EVENT_DATE = 42           # Ввод даты мероприятия
MOD_EVENT_TIME = 43           # Ввод времени мероприятия
MOD_EVENT_CITY = 44           # Выбор региона проведения
MOD_EVENT_CREATOR = 45        # Указание организатора
MOD_EVENT_DESCRIPTION = 46    # Ввод описания мероприятия
MOD_EVENT_POINTS = 47         # Установка баллов за участие
MOD_EVENT_TAGS = 48           # Выбор тегов мероприятия
MOD_EVENT_CODE = 49           # Установка кода подтверждения
MOD_EVENT_CONFIRM = 50        # Подтверждение создания мероприятия
MOD_EVENT_USERS = 51          # Просмотр списка участников
MOD_EVENT_DELETE = 52         # Добавляем новое состояние для удаления мероприятия
CSV_EXPORT_MENU = 53          # Для модераторского меню

# Состояния для работы с отчетами (60-69)
EVENT_REPORT_CREATE = 60       # Создание отчета о мероприятии
EVENT_REPORT_PARTICIPANTS = 61 # Ввод количества участников
EVENT_REPORT_PHOTOS = 62       # Добавление ссылок на фотографии
EVENT_REPORT_SUMMARY = 63      # Ввод краткого описания итогов
EVENT_REPORT_FEEDBACK = 64     # Ввод отзывов участников

PASSWORD_CHECK = 100          # Хардкод пароль