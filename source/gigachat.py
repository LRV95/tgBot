import requests
import time
import logging
from data.config import AUTHORIZATION_KEY, GIGACHAT_TOKEN_URL, GIGACHAT_API_URL, MODEL_NAME, TEMPERATURE

# Настройка логирования
logger = logging.getLogger(__name__)

# Глобальная переменная для хранения токена и времени его истечения
access_token = None
token_expires_at = 0

def get_access_token():
    """
    Получает Access Token от GigaChat API.
    """
    global access_token, token_expires_at

    # Если токен уже есть и он не истек, возвращаем его
    if access_token and time.time() < token_expires_at:
        return access_token

    # Заголовки для запроса токена
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'Authorization': f'Basic {AUTHORIZATION_KEY}',
        'RqUID': '7399aba6-c390-4aac-b2c5-f75d064f2d01',  # Уникальный идентификатор запроса
    }

    # Параметры запроса
    payload = {
        'scope': 'GIGACHAT_API_PERS',
    }

    # Отправляем запрос на получение токена (отключаем проверку SSL)
    try:
        response = requests.post(GIGACHAT_TOKEN_URL, headers=headers, data=payload, verify=False)
        response.raise_for_status()  # Проверяем, не вернулась ли ошибка
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при получении токена: {e}")
        raise Exception(f"Ошибка при получении токена: {e}")

    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get('access_token')
        expires_in = token_data.get('expires_in', 3600)  # Время жизни токена (по умолчанию 1 час)
        token_expires_at = time.time() + expires_in  # Время истечения токена
        return access_token
    else:
        logger.error(f"Ошибка при получении токена: {response.status_code} - {response.text}")
        raise Exception(f"Ошибка при получении токена: {response.status_code} - {response.text}")

def get_gigachat_response(prompt):
    """
    Отправляет запрос к GigaChat API и возвращает ответ.
    """
    # Получаем актуальный токен
    token = get_access_token()

    # Заголовки для запроса к API
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
    }

    # Тело запроса
    payload = {
        "model": MODEL_NAME,  # Модель из config.py
        "messages": prompt.get("messages", []),  # Используем переданные сообщения
        "temperature": prompt.get("temperature", TEMPERATURE),  # Параметр температуры из config.py
        "max_tokens": prompt.get("max_tokens"),  # Максимальное количество токенов в ответе
    }

    # Отправляем запрос к GigaChat API (отключаем проверку SSL)
    try:
        response = requests.post(GIGACHAT_API_URL, headers=headers, json=payload, verify=False)
        response.raise_for_status()  # Проверяем, не вернулась ли ошибка
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе к GigaChat API: {e}")
        return {"error": f"Ошибка при запросе к GigaChat API: {e}"}

    if response.status_code == 200:
        return response.json().get("choices", [])[0].get("message", {}).get("content", "").strip()
    else:
        logger.error(f"Ошибка при запросе к GigaChat API: {response.status_code} - {response.text}")
        return {"error": f"Ошибка при запросе к GigaChat API: {response.status_code} - {response.text}"}
