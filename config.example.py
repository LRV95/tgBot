"""Пример файла конфигурации бота"""

import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Токен бота Telegram
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "your_telegram_bot_token_here")

# ID администраторов (список Telegram ID)
ADMIN_ID = [
    123456789,  # Пример ID администратора
]

# Настройки GigaChat
AUTHORIZATION_KEY = os.getenv("GIGACHAT_AUTH_KEY", "your_gigachat_auth_key_here")
GIGACHAT_TOKEN_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
MODEL_NAME = "GigaChat:latest"
TEMPERATURE = 0.7  # Параметр генеративности (0.0 - 1.0)
MAX_TOKENS = 200  # Максимальное количество токенов в ответе
