"""Сервисы для работы с AI."""

import logging
import requests
import time
from abc import ABC, abstractmethod
from config import (
    AUTHORIZATION_KEY, 
    GIGACHAT_TOKEN_URL, 
    GIGACHAT_API_URL, 
    MODEL_NAME, 
    TEMPERATURE
)
from database.db import Database

# Настройка логирования
logger = logging.getLogger(__name__)

# Глобальные переменные для GigaChat
access_token = None
token_expires_at = 0

def get_access_token():
    """Получает Access Token от GigaChat API."""
    global access_token, token_expires_at

    if access_token and time.time() < token_expires_at:
        return access_token

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'Authorization': f'Basic {AUTHORIZATION_KEY}',
        'RqUID': '7399aba6-c390-4aac-b2c5-f75d064f2d01',
    }

    payload = {'scope': 'GIGACHAT_API_PERS'}

    try:
        response = requests.post(GIGACHAT_TOKEN_URL, headers=headers, data=payload, verify=False)
        response.raise_for_status()
    except requests.exceptions.SSLError:
        logger.error("Ошибка SSL сертификата при подключении к GigaChat API")
        raise Exception("Ошибка SSL сертификата при подключении к GigaChat API")
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при получении токена: {e}")
        raise Exception(f"Ошибка при получении токена: {e}")

    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get('access_token')
        expires_in = token_data.get('expires_in', 3600)
        token_expires_at = time.time() + expires_in
        return access_token
    else:
        logger.error(f"Ошибка при получении токена: {response.status_code} - {response.text}")
        raise Exception(f"Ошибка при получении токена: {response.status_code} - {response.text}")

def get_gigachat_response(prompt):
    """Отправляет запрос к GigaChat API и возвращает ответ."""
    token = get_access_token()

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
    }

    payload = {
        "model": MODEL_NAME,
        "messages": prompt.get("messages", []),
        "temperature": prompt.get("temperature", TEMPERATURE),
        "max_tokens": prompt.get("max_tokens"),
    }

    try:
        response = requests.post(GIGACHAT_API_URL, headers=headers, json=payload, verify=False)
        response.raise_for_status()
    except requests.exceptions.SSLError:
        logger.error("Ошибка SSL сертификата при подключении к GigaChat API")
        return {"error": "Ошибка SSL сертификата при подключении к GigaChat API"}
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе к GigaChat API: {e}")
        return {"error": f"Ошибка при запросе к GigaChat API: {e}"}

    if response.status_code == 200:
        return response.json().get("choices", [])[0].get("message", {}).get("content", "").strip()
    else:
        logger.error(f"Ошибка при запросе к GigaChat API: {response.status_code} - {response.text}")
        return {"error": f"Ошибка при запросе к GigaChat API: {response.status_code} - {response.text}"}

# Теги для маршрутизации запросов
TAGS = ['small_talk', 'events_recommendation']

class AIAgent(ABC):
    """Базовый класс для AI агентов."""

    def __init__(self):
        self.db = Database()

    @abstractmethod
    def process_query(self, query: str, user_id: int) -> str:
        """Обрабатывает запрос пользователя."""
        pass

class RecommendationAgent(AIAgent):
    """Агент для рекомендации мероприятий."""

    def get_user_events(self, user_id: int):
        """Получает список мероприятий пользователя."""
        user = self.db.get_user(user_id)
        if user and user.get("registered_events"):
            return [e.strip() for e in user["registered_events"].split(",") if e.strip()]
        return []

    def get_all_events(self):
        """Получает все доступные мероприятия."""
        events = []
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events")
            for row in cursor.fetchall():
                events.append({
                    "id": row[0],
                    "name": row[1],
                    "date": row[2],
                    "time": row[3],
                    "count": row[4],
                    "points": row[5],
                    "curator": row[6],
                    "description": row[7]
                })
        return events

    def recommend_events(self, user_id: int) -> str:
        """Формирует рекомендации по мероприятиям."""
        all_events = self.get_all_events()
        user_events = self.get_user_events(user_id)
        
        all_events_text = "\n".join([
            f"- {event['name']} (Дата: {event['date']}, Описание: {event['description']})"
            for event in all_events
        ]) if all_events else "Нет доступных событий."
        
        user_events_text = "\n".join(user_events) if user_events else (
            "Пользователь ещё не участвовал в мероприятиях."
        )
        
        prompt = (
            "У пользователя есть следующий опыт участия в мероприятиях:\n"
            f"{user_events_text}\n\n"
            "Вот список всех доступных мероприятий:\n"
            f"{all_events_text}\n\n"
            "Пожалуйста, на основе этого опыта и списка мероприятий, дай рекомендации для пользователя, "
            "какие мероприятия ему стоит посетить. Укажи названия рекомендованных мероприятий и кратко обоснуй свой выбор. "
            "Ты заинтересован в этом, с увлечением отвечаешь пользователю, делаешь это крайне уважительно. "
            "Если пользователь не принимал участия в мероприятиях, предложи из доступных. "
            "Если нет доступных, скажи, что на данный момент мероприятия не проходят. "
            "Не используй markdown, сделай текст красивым для telegram. Используй emoji. "
        )
        
        response = get_gigachat_response({"messages": [{"role": "user", "content": prompt}]})
        return response.strip()

    def process_query(self, query: str, user_id: int) -> str:
        """Обрабатывает запрос и возвращает рекомендации."""
        rec_text = self.recommend_events(user_id)
        prompt = (
            f"Оцени следующие рекомендации для пользователя с учетом его предпочтений:\n"
            f"{rec_text}\n"
            "Дай финальную оценку и дополнительные рекомендации, если необходимо."
        )
        response = get_gigachat_response({"messages": [{"role": "user", "content": prompt}]})
        return response.strip()

class ContextRouterAgent(AIAgent):
    """Агент для маршрутизации запросов."""
    
    def __init__(self):
        super().__init__()
        self.recommendation_agent = RecommendationAgent()
        self.allowed_topics = ["Все"]

    def process_query(self, query: str, user_id: int) -> str:
        """Маршрутизирует запрос к нужному обработчику."""
        lower_query = query.lower()
        prompt = (f"Ты - оркестровый агент, выбираешь кому делегировать задачу. \n"
                  f"Пользователь ввёл запрос: {lower_query}\n"
                  f"Разбери запрос и пойми о чём хочет говорить пользователь, для этого у тебя на выбор есть следующие теги: {TAGS} \n"
                  f"В ответ я должен получить только 1 тег из предложенных, ничего кроме этого. \n")
        response = get_gigachat_response({"messages": [{"role": "user", "content": prompt}]})

        if "events_recommendation" in response:
            return self.recommendation_agent.recommend_events(user_id)
        elif "small_talk" in response:
            return self.default_response(query)
        else:
            topics = ", ".join(self.allowed_topics)
            return ("Извините, я не смог понять ваш запрос. "
                    "Пожалуйста, уточните его или поговорите на одну из следующих тем: " + topics)

    def default_response(self, query: str) -> str:
        """Обрабатывает обычный диалог."""
        prompt = (f"Пользователь задал вопрос: {query}\n"
                  "Ответь дружелюбно и информативно, используя стиль, подходящий для общения в Telegram.")
        response = get_gigachat_response({"messages": [{"role": "user", "content": prompt}]})
        return response.strip()
