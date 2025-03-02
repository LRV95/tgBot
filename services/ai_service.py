ALLOWED_TOPICS = [
    "event_info",
    "events_recommendation",
    "volunteer_projects",
    "charity",
    "volunteer_experience",
    "small_talk",
    "random_events"
]

import logging
import requests
import time
import random
from abc import ABC, abstractmethod
from config import (
    AUTHORIZATION_KEY,
    GIGACHAT_TOKEN_URL,
    GIGACHAT_API_URL,
    MODEL_NAME,
    TEMPERATURE
)
from database.db import Database

logger = logging.getLogger(__name__)

# Глобальные переменные для GigaChat
access_token = None
token_expires_at = 0

def get_access_token():
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

class AIAgent(ABC):
    def __init__(self):
        self.db = Database()

    @abstractmethod
    def process_query(self, query: str, user_id: int) -> str:
        pass
class RecommendationAgent(AIAgent):
    # существующая логика для рекомендаций мероприятий
    def get_user_events(self, user_id: int):
        user = self.db.get_user(user_id)
        if user and user.get("registered_events"):
            return [e.strip() for e in user["registered_events"].split(",") if e.strip()]
        return []
    def get_all_events(self):
        events = []
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events")
            for row in cursor.fetchall():
                events.append({
                    "id": row[0],
                    "project_id": row[1],
                    "event_date": row[2],
                    "start_time": row[3],
                    "city": row[4],
                    "participants_count": row[5],
                    "points": row[6],
                    "creator": row[7],
                    "tags": row[8]
                })
        return events
    def recommend_events(self, user_id: int) -> str:
        all_events = self.get_all_events()
        user_events = self.get_user_events(user_id)
        all_events_text = "\n".join([
            f"- {event['project_id']} (Дата: {event['event_date']}, Описание: {event['tags']})"
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
        rec_text = self.recommend_events(user_id)
        return rec_text.strip()

class DialogueAgent(AIAgent):
    def process_query(self, query: str, conversation_history: list) -> str:
        system_prompt = {
            "role": "system",
            "content": "Ты - эксперт в волонтёрстве, помогаешь пользователям обсуждать вопросы волонтёрства дружелюбно и информативно."
        }
        messages = conversation_history.copy() if conversation_history else []
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, system_prompt)
        messages.append({"role": "user", "content": query})
        prompt = {
            "messages": messages,
            "temperature": TEMPERATURE,
            "max_tokens": 300
        }
        response = get_gigachat_response(prompt)
        return response.strip()

class EventInfoAgent(AIAgent):
    def process_query(self, query: str, user_id: int) -> str:
        all_events = self.db.get_all_events()
        if all_events:
            events_summary = "\n".join([
                f"{event['id']}: {self._extract_event_name(event)} (Дата: {event['event_date']}, Город: {event['city']})"
                for event in all_events
            ])
        else:
            events_summary = "Нет доступных мероприятий."
        prompt = (
            f"У нас имеется следующая информация о мероприятиях:\n{events_summary}\n\n"
            f"Пользователь задал вопрос о событии: \"{query}\".\n"
            "Определи название мероприятия, дату, город, краткое описание и название связанного проекта (если имеется) "
            "на основе информации о мероприятиях выше.\n"
            "Ответь в следующем формате:\n"
            "Название мероприятия: <...>\n"
            "Дата: <...>\n"
            "Город: <...>\n"
            "Описание: <...>\n"
            "Название проекта: <...>\n"
            "Если какая-либо информация недоступна, укажи 'Неизвестно'."
        )
        gigachat_response = get_gigachat_response({"messages": [{"role": "user", "content": prompt}]})
        fields = ["Название мероприятия", "Дата", "Город", "Описание", "Название проекта"]
        extracted = {}
        for field in fields:
            try:
                start = gigachat_response.find(field + ":")
                if start != -1:
                    substring = gigachat_response[start + len(field) + 1:]
                    end = substring.find("\n")
                    value = substring[:end].strip() if end != -1 else substring.strip()
                    extracted[field] = value if value else "Неизвестно"
                else:
                    extracted[field] = "Неизвестно"
            except Exception:
                extracted[field] = "Неизвестно"
        event_name = extracted.get("Название мероприятия", "Неизвестно")
        if event_name == "Неизвестно":
            return "Не удалось определить название мероприятия по вашему запросу. Попробуйте переформулировать вопрос."
        events = self.db.search_events_by_tag(event_name)
        if not events:
            events = self.db.search_events_by_tag(query)
        if not events:
            return f"Мероприятие с названием '{event_name}' не найдено в базе данных."
        elif len(events) > 1:
            events_list_text = "\n".join([
                f"{event['id']}: {self._extract_event_name(event)} (Дата: {event['event_date']}, Город: {event['city']})"
                for event in events
            ])
            return (
                f"Найдено несколько мероприятий, похожих на '{event_name}':\n{events_list_text}\n"
                "Пожалуйста, уточните, о каком из этих мероприятий вы хотите узнать подробнее."
            )
        event = events[0]
        extracted["Дата"] = event.get("event_date", extracted["Дата"])
        extracted["Город"] = event.get("city", extracted["Город"])
        if event.get("tags"):
            parts = event["tags"].split(";")
            for part in parts:
                if "Описание:" in part:
                    extracted["Описание"] = part.split("Описание:")[1].strip()
                    break
        project_info = ""
        if event.get("project_id"):
            project_id = event.get("project_id")
            projects = self.db.get_all_projects()
            project = next((p for p in projects if p["id"] == project_id), None)
            if project:
                project_info = (
                    f"\nИнформация о проекте:\n"
                    f"Название: {project.get('name', 'Неизвестно')}\n"
                    f"Ответственный: {project.get('curator', 'Неизвестно')}\n"
                    f"Описание: {project.get('description', 'Неизвестно')}"
                )
            else:
                project_info = "\nИнформация о проекте: Неизвестно"
        else:
            project_info = "\nИнформация о проекте: Неизвестно"
        response_text = (
            f"Ты помощник волонтёра. Обработай данные и выдай пользователю информацию в дружелюбном формате. Используй emoji."
            f"Все данные должны быть указаны в твоём ответе. Не здоровайся"
            f"Расскажи пользователю как подготовиться и с какими трудностями ему предстоит столкнуться, но в лёгком "
            f"формате. Вот описание:"
            f"{extracted['Описание']}"
            "Информация о мероприятии:\n"
            f"Название мероприятия: {extracted.get('Название мероприятия', 'Неизвестно')}\n"
            f"Дата: {extracted.get('Дата', 'Неизвестно')}\n"
            f"Город: {extracted.get('Город', 'Неизвестно')}\n"
            f"Описание: {extracted.get('Описание', 'Неизвестно')}\n"
            f"Название проекта: {extracted.get('Название проекта', 'Неизвестно')}"
            f"{project_info}"
        )
        final_response = get_gigachat_response({"messages": [{"role": "user", "content": response_text}]})
        return final_response

    def _extract_event_name(self, event: dict) -> str:
        name = ""
        if event.get("tags"):
            parts = event["tags"].split(";")
            for part in parts:
                if "Название:" in part:
                    name = part.split("Название:")[1].strip()
                    break
        if not name:
            name = f"Мероприятие #{event.get('id')}"
        return name

# Новый агент для показа случайных мероприятий
class RandomEventsAgent(AIAgent):
    def _extract_event_name(self, event: dict) -> str:
        name = ""
        if event.get("tags"):
            parts = event["tags"].split(";")
            for part in parts:
                if "Название:" in part:
                    name = part.split("Название:")[1].strip()
                    break
        if not name:
            name = f"Мероприятие #{event.get('id')}"
        return name

    def process_query(self, query: str, user_id: int) -> str:
        events = self.db.get_all_events()
        if not events:
            return "На данный момент нет доступных мероприятий."
        # Выбираем 5 случайных мероприятий (если их больше 5, иначе выводим все)
        selected_events = random.sample(events, 5) if len(events) > 5 else events
        response_lines = ["Вот 5 случайных мероприятий:"]
        for event in selected_events:
            name = self._extract_event_name(event)
            date = event.get("event_date", "Неизвестно")
            time_str = event.get("start_time", "Неизвестно")
            city = event.get("city", "Неизвестно")
            response_lines.append(f"✨ {name}\n📅 {date} 🕒 {time_str} 📍 {city}")
        return "\n\n".join(response_lines)

class ContextRouterAgent(AIAgent):
    def __init__(self):
        super().__init__()
        self.recommendation_agent = RecommendationAgent()
        self.dialogue_agent = DialogueAgent()
        self.event_info_agent = EventInfoAgent()
        self.random_events_agent = RandomEventsAgent()

    def process_query(self, query: str, user_id: int, conversation_history: list) -> str:
        lower_query = query.lower()
        prompt = (
            "Ты - оркестровый агент, который определяет тему запроса пользователя, связанного с волонтёрством.\n"
            f"Пользователь ввёл: {lower_query}\n"
            f"История диалога: {conversation_history}\n"
            f"Выбери один из следующих тегов: {', '.join(ALLOWED_TOPICS)}.\n"
            "Ответ должен содержать только один тег. Если выходит за пределы тегов, пиши None. "
            "Старайся реагировать на small_talk, если есть сомнения. "
            "Если диалог с пользователем продолжается и ты не можешь отнести его к тегам, которые уже были, выводи на small_talk."
        )
        response = get_gigachat_response({"messages": [{"role": "user", "content": prompt}]})
        topic = response.strip().lower()

        if topic not in ALLOWED_TOPICS:
            allowed = ", ".join(ALLOWED_TOPICS)
            return ("Извините, я не могу вести диалог на эту тему")

        if topic == "event_info":
            return self.event_info_agent.process_query(query, user_id)
        elif topic == "events_recommendation":
            return self.recommendation_agent.recommend_events(user_id)
        elif topic == "random_events":
            return self.random_events_agent.process_query(query, user_id)
        elif topic in ["volunteer_projects", "charity", "volunteer_experience", "small_talk"]:
            return self.dialogue_agent.process_query(query, conversation_history)
        else:
            allowed = ", ".join(ALLOWED_TOPICS)
            return ("Извините, я не смог понять ваш запрос. "
                    "Пожалуйста, уточните его или поговорите на одну из следующих тем: " + allowed)