# services/ai/unified_rag_agent.py
import logging
import json
import random
import re
from typing import List, Dict, Any, Optional

from .base import AIAgent
from database.core import Database
from .gigachat_llm import GigaChatLLM
from .memory_store import MemoryStore
from .embeddings_store import EmbeddingsStore

logger = logging.getLogger(__name__)


class UnifiedRAGAgent(AIAgent):
    """
    Унифицированный RAG-агент, который использует единый подход 
    для обработки всех типов запросов на основе извлечения знаний.
    """

    def __init__(self):
        super().__init__(name="UnifiedRAGAgent", autonomy_level=2)
        self.db = Database()
        self.llm = GigaChatLLM(temperature=0.7)
        self.memory_store = MemoryStore()
        self.embeddings_store = EmbeddingsStore()

        # Определение типов запросов и соответствующих обработчиков
        self.handlers = {
            "event_info": self._handle_event_info,
            "current_events": self._handle_current_events,
            "recommendation": self._handle_recommendation,
            "dialogue": self._handle_dialogue
        }

        # Регистрация инструментов
        self.register_tool(
            "detect_query_intent",
            self._detect_intent,
            "Определяет намерение и тип запроса пользователя"
        )
        
        self.register_tool(
            "semantic_search",
            self._semantic_search,
            "Выполняет семантический поиск по данным"
        )
        
        self.register_tool(
            "generate_response",
            self._generate_response,
            "Генерирует ответ на основе найденной информации и запроса"
        )
        
        self.register_tool(
            "get_db_events",
            self._get_db_events,
            "Получает события напрямую из базы данных"
        )

    def _detect_intent(self, query: str, context: Dict = None) -> Dict:
        """
        Определяет намерение пользователя и тип запроса с учетом контекста
        
        Args:
            query: Запрос пользователя
            context: Дополнительный контекст разговора
            
        Returns:
            Словарь с информацией о типе запроса и намерении
        """
        # Получаем контекст разговора
        is_follow_up = context.get("is_follow_up", False) if context else False
        previous_intent = context.get("previous_intent") if context else None
        previous_response = context.get("previous_response") if context else None
        
        # Если это уточняющий вопрос и мы знаем предыдущее намерение - больше шансов продолжить тот же тип запроса
        if is_follow_up and previous_intent and previous_intent in self.handlers:
            # Короткие вопросы после конкретного намерения обычно являются уточнениями того же типа
            if len(query.split()) <= 5:
                return {
                    "type": previous_intent,
                    "confidence": 0.8,
                    "query": query,
                    "is_follow_up": True
                }
        
        try:
            # Используем GigaChat для определения намерения
            prompt = f"""
            Проанализируй запрос пользователя и определи его намерение.
            
            Запрос пользователя: "{query}"
            
            {"Предыдущий ответ ассистента: " + previous_response if previous_response else ""}
            
            Возможные типы намерений:
            1. event_info - запрос информации о конкретном мероприятии
            2. current_events - запрос текущих или ближайших мероприятий
            3. recommendation - запрос рекомендаций по мероприятиям
            4. dialogue - общий диалог, вопрос не о мероприятиях
            
            Верни ответ в формате JSON:
            {{
                "type": "тип намерения",
                "confidence": число от 0 до 1,
                "explanation": "краткое объяснение почему выбран этот тип",
                "extracted_info": {{
                    "city": "город если упомянут",
                    "interests": ["список интересов"],
                    "profession": "профессия если упомянута",
                    "event_name": "название мероприятия если упомянуто"
                }}
            }}
            """
            
            response = self.llm.generate(prompt)
            try:
                result = json.loads(response)
                
                # Проверяем корректность типа
                if result["type"] in self.handlers:
                    return {
                        "type": result["type"],
                        "confidence": result["confidence"],
                        "query": query,
                        "is_follow_up": is_follow_up,
                        "extracted_info": result.get("extracted_info", {})
                    }
            except json.JSONDecodeError:
                logger.error("Failed to parse LLM response for intent detection")
        
        except Exception as e:
            logger.error(f"Error using LLM for intent detection: {e}")
        
        # По умолчанию считаем диалогом
        return {
            "type": "dialogue",
            "confidence": 0.5,
            "query": query,
            "is_follow_up": is_follow_up
        }

    def _semantic_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Выполняет семантический поиск по базе мероприятий
        
        Args:
            query: Запрос для поиска
            k: Количество результатов
            
        Returns:
            Список найденных мероприятий
        """
        try:
            # Проверяем, что запрос не пустой
            if not query or not query.strip():
                logger.warning("Empty query for semantic search")
                return []
                
            # Используем улучшенный запрос для повышения точности поиска
            try:
                enriched_query = self.llm.generate(
                    f"""
                    Перефразируй запрос для улучшения семантического поиска мероприятий.
                    Добавь ключевые слова, связанные с волонтерством и событиями.
                    
                    Запрос: "{query}"
                    
                    Верни только улучшенный запрос, без объяснений.
                    """
                )
                
                # Проверяем, что получили содержательный ответ
                if enriched_query and len(enriched_query.strip()) > 5:
                    # Выполняем поиск с улучшенным запросом
                    results = self.embeddings_store.search(enriched_query, k)
                    
                    if results:
                        return results
            except Exception as inner_e:
                logger.warning(f"Error enriching query: {inner_e}, falling back to original query")
            
            # Если произошла ошибка или нет результатов, используем оригинальный запрос
            return self.embeddings_store.search(query, k)
                
        except Exception as e:
            logger.error(f"Error performing semantic search: {e}")
            return []

    def _get_db_events(self, filters: Dict = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает события напрямую из базы данных
        
        Args:
            filters: Фильтры для запроса (теги, город и т.д.)
            limit: Ограничение по количеству результатов
            
        Returns:
            Список мероприятий из БД
        """
        try:
            conditions = []
            params = []
            
            if filters:
                if 'city' in filters and filters['city']:
                    conditions.append("city LIKE ?")
                    params.append(f"%{filters['city']}%")
                
                if 'tags' in filters and filters['tags']:
                    for tag in filters['tags']:
                        conditions.append("tags LIKE ?")
                        params.append(f"%{tag}%")
                
                if 'query' in filters and filters['query']:
                    # Поиск по ключевым словам в названии и описании
                    keywords = filters['query'].split()
                    for keyword in keywords:
                        if len(keyword) > 3:  # Игнорируем короткие слова
                            conditions.append("(name LIKE ? OR description LIKE ?)")
                            params.append(f"%{keyword}%")
                            params.append(f"%{keyword}%")
            
            sql_where = ""
            if conditions:
                sql_where = "WHERE " + " OR ".join(conditions)
            
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT id, name, description, event_date, start_time,
                           city, creator, participation_points, tags
                    FROM events
                    {sql_where}
                    LIMIT ?
                """, params + [limit])
                
                db_events = cursor.fetchall()
                
                if not db_events:
                    return []
                
                events = []
                for db_event in db_events:
                    event = {
                        "id": db_event['id'],
                        "name": db_event['name'],
                        "date": db_event['event_date'],
                        "event_date": db_event['event_date'],
                        "time": db_event['start_time'],
                        "city": db_event['city'],
                        "description": db_event['description'],
                        "tags": db_event['tags'],
                        "points": db_event['participation_points'],
                    }
                    events.append(event)
                
                return events
                
        except Exception as e:
            logger.error(f"Error fetching events from database: {e}")
            return []

    def _generate_response(self, query: str, events: List[Dict], intent: str, **kwargs) -> str:
        """
        Генерирует ответ на основе найденной информации и запроса
        
        Args:
            query: Запрос пользователя
            events: Список мероприятий
            intent: Тип запроса/намерение
            **kwargs: Дополнительные параметры
            
        Returns:
            Сгенерированный ответ
        """
        logger.info(f"Generating response for intent: {intent} with {len(events)} events")
        if not events:
            try:
                # Если не нашли события по критериям, проверим, есть ли вообще какие-то события в БД
                with self.db.connect() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM events")
                    total_events = cursor.fetchone()[0]
                    
                    logger.info(f"Total events in DB: {total_events}")
                    
                    if total_events == 0:
                        # Если в БД действительно нет событий
                        return "В базе данных пока нет мероприятий. Приходите позже, когда появятся новые события!"
                    else:
                        # Если события есть, но не подошли под фильтры, предложим изменить критерии поиска
                        city = kwargs.get("city", "")
                        city_msg = f" в городе {city}" if city else ""
                        return f"К сожалению, я не нашел подходящих мероприятий{city_msg} по вашему запросу. Попробуйте изменить параметры поиска или спросить о мероприятиях в других городах."
            except Exception as e:
                logger.error(f"Error checking total events: {e}")
                return "Извините, не удалось найти подходящие мероприятия по вашему запросу. Возможно, вы хотите узнать о мероприятиях в определенном городе или конкретной категории? Я могу помочь вам найти что-то интересное."
        
        # Получаем информацию о пользователе, если доступна
        user_id = kwargs.get("user_id")
        user_info = kwargs.get("user_info", {})
        
        # Если информация о пользователе не была передана, пытаемся получить ее из базы данных
        if not user_info and user_id:
            try:
                with self.db.connect() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT first_name, city, tags FROM users WHERE id = ?", (user_id,))
                    result = cursor.fetchone()
                    if result:
                        user_info = dict(result)
            except Exception as e:
                logger.error(f"Error fetching user info: {e}")
        
        # Персонализируем приветствие
        greeting = ""
        if user_info and user_info.get('first_name'):
            greeting = f"для вас, {user_info.get('first_name')}, "
        
        # Учитываем интересы пользователя при формировании ответа
        user_interests = []
        if user_info and user_info.get('tags'):
            if isinstance(user_info.get('tags'), str):
                user_interests = [tag.strip() for tag in user_info.get('tags').split(',')]
            elif isinstance(user_info.get('tags'), list):
                user_interests = user_info.get('tags')
        
        # Получаем интересы из параметров, если они есть
        if kwargs.get("user_interests"):
            user_interests = kwargs.get("user_interests")
        
        # Фильтруем мероприятия по городу пользователя, если известен
        user_city = None
        if user_info and user_info.get('city'):
            user_city = user_info.get('city')
        
        # Получаем город из параметров, если он есть
        if kwargs.get("city"):
            user_city = kwargs.get("city")
            
        city_filtered_events = []
        if user_city:
            for event in events:
                event_city = event.get('city', '').lower()
                if event_city and user_city.lower() in event_city:
                    city_filtered_events.append(event)
            
            # Если нашли мероприятия в городе пользователя, используем их
            if city_filtered_events:
                events = city_filtered_events
        
        # Форматируем список мероприятий для LLM
        events_text = self._format_events_for_prompt(events)
        
        # Определяем стиль ответа в зависимости от намерения
        response_style = {
            "event_info": "подробно о конкретном мероприятии, с акцентом на детали",
            "current_events": "энтузиастичный рассказ о ближайших мероприятиях",
            "recommendation": "персонализированный подбор с учетом интересов пользователя",
            "dialogue": "дружелюбная беседа с элементами рекомендаций"
        }
        
        style = response_style.get(intent, "информативный и дружелюбный")
        
        # Создаем промпт, обогащенный контекстной информацией
        prompt = f"""
        Запрос пользователя: "{query}"
        
        Тип запроса: {intent}
        
        {"Город пользователя: " + user_city if user_city else ""}
        {"Интересы пользователя: " + ", ".join(user_interests) if user_interests else ""}
        
        Информация о найденных мероприятиях:
        {events_text}
        
        Сформируй персонализированный ответ {greeting}в стиле: {style}
        
        Ответ должен быть:
        - Естественным и дружелюбным, как в разговоре с живым человеком
        - Информативным, основанным на предоставленных данных о мероприятиях
        - Учитывающим интересы пользователя, если они указаны
        - Подчеркивающим мероприятия в городе пользователя, если они найдены
        - С элементами энтузиазма и вовлечения пользователя
        
        Для ответов о рекомендациях: объясни, почему конкретное мероприятие может понравиться пользователю.
        Для ответов о конкретном мероприятии: сосредоточься на ключевых деталях и практической информации.
        Для ответов о текущих мероприятиях: выдели самые ближайшие или интересные события.
        
        Важно! Не упоминай, что ты используешь базу данных или другие технические аспекты. Общайся естественно,
        как если бы ты был сотрудником волонтерского центра, который хорошо знает все мероприятия.
        
        Ответ:
        """
        
        try:
            response = self.llm.generate(prompt)
            return response
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            # Возвращаем запасной ответ в случае ошибки
            if intent == "event_info":
                return f"Я нашел информацию о мероприятии '{events[0].get('name', 'мероприятие')}'. Оно пройдет {events[0].get('event_date', '')} в {events[0].get('city', '')}. Подробности: {events[0].get('description', 'Описание недоступно')}."
            elif intent == "recommendation":
                return f"Я рекомендую вам обратить внимание на мероприятие '{events[0].get('name', 'мероприятие')}'. Оно пройдет {events[0].get('event_date', '')} и соответствует вашим интересам."
            elif intent == "current_events":
                events_list = ", ".join([f"'{e.get('name', 'мероприятие')}'" for e in events[:3]])
                return f"Сейчас доступны следующие мероприятия: {events_list}. Что из этого вас заинтересовало?"
            else:
                return "Я нашел несколько интересных мероприятий для вас. Могу рассказать подробнее о любом из них или предложить что-то еще."

    def _handle_event_info(self, query: str, **kwargs) -> str:
        """
        Обрабатывает запросы о конкретных мероприятиях
        
        Args:
            query: Запрос пользователя
            **kwargs: Дополнительные параметры
            
        Returns:
            Ответ с информацией о мероприятии
        """
        try:
            user_id = kwargs.get("user_id")
            
            # Проверяем, можем ли найти название мероприятия в запросе
            event_name = self._extract_event_name(query)
            
            # Если не нашли название в запросе напрямую, пробуем семантический поиск
            if not event_name:
                try:
                    logger.info(f"Event name not found in query, trying semantic search: {query}")
                    events = self._semantic_search(query, k=3)
                    
                    if not events:
                        # Если и семантический поиск не нашел результатов, возвращаем сообщение
                        return "К сожалению, я не смог найти мероприятие по вашему запросу. Попробуйте описать его иначе или спросите о других мероприятиях."
                    
                    # Выбираем наиболее релевантное мероприятие
                    event = events[0]
                    event_name = event.get("name", "")
                except Exception as e:
                    logger.error(f"Error performing semantic search for event: {e}")
                    return "Извините, но я не смог найти информацию о запрашиваемом мероприятии. Проверьте название или спросите о других мероприятиях."
            
            # Пробуем найти мероприятие в базе данных (более полная информация)
            event_details = None
            try:
                with self.db.connect() as conn:
                    cursor = conn.cursor()
                    # Сначала пробуем найти по точному совпадению
                    cursor.execute("SELECT * FROM events WHERE name = ?", (event_name,))
                    result = cursor.fetchone()
                    
                    # Если не нашли по точному совпадению, пробуем искать по частичному
                    if not result:
                        cursor.execute("SELECT * FROM events WHERE name LIKE ?", (f"%{event_name}%",))
                        result = cursor.fetchone()
                    
                    if result:
                        event_details = dict(result)
                        
                        # Проверяем, зарегистрирован ли пользователь на это мероприятие
                        if user_id:
                            cursor.execute(
                                "SELECT * FROM user_events WHERE user_id = ? AND event_id = ?", 
                                (user_id, event_details["id"])
                            )
                            user_registered = cursor.fetchone() is not None
                            event_details["user_registered"] = user_registered
            except Exception as e:
                logger.error(f"Error fetching event details from database: {e}")
            
            # Если событие не найдено в базе, используем результаты семантического поиска
            if not event_details:
                try:
                    events = self._semantic_search(event_name, k=1)
                    if events:
                        event_details = events[0]
                    else:
                        return "К сожалению, я не нашел подробной информации о мероприятии. Попробуйте уточнить название или спросить о других событиях."
                except Exception as e:
                    logger.error(f"Error fetching event details from semantic search: {e}")
                    return "Извините, я не смог найти информацию о запрашиваемом мероприятии. Проверьте название или спросите о других мероприятиях."
            
            # Теперь у нас есть event_details, можем генерировать ответ
            try:
                # Подготавливаем информацию для промпта
                event_info = self._format_event_for_user(event_details)
                
                # Проверяем, зарегистрирован ли пользователь на это событие
                registration_info = ""
                if event_details.get("user_registered"):
                    registration_info = "Пользователь уже зарегистрирован на это мероприятие."
                else:
                    registration_info = "Пользователь еще не зарегистрирован на это мероприятие."
                
                # Создаем промпт для генерации ответа
                prompt = f"""
                Запрос пользователя: "{query}"
                
                Информация о мероприятии:
                {event_info}
                
                {registration_info}
                
                Сгенерируй информативный и дружелюбный ответ о данном мероприятии. 
                Не упоминай, что ты нашел эту информацию в базе данных.
                Создай ощущение, будто ты настоящий консультант волонтерского центра.
                
                Включи ключевые детали:
                - Название мероприятия
                - Дату и время
                - Место проведения
                - Краткое описание
                - Требуемые навыки (если указаны)
                - Уточнение о регистрации пользователя на мероприятие
                
                Если пользователь не зарегистрирован, предложи ему зарегистрироваться.
                
                Твой ответ должен быть структурированным, понятным и вовлекающим.
                """
                
                return self.llm.generate(prompt)
            except Exception as e:
                logger.error(f"Error generating event info response: {e}")
                
                # Запасной ответ, если не удалось сгенерировать ответ через LLM
                # Формируем базовый ответ из доступных данных
                event_name = event_details.get("name", "мероприятие")
                event_date = event_details.get("event_date", "скоро")
                event_location = event_details.get("location", event_details.get("city", "уточняется"))
                
                return f"Мероприятие '{event_name}' пройдет {event_date} в {event_location}. Для получения дополнительной информации, пожалуйста, уточните, что именно вас интересует."
                
        except Exception as e:
            logger.error(f"Unexpected error in event info handler: {e}")
            return "Извините, произошла ошибка при поиске информации о мероприятии. Пожалуйста, уточните название события или спросите о других волонтерских возможностях."
            
    def _extract_event_name(self, query: str) -> str:
        """
        Извлекает название мероприятия из запроса с помощью GigaChat API
        
        Args:
            query: Запрос пользователя
            
        Returns:
            Название мероприятия или пустая строка, если не удалось извлечь
        """
        try:
            # Проверяем запрос на пустоту или слишком короткую длину
            if not query or len(query.strip()) < 5:
                return ""
                
            prompt = f"""
            Проанализируй запрос пользователя и извлеки название мероприятия.
            
            Запрос: "{query}"
            
            Учти следующие аспекты:
            1. Прямые упоминания названий мероприятий
            2. Названия в кавычках
            3. Названия после фраз "о мероприятии", "про мероприятие", "о событии" и т.д.
            4. Контекстные упоминания (например, "расскажи про уборку парка")
            
            Верни ответ в формате JSON:
            {{
                "event_name": "название мероприятия",
                "confidence": число от 0 до 1,
                "explanation": "краткое объяснение почему выбрано это название",
                "context": "дополнительный контекст о мероприятии"
            }}
            
            Если название мероприятия не найдено, верни:
            {{
                "event_name": "",
                "confidence": 0,
                "explanation": "название мероприятия не найдено в запросе",
                "context": ""
            }}
            
            Особые правила:
            1. Название должно быть полным и точным
            2. Если название в кавычках, используй его как есть
            3. Если название неполное, попробуй восстановить его из контекста
            4. Игнорируй общие фразы типа "мероприятие", "событие" без конкретного названия
            """
            
            response = self.llm.generate(prompt)
            try:
                result = json.loads(response)
                event_name = result.get("event_name", "").strip()
                
                if event_name and result.get("confidence", 0) > 0.5:
                    logger.info(f"Extracted event name: '{event_name}' with confidence {result.get('confidence')}")
                    return event_name
                    
            except json.JSONDecodeError:
                logger.error("Failed to parse LLM response for event name extraction")
                
        except Exception as e:
            logger.error(f"Error extracting event name: {e}")
            
        return ""

    def _format_event_for_user(self, event: Dict) -> str:
        """
        Форматирует информацию о мероприятии для пользователя
        
        Args:
            event: Словарь с информацией о мероприятии
            
        Returns:
            Отформатированная строка с информацией о мероприятии
        """
        try:
            # Проверяем наличие базовых полей
            if not event:
                return "Информация о мероприятии отсутствует."

            # Получаем значения полей с проверкой на наличие
            name = event.get("name", "Название не указано")
            date = event.get("event_date", "Дата не указана")
            time = event.get("time", event.get("start_time", "Время не указано"))
            location = event.get("location", "Место не указано")
            city = event.get("city", "")
            description = event.get("description", "Описание отсутствует")
            skills = event.get("skills", "Не указаны")
            
            # Формируем полное местоположение
            full_location = location
            if city and city not in location:
                full_location = f"{location}, {city}"
                
            # Строим форматированный текст
            formatted_info = f"""
            Название: {name}
            Дата: {date}
            Время: {time}
            Место: {full_location}
            Описание: {description}
            Навыки: {skills}
            """
            
            # Добавляем дополнительные поля, если они есть
            if event.get("organizer"):
                formatted_info += f"Организатор: {event.get('organizer')}\n"
                
            if event.get("capacity"):
                formatted_info += f"Количество мест: {event.get('capacity')}\n"
                
            if event.get("tags"):
                tags = event.get("tags")
                if isinstance(tags, str):
                    tags_str = tags
                elif isinstance(tags, list):
                    tags_str = ", ".join(tags)
                else:
                    tags_str = str(tags)
                formatted_info += f"Теги: {tags_str}\n"
                
            return formatted_info
        except Exception as e:
            logger.error(f"Error formatting event for user: {e}")
            # Возвращаем базовую информацию в случае ошибки
            name = event.get("name", "Название не указано") if event else "Мероприятие"
            return f"Название: {name}\nПодробности уточняются."

    def _handle_current_events(self, query: str, **kwargs) -> str:
        """
        Обрабатывает запросы о текущих мероприятиях
        
        Args:
            query: Запрос пользователя
            **kwargs: Дополнительные параметры
            
        Returns:
            Ответ со списком текущих мероприятий
        """
        try:
            user_id = kwargs.get("user_id")
            user_info = kwargs.get("user_info", {})
            
            # Пытаемся извлечь интересы пользователя из запроса
            interests = self._extract_interests_from_query(query)
            
            # Добавляем интересы пользователя из базы данных, если есть
            user_interests = []
            if user_info and "tags" in user_info:
                # Проверяем тип данных tags - может быть как строкой, так и списком
                if isinstance(user_info["tags"], list):
                    user_interests = user_info["tags"]
                elif isinstance(user_info["tags"], str):
                    user_interests = [tag.strip() for tag in user_info["tags"].split(',')]
                
                interests.extend(user_interests)
            
            # Извлекаем город из запроса или информации пользователя
            city = self._extract_city_from_query(query)
            if not city and user_info and user_info.get("city"):
                city = user_info["city"]
            
            logger.info(f"Processing current events query with city: {city}, interests: {interests}")
            
            # Получаем текущие мероприятия - сначала попробуем без фильтра по городу
            try:
                with self.db.connect() as conn:
                    cursor = conn.cursor()
                    
                    # Базовый запрос
                    sql_query = "SELECT * FROM events"
                    params = []
                    
                    # Если указан город, добавляем его как фильтр
                    if city:
                        sql_query += " WHERE city LIKE ?"
                        params.append(f"%{city}%")
                        
                        # Добавляем интересы как дополнительные фильтры
                        if interests:
                            placeholders = " OR ".join(["tags LIKE ?" for _ in interests])
                            if placeholders:
                                sql_query += f" AND ({placeholders})"
                                params.extend([f"%{interest}%" for interest in interests])
                    else:
                        # Если город не указан, но есть интересы
                        if interests:
                            placeholders = " OR ".join(["tags LIKE ?" for _ in interests])
                            if placeholders:
                                sql_query += f" WHERE ({placeholders})"
                                params.extend([f"%{interest}%" for interest in interests])
                    
                    # Сортируем по дате
                    sql_query += " ORDER BY event_date ASC LIMIT 10"
                    
                    logger.info(f"SQL query for events: {sql_query}, params: {params}")
                    cursor.execute(sql_query, params)
                    
                    # Преобразуем результаты запроса в список словарей
                    events = []
                    for row in cursor.fetchall():
                        event_dict = dict(row)
                        logger.info(f"Found event: {event_dict.get('name')} in {event_dict.get('city')}")
                        events.append(event_dict)
                        
                    # Если не нашли события и был фильтр по городу, пробуем без фильтра
                    if not events and city:
                        logger.info(f"No events found for city {city}, trying without city filter")
                        cursor.execute("SELECT * FROM events ORDER BY event_date ASC LIMIT 10")
                        events = [dict(row) for row in cursor.fetchall()]
                        
                        if events:
                            logger.info(f"Found {len(events)} events without city filter")
                    
                    # Если пользователь авторизован, проверяем регистрацию на мероприятия
                    if user_id and events:
                        for event in events:
                            cursor.execute(
                                "SELECT * FROM user_events WHERE user_id = ? AND event_id = ?",
                                (user_id, event["id"])
                            )
                            event["user_registered"] = cursor.fetchone() is not None
            except Exception as db_error:
                logger.error(f"Database error while fetching current events: {db_error}")
                # В случае ошибки базы данных пробуем использовать векторный поиск
                try:
                    # Формируем запрос для семантического поиска
                    search_query = "текущие мероприятия"
                    if city:
                        search_query += f" в {city}"
                    if interests:
                        search_query += f" по темам {', '.join(interests[:3])}"
                        
                    events = self._semantic_search(search_query, k=10)
                except Exception as e:
                    logger.error(f"Error in semantic search for current events: {e}")
            
            # Если мероприятий нет, возвращаем сообщение об этом
            if not events:
                if city:
                    return f"К сожалению, я не нашел текущих мероприятий в городе {city}. Попробуйте поискать мероприятия в других городах или изменить параметры поиска."
                else:
                    return "К сожалению, я не нашел текущих мероприятий. Попробуйте изменить параметры поиска или спросить о других волонтерских возможностях."
            
            # Формируем информацию о мероприятиях для промпта
            events_info = ""
            for i, event in enumerate(events[:5], 1):  # Ограничиваем до 5 мероприятий для промпта
                events_info += f"{i}. Название: {event.get('name')}\n"
                events_info += f"   Дата: {event.get('event_date')}\n"
                events_info += f"   Город: {event.get('city', '')}\n"
                events_info += f"   Описание: {event.get('description', '')[:100]}...\n"
                if event.get("user_registered") is not None:
                    status = "Вы зарегистрированы" if event.get("user_registered") else "Вы еще не зарегистрированы"
                    events_info += f"   Статус: {status}\n"
                events_info += "\n"
            
            # Генерируем ответ на основе найденных мероприятий
            try:
                # Создаем промпт с контекстом запроса пользователя
                prompt = f"""
                Запрос пользователя: "{query}"
                
                Найдены следующие текущие мероприятия:
                {events_info}
                
                Сгенерируй информативный и дружелюбный ответ, представляющий пользователю список текущих мероприятий.
                Ответ должен быть структурированным и содержать ключевую информацию о каждом мероприятии:
                - название
                - дата и время
                - место проведения
                - краткое описание
                
                Если пользователь указал конкретные интересы ({", ".join(interests) if interests else "не указаны"}), 
                подчеркни мероприятия, соответствующие этим интересам.
                
                Если пользователь уже зарегистрирован на какие-то мероприятия, упомяни это.
                Предложи зарегистрироваться на мероприятия, если пользователь еще не сделал этого.
                
                Сделай акцент на разнообразии мероприятий и возможностях для волонтерства.
                Твой ответ должен быть персонализированным и вовлекающим, как если бы ты был настоящим консультантом волонтерского центра.
                """
                
                return self.llm.generate(prompt)
            except Exception as gen_error:
                logger.error(f"Error generating response for current events: {gen_error}")
                
                # Запасной ответ в случае ошибки генерации
                response = "Вот текущие мероприятия:\n\n"
                for i, event in enumerate(events[:5], 1):
                    response += f"{i}. {event.get('name')} - {event.get('event_date')}"
                    if event.get('city'):
                        response += f", {event.get('city')}"
                    response += "\n"
                
                response += "\nДля получения подробной информации о конкретном мероприятии, уточните его название."
                return response
                
        except Exception as e:
            logger.error(f"Unexpected error in current events handler: {e}")
            return "Извините, произошла ошибка при поиске текущих мероприятий. Пожалуйста, попробуйте немного позже или уточните ваш запрос."

    def _handle_recommendation(self, query: str, **kwargs) -> str:
        """
        Обрабатывает запрос на рекомендации мероприятий
        
        Args:
            query: Запрос пользователя
            **kwargs: Дополнительные параметры
            
        Returns:
            Ответ с рекомендациями
        """
        user_id = kwargs.get("user_id")
        user_info = kwargs.get("user_info", {})
        context = kwargs.get("context", {})
        conversation_history = kwargs.get("conversation_history", [])
        
        # Получаем историю разговора для контекста
        conversation_context = ""
        if conversation_history:
            for msg in conversation_history[-5:]:  # Берем последние 5 сообщений
                role = "Пользователь" if msg["role"] == "user" else "Ассистент"
                conversation_context += f"{role}: {msg['content']}\n"
        
        # Анализируем контекст и запрос с помощью GigaChat
        try:
            analysis_prompt = f"""
            Проанализируй диалог с пользователем и определи:
            1. Профессию или род деятельности пользователя (если упоминается)
            2. Интересы и предпочтения
            3. Город или регион (если упоминается)
            4. Тип мероприятий, которые могут быть интересны
            
            Диалог:
            {conversation_context}
            
            Текущий запрос: "{query}"
            
            Верни ответ в формате JSON:
            {{
                "profession": "название профессии или пустая строка",
                "interests": ["список", "интересов"],
                "city": "название города или пустая строка",
                "event_types": ["список", "типов", "мероприятий"]
            }}
            """
            
            analysis_result = self.llm.generate(analysis_prompt)
            try:
                analysis = json.loads(analysis_result)
            except json.JSONDecodeError:
                logger.error("Failed to parse LLM analysis result")
                analysis = {
                    "profession": "",
                    "interests": [],
                    "city": "",
                    "event_types": []
                }
            
            # Формируем поисковый запрос на основе анализа
            search_terms = []
            
            if analysis["profession"]:
                search_terms.append(analysis["profession"])
            
            if analysis["interests"]:
                search_terms.extend(analysis["interests"])
            
            if analysis["event_types"]:
                search_terms.extend(analysis["event_types"])
            
            # Добавляем город в поиск, если он указан
            city = analysis["city"]
            if not city and user_info and user_info.get("city"):
                city = user_info["city"]
            
            # Формируем поисковый запрос
            search_query = " ".join(search_terms) if search_terms else "интересные мероприятия"
            if city:
                search_query += f" в городе {city}"
            
            # Поиск мероприятий
            events = self._semantic_search(search_query, k=5)
            
            # Если не нашли через векторный поиск, используем прямой запрос к БД
            if not events:
                db_filters = {
                    'city': city,
                    'tags': search_terms,
                    'query': search_query
                }
                events = self._get_db_events(db_filters, limit=5)
            
            # Если все еще нет результатов, ищем любые мероприятия
            if not events:
                events = self._get_db_events({'city': city} if city else {}, limit=5)
            
            # Форматируем информацию о мероприятиях для промпта
            events_text = self._format_events_for_prompt(events)
            
            # Генерируем персонализированный ответ
            response_prompt = f"""
            На основе анализа диалога с пользователем и найденных мероприятий, сформируй персонализированный ответ.
            
            Анализ пользователя:
            - Профессия: {analysis["profession"]}
            - Интересы: {", ".join(analysis["interests"])}
            - Город: {city}
            - Интересующие типы мероприятий: {", ".join(analysis["event_types"])}
            
            Найденные мероприятия:
            {events_text}
            
            Сформируй ответ, который:
            1. Учитывает профессию и интересы пользователя
            2. Предлагает мероприятия, где профессиональные навыки могут быть особенно полезны
            3. Подчеркивает мероприятия, соответствующие интересам пользователя
            4. Учитывает предпочтительный город
            5. Объясняет, почему каждое мероприятие может быть интересно пользователю
            
            Ответ должен быть:
            - Естественным и дружелюбным
            - Персонализированным под пользователя
            - Содержать конкретные рекомендации с объяснениями
            - Вовлекать пользователя в диалог
            """
            
            return self.llm.generate(response_prompt)
            
        except Exception as e:
            logger.error(f"Error in recommendation handler: {e}")
            # Возвращаем запасной ответ
            if events:
                return f"Я нашел несколько интересных мероприятий для вас. Вот что я могу предложить:\n\n{self._format_events_for_prompt(events)}"
            else:
                return "К сожалению, я не нашел подходящих мероприятий по вашему запросу. Попробуйте изменить параметры поиска или спросить о мероприятиях в других городах."

    def _extract_interests_from_query(self, query: str) -> List[str]:
        """
        Извлекает интересы пользователя из запроса с помощью GigaChat API
        
        Args:
            query: Запрос пользователя
            
        Returns:
            Список интересов
        """
        try:
            # Проверяем, что запрос не пустой
            if not query or not query.strip():
                return []
                
            prompt = f"""
            Проанализируй запрос пользователя и извлеки его интересы, связанные с волонтерскими мероприятиями.
            
            Запрос: "{query}"
            
            Учти следующие аспекты:
            1. Прямые упоминания интересов (например, "интересуюсь экологией", "люблю спорт")
            2. Косвенные указания на интересы (например, "хочу помогать детям", "ищу мероприятия по уборке")
            3. Профессиональные интересы (например, "я врач, хочу помогать в медицинских мероприятиях")
            4. Общие предпочтения (например, "люблю работать с людьми", "интересуюсь образованием")
            
            Верни ответ в формате JSON:
            {{
                "interests": ["список интересов"],
                "confidence": число от 0 до 1,
                "explanation": "краткое объяснение почему выбраны эти интересы"
            }}
            
            Интересы должны быть:
            - Конкретными и релевантными для волонтерских мероприятий
            - В единственном числе
            - Без специальных символов
            - На русском языке
            """
            
            response = self.llm.generate(prompt)
            try:
                result = json.loads(response)
                interests = result.get("interests", [])
                
                # Фильтруем интересы
                filtered_interests = []
                for interest in interests:
                    # Проверяем длину и наличие только букв
                    if len(interest) >= 3 and interest.isalpha():
                        filtered_interests.append(interest.lower())
                
                return filtered_interests
                
            except json.JSONDecodeError:
                logger.error("Failed to parse LLM response for interests extraction")
                return []
                
        except Exception as e:
            logger.error(f"Error extracting interests with LLM: {e}")
            return []
    
    def _extract_city_from_query(self, query: str) -> Optional[str]:
        """
        Извлекает упоминание города из запроса с помощью GigaChat API
        
        Args:
            query: Запрос пользователя
            
        Returns:
            Название города или None
        """
        logger.info(f"Extracting city from query: '{query}'")
        
        try:
            prompt = f"""
            Проанализируй запрос пользователя и извлеки упоминание города.
            
            Запрос: "{query}"
            
            Учти следующие аспекты:
            1. Прямые упоминания городов (например, "в Москве", "Санкт-Петербург")
            2. Сокращенные названия (например, "СПб", "Питер" для Санкт-Петербурга)
            3. Указания на регион или область
            4. Контекстные упоминания (например, "мероприятия в городе")
            
            Верни ответ в формате JSON:
            {{
                "city": "название города в именительном падеже",
                "confidence": число от 0 до 1,
                "explanation": "краткое объяснение почему выбран этот город",
                "variants": ["список вариантов написания города"]
            }}
            
            Если город не упомянут, верни:
            {{
                "city": "",
                "confidence": 0,
                "explanation": "город не упомянут в запросе",
                "variants": []
            }}
            
            Особые правила:
            1. Для Санкт-Петербурга всегда возвращай "Санкт-Петербург" независимо от формы упоминания
            2. Город должен быть в именительном падеже
            3. Используй официальное название города
            """
            
            response = self.llm.generate(prompt)
            try:
                result = json.loads(response)
                city = result.get("city", "").strip()
                
                if city and result.get("confidence", 0) > 0.5:
                    logger.info(f"Extracted city: '{city}' with confidence {result.get('confidence')}")
                    return city
                    
            except json.JSONDecodeError:
                logger.error("Failed to parse LLM response for city extraction")
                
        except Exception as e:
            logger.error(f"Error using LLM to extract city: {e}")
        
        logger.info("No city found in query")
        return None

    def _handle_dialogue(self, query: str, **kwargs) -> str:
        """
        Обрабатывает общие диалоговые запросы и поддерживает разговор с пользователем
        
        Args:
            query: Запрос пользователя
            **kwargs: Дополнительные параметры
            
        Returns:
            Ответ на общий запрос
        """
        try:
            user_id = kwargs.get("user_id")
            conversation_history = kwargs.get("conversation_history", [])
            
            # Получаем последние несколько сообщений для контекста
            recent_context = ""
            if len(conversation_history) > 2:
                # Берем последние 5 сообщений (исключая текущее) для контекста
                context_messages = conversation_history[-6:-1] if len(conversation_history) > 6 else conversation_history[:-1]
                for msg in context_messages:
                    role_prefix = "Пользователь: " if msg["role"] == "user" else "Ассистент: "
                    recent_context += f"{role_prefix}{msg['content']}\n"
            
            # Проверяем, является ли запрос приветствием
            lower_query = query.lower()
            greetings = ["привет", "здравствуй", "добрый день", "добрый вечер", "доброе утро", "хай"]
            
            if any(greeting in lower_query for greeting in greetings) and len(conversation_history) <= 2:
                personality_responses = [
                    "Здравствуйте! Я чат-бот волонтерского центра. Я могу рассказать о предстоящих мероприятиях, помочь с выбором мероприятия по вашим интересам или предоставить подробную информацию о конкретном событии. Что вас интересует?",
                    "Привет! Рад вас видеть в нашем волонтерском сообществе. Могу рассказать вам о ближайших мероприятиях или предложить что-то по вашим интересам. Чем я могу помочь?",
                    "Добрый день! Я здесь, чтобы помочь вам найти интересные волонтерские мероприятия. Могу подсказать, что сейчас актуально или подобрать подходящее для вас. Расскажите, что вас интересует?"
                ]
                return random.choice(personality_responses)
            
            # Проверяем, является ли запрос благодарностью
            thanks = ["спасибо", "благодарю", "спс", "сенкс"]
            if any(thank in lower_query for thank in thanks):
                follow_up_suggestions = [
                    "Всегда рад помочь! Хотите узнать о других мероприятиях или, может быть, вас интересует что-то конкретное?",
                    "Пожалуйста! Могу ли я еще чем-то помочь? Возможно, вас интересуют мероприятия на выходных?",
                    "Не за что! Если захотите узнать больше о волонтерских возможностях или конкретных мероприятиях - только спросите."
                ]
                return random.choice(follow_up_suggestions)
            
            # Проверяем, может ли это быть вопрос о деталях из предыдущего ответа
            is_follow_up = False
            last_bot_message = None
            last_mentioned_events = []
            
            # Ищем последнее сообщение бота и проверяем, упоминались ли в нем мероприятия
            for msg in reversed(conversation_history[:-1]):  # Исключаем текущий запрос
                if msg["role"] == "assistant":
                    last_bot_message = msg["content"]
                    break
                    
            # Если найдено последнее сообщение бота, проверяем, есть ли в нем упоминания мероприятий
            if last_bot_message:
                # Проверяем, может ли текущий запрос быть уточнением предыдущего ответа
                follow_up_keywords = ["подробнее", "расскажи больше", "это", "этом", "первом", "втором", 
                                "последнем", "о нем", "о ней", "детали", "когда", "где", "как"]
                
                if any(keyword in lower_query for keyword in follow_up_keywords) and len(query.split()) < 15:
                    is_follow_up = True
                    try:
                        # Используем последний ответ как контекст для поиска мероприятий
                        last_mentioned_events = self._semantic_search(last_bot_message, k=3)
                    except Exception as e:
                        logger.error(f"Error searching for events in follow-up context: {e}")
            
            # Получаем интересы пользователя, если они есть в базе
            user_interests = []
            if user_id:
                try:
                    with self.db.connect() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT tags FROM users WHERE id = ?", (user_id,))
                        result = cursor.fetchone()
                        if result:
                            # Преобразуем объект sqlite3.Row в dict и затем получаем значение
                            tags = dict(result).get('tags')
                            if tags:
                                user_interests = [tag.strip() for tag in tags.split(',')]
                except Exception as e:
                    logger.error(f"Error fetching user interests: {e}")
            
            # Если это уточняющий вопрос по предыдущему ответу
            if is_follow_up and last_mentioned_events:
                try:
                    # Объединяем предыдущий контекст и текущий запрос
                    enriched_query = f"{last_bot_message}\n\nПользователь спрашивает: {query}"
                    prompt = f"""
                    Пользователь задает уточняющий вопрос о мероприятиях, которые были упомянуты в вашем предыдущем ответе.
                    
                    Предыдущий контекст:
                    {last_bot_message}
                    
                    Текущий вопрос пользователя: "{query}"
                    
                    Информация о мероприятиях:
                    {self._format_events_for_prompt(last_mentioned_events)}
                    
                    Пожалуйста, ответь на уточняющий вопрос пользователя, используя информацию из предыдущего контекста и данные о мероприятиях.
                    Твой ответ должен быть дружелюбным, информативным и личностным, как будто ты настоящий помощник волонтерского центра.
                    
                    Ответ:
                    """
                    return self.llm.generate(prompt)
                except Exception as e:
                    logger.error(f"Error generating response for follow-up question: {e}")
                    # Возвращаем запасной ответ
                    event = last_mentioned_events[0] if last_mentioned_events else None
                    if event:
                        return f"Конечно! Мероприятие '{event.get('name', 'мероприятие')}' пройдет {event.get('event_date', '')} в {event.get('city', '')}. Хотите узнать что-то ещё?"
                    else:
                        return "Извините, у меня не получилось найти подробную информацию по вашему вопросу. Может быть, вы хотите узнать о других мероприятиях?"
            
            # Для других диалоговых запросов ищем релевантную информацию
            # Если у пользователя есть интересы, используем их для улучшения поиска
            events = []
            try:
                if user_interests:
                    enriched_query = f"{query} {' '.join(user_interests)}"
                    events = self._semantic_search(enriched_query, k=3)
                else:
                    events = self._semantic_search(query, k=3)
            except Exception as e:
                logger.error(f"Error searching for events in dialogue: {e}")
            
            # Генерируем ответ на основе найденной информации или общий ответ
            if events:
                # Удаляем аргумент intent из kwargs, если он там есть, так как он будет передан явно
                dialogue_kwargs = {k: v for k, v in kwargs.items() if k != 'intent'}
                return self._generate_response(query, events, "dialogue", **dialogue_kwargs)
            else:
                # Если не нашли релевантной информации, используем контекст разговора
                try:
                    prompt = f"""
                    Предыдущий контекст разговора:
                    {recent_context}
                    
                    Текущий запрос пользователя: "{query}"
                    
                    Ты - дружелюбный и полезный чат-бот волонтерского центра. Твоя задача - помогать пользователям находить
                    интересные волонтерские мероприятия и отвечать на их вопросы. Поддерживай разговор естественно,
                    как если бы ты был настоящим человеком-консультантом.
                    
                    Если запрос не связан с волонтерством, ты можешь ответить на общие вопросы, но старайся
                    направить разговор к теме волонтерских мероприятий, проявляя личностность и эмпатию.
                    
                    Твой ответ должен быть:
                    - Дружелюбным и отзывчивым
                    - Естественным, как в разговоре с человеком
                    - По возможности, содержать предложение узнать о волонтерских мероприятиях
                    - Кратким (не более 3-4 предложений)
                    
                    Ответ:
                    """
                    
                    return self.llm.generate(prompt)
                except Exception as e:
                    logger.error(f"Error generating general dialogue response: {e}")
                    return "Я готов помочь вам с поиском волонтерских мероприятий. Расскажите, что вас интересует, или спросите о текущих событиях."
        except Exception as e:
            logger.error(f"Unexpected error in dialogue handler: {e}")
            return "Я здесь, чтобы помочь вам найти интересные волонтерские мероприятия. Хотите узнать о ближайших событиях или подобрать что-то по вашим интересам?"

    def _format_events_for_prompt(self, events: List[Dict]) -> str:
        """
        Форматирует список мероприятий для использования в промптах
        
        Args:
            events: Список мероприятий
            
        Returns:
            Отформатированный текст с мероприятиями
        """
        if not events:
            return "Информация о мероприятиях отсутствует."
            
        events_text = ""
        for idx, event in enumerate(events, 1):
            event_name = event.get('name', 'Неизвестное мероприятие')
            event_date = event.get('event_date', event.get('date', 'Дата не указана'))
            event_time = event.get('time', event.get('start_time', 'Время не указано'))
            event_city = event.get('city', 'Город не указан')
            event_tags = event.get('tags', 'Без категории')
            event_desc = event.get('description', '')[:200] + ('...' if len(event.get('description', '')) > 200 else '')
            
            events_text += f"Мероприятие #{idx}:\n"
            events_text += f"Название: {event_name}\n"
            events_text += f"Дата и время: {event_date}, {event_time}\n"
            events_text += f"Город: {event_city}\n"
            events_text += f"Теги: {event_tags}\n"
            events_text += f"Описание: {event_desc}\n\n"
            
        return events_text

    def process_query(self, query: str, **kwargs) -> str:
        """
        Обрабатывает запрос пользователя
        
        Args:
            query: Запрос пользователя
            **kwargs: Дополнительные параметры
            
        Returns:
            Ответ на запрос
        """
        try:
            # Получаем идентификатор пользователя
            user_id = kwargs.get("user_id")
            
            # Получаем историю разговора
            conversation_history = kwargs.get("conversation_history", [])
            if not conversation_history and user_id:
                # Если история не передана, но известен ID пользователя, 
                # пытаемся загрузить историю из хранилища
                conversation_history = self.memory_store.get_conversation(user_id) or []
            
            # Анализируем предыдущие сообщения для определения контекста
            context = self._analyze_conversation_context(conversation_history, query)
            
            # Сохраняем текущий запрос в истории
            if user_id:
                conversation_history.append({"role": "user", "content": query})
                self.memory_store.save_conversation(user_id, conversation_history)
            
            # Определяем намерение пользователя с учетом контекста
            intent_info = self._detect_intent(query, context)
            logger.debug(f"Detected intent: {intent_info['type']} with confidence {intent_info['confidence']}")
            
            # Проверяем, является ли это продолжением предыдущего диалога
            if context.get("is_follow_up") and context.get("previous_intent"):
                # Если это уточняющий запрос, используем предыдущее намерение
                previous_intent = context.get("previous_intent")
                if previous_intent in self.handlers and intent_info["confidence"] < 0.7:
                    intent_info["type"] = previous_intent
                    logger.debug(f"Using previous intent: {previous_intent} for follow-up question")
            
            # Получаем соответствующий обработчик
            handler = self.handlers.get(intent_info["type"], self._handle_dialogue)
            
            # Добавляем контекст разговора в параметры
            kwargs["conversation_history"] = conversation_history
            kwargs["context"] = context
            
            # Получаем информацию о пользователе, если доступна
            if user_id:
                user_info = self._get_user_info(user_id)
                if user_info:
                    kwargs["user_info"] = user_info
            
            # Очищаем kwargs от возможного дублирования intent
            handler_kwargs = {k: v for k, v in kwargs.items() if k != 'intent'}
            
            # Вызываем обработчик с явным указанием intent, избегая дублирования
            response = handler(query, intent=intent_info["type"], **handler_kwargs)
            
            # Сохраняем ответ в истории
            if user_id:
                conversation_history.append({"role": "assistant", "content": response})
                self.memory_store.save_conversation(user_id, conversation_history)
            
            # Сохраняем цепочку рассуждений, если включена отладка
            if logger.isEnabledFor(logging.DEBUG):
                reasoning_steps = self.reason(query, context)
                self.memory_store.store_reasoning_chain(
                    agent_id=self.name,
                    query=query,
                    reasoning_steps=reasoning_steps,
                    result=response[:100] + "..." if len(response) > 100 else response
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте переформулировать вопрос или задать другой вопрос."
    
    def _analyze_conversation_context(self, conversation_history: List[Dict], current_query: str) -> Dict:
        """
        Анализирует историю разговора для определения контекста
        
        Args:
            conversation_history: История разговора
            current_query: Текущий запрос пользователя
            
        Returns:
            Словарь с информацией о контексте
        """
        context = {
            "is_follow_up": False,
            "previous_query": None,
            "previous_response": None,
            "previous_intent": None,
            "mentioned_events": [],
            "conversation_length": len(conversation_history)
        }
        
        # Если истории разговора нет или она слишком короткая
        if not conversation_history or len(conversation_history) < 2:
            return context
        
        # Получаем предыдущий запрос пользователя и ответ бота
        previous_messages = conversation_history[-2:] if len(conversation_history) >= 2 else conversation_history
        
        for msg in previous_messages:
            if msg["role"] == "user":
                context["previous_query"] = msg["content"]
            elif msg["role"] == "assistant":
                context["previous_response"] = msg["content"]
        
        # Определяем, является ли текущий запрос уточнением предыдущего
        if context["previous_response"] and context["previous_query"]:
            # Короткие запросы часто являются уточнениями
            if len(current_query.split()) <= 5:
                context["is_follow_up"] = True
            
            # Запросы с указательными местоимениями
            follow_up_indicators = ["это", "эти", "этот", "он", "она", "они", "там", "его", "ее", "их", 
                                   "такой", "такие", "подробнее", "больше", "детали", "когда", "где"]
            
            if any(indicator in current_query.lower() for indicator in follow_up_indicators):
                context["is_follow_up"] = True
            
            # Определяем предыдущее намерение по ключевым словам в ответе бота
            if "мероприятие" in context["previous_response"].lower() or "событие" in context["previous_response"].lower():
                if "рекомендуем" in context["previous_response"].lower() or "подходит" in context["previous_response"].lower():
                    context["previous_intent"] = "recommendation"
                elif "ближайшие" in context["previous_response"].lower() or "актуальные" in context["previous_response"].lower():
                    context["previous_intent"] = "current_events"
                elif len(context["previous_response"].split("\n")) > 5 and "описание" in context["previous_response"].lower():
                    context["previous_intent"] = "event_info"
        
        return context
        
    def _get_user_info(self, user_id: int) -> Dict:
        """
        Получает информацию о пользователе из базы данных
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь с информацией о пользователе
        """
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, first_name, telegram_tag, role, city, tags, 
                           score, employee_number, registered_events
                    FROM users
                    WHERE id = ?
                    """, 
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    # Преобразуем объект sqlite3.Row в словарь
                    user_info = dict(result)
                    
                    # Преобразуем теги в список
                    if 'tags' in user_info and user_info['tags']:
                        user_info['tags'] = [tag.strip() for tag in user_info['tags'].split(',') if tag.strip()]
                    else:
                        user_info['tags'] = []
                    
                    # Преобразуем зарегистрированные мероприятия в список
                    if 'registered_events' in user_info and user_info['registered_events']:
                        user_info['registered_events'] = [
                            event_id.strip() for event_id in user_info['registered_events'].split(',') 
                            if event_id.strip()
                        ]
                    else:
                        user_info['registered_events'] = []
                    
                    return user_info
                
                return {}
        except Exception as e:
            logger.error(f"Error fetching user info: {e}")
            return {}

    def reason(self, query: str, context: Dict = None) -> List[str]:
        """
        Построение цепочки рассуждений для обработки запроса
        
        Args:
            query: Запрос пользователя
            context: Контекстная информация
            
        Returns:
            Список шагов рассуждения
        """
        reasoning_steps = []
        
        # 1. Анализ запроса
        reasoning_steps.append(f"Анализирую запрос пользователя: {query}")
        
        # 2. Определение намерения
        intent_info = self._detect_intent(query, context)
        reasoning_steps.append(f"Определен тип запроса: {intent_info['type']} с уверенностью {intent_info['confidence']}")
        
        # 3. Поиск релевантной информации
        reasoning_steps.append("Выполняю поиск релевантной информации")
        
        # 4. Формирование ответа
        reasoning_steps.append("Формирую персонализированный ответ на основе найденной информации")
        
        return reasoning_steps

    def _extract_profession_from_query(self, query: str) -> Optional[str]:
        """
        Извлекает упоминание профессии из запроса пользователя с помощью GigaChat API
        
        Args:
            query: Запрос пользователя
            
        Returns:
            Название профессии или None
        """
        logger.info(f"Extracting profession from query: '{query}'")
        
        try:
            prompt = f"""
            Проанализируй запрос пользователя и определи, упоминает ли он свою профессию или род деятельности.
            
            Запрос: "{query}"
            
            Если в запросе упоминается профессия или род деятельности:
            1. Извлеки название профессии
            2. Определи, является ли это основной профессией или дополнительной деятельностью
            3. Учти различные формы написания (например, "я юрист", "работаю юристом", "имею юридическое образование")
            
            Верни ответ в формате JSON:
            {{
                "profession": "название профессии в именительном падеже",
                "confidence": число от 0 до 1,
                "explanation": "краткое объяснение почему выбрана эта профессия",
                "context": "дополнительный контекст о профессии"
            }}
            
            Если профессия не упоминается, верни:
            {{
                "profession": "",
                "confidence": 0,
                "explanation": "профессия не упомянута в запросе",
                "context": ""
            }}
            
            Особые правила:
            1. Профессия должна быть в именительном падеже
            2. Игнорируй временные или разовые занятия
            3. Учитывай только основные профессии, а не подработки
            4. Если упомянуто образование, используй соответствующую профессию
            """
            
            response = self.llm.generate(prompt)
            try:
                result = json.loads(response)
                profession = result.get("profession", "").strip()
                
                if profession and result.get("confidence", 0) > 0.5:
                    logger.info(f"Extracted profession: '{profession}' with confidence {result.get('confidence')}")
                    return profession.lower()
                    
            except json.JSONDecodeError:
                logger.error("Failed to parse LLM response for profession extraction")
                
        except Exception as e:
            logger.error(f"Error extracting profession with LLM: {e}")
        
        logger.info("No profession found in query")
        return None
