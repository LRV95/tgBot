# Бот для волонтёрского центра

Телеграм-бот для управления волонтёрской программой

## Структура проекта

```
volunteer-bot/
├── bot/                    # Основной код бота
│   ├── handlers/          # Обработчики команд
│   │   ├── admin.py      # Админские команды
│   │   ├── user.py       # Пользовательские команды
│   │   └── common.py     # Общие команды (start, cancel)
│   ├── keyboards.py      # Клавиатуры для разных меню
│   └── states.py        # Состояния диалога
├── database/             # Работа с базой данных
│   └── db.py           # Класс Database для работы с SQLite
├── services/            # Дополнительные сервисы
│   └── ai_service.py   # Работа с GigaChat API
├── config.py           # Конфигурация бота
└── main.py            # Точка входа в приложение
```

### Описание компонентов

- **bot/handlers/**: Обработчики команд и сообщений
  - `admin.py` - команды администратора (/admin, /set_admin и т.д.)
  - `user.py` - обработка пользовательских действий
  - `common.py` - общие команды (/start, /cancel)
- **bot/keyboards.py**: Все клавиатуры бота (основное меню, меню профиля и т.д.)
- **bot/states.py**: Состояния для ConversationHandler
- **database/db.py**: Взаимодействие с SQLite базой данных
- **services/ai_service.py**: Интеграция с GigaChat для ИИ-функционала
- **config.py**: Настройки бота (токены, ключи API)
- **main.py**: Инициализация и запуск бота

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/volunteer-bot.git
cd volunteer-bot
```

2. Создайте виртуальное окружение:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

3. Установите зависимости:
```bash
# Windows
pip install -r requirements.txt

# Linux/macOS
pip3 install -r requirements.txt
```

4. Настройте конфигурацию:
   - Скопируйте `config.example.py` в `config.py`
   - Заполните необходимые значения в `config.py`
   - Или создайте `.env` файл с переменными окружения:
     ```
     TELEGRAM_BOT_TOKEN=your_token_here
     GIGACHAT_AUTH_KEY=your_key_here
     ```

## Использование

1. Запустите бота:
```bash
python main.py
```

2. В Telegram найдите бота по имени и начните диалог командой `/start`
