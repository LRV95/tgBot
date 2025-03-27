# services/ai/dialogue.py
import logging
from typing import List, Dict, Any
import json
import re
import time
import random

from .base import AIAgent
from .gigachat_llm import GigaChatLLM
from .memory_store import MemoryStore
from .bot_info import get_bot_info, get_volunteering_definition

logger = logging.getLogger(__name__)


class DialogueAgent(AIAgent):
    """
    Агент для ведения диалога с пользователем по вопросам волонтерства.
    Поддерживает адаптивные роли и обучение на основе опыта.
    """

    def __init__(self):
        super().__init__(name="DialogueAgent", autonomy_level=2)
        self.llm = GigaChatLLM(temperature=0.7, max_tokens=300)
        self.memory_store = MemoryStore()

        # Определение доступных ролей
        self.available_roles = {
            "consultant": "Консультант по волонтерству, который предоставляет информацию и советы",
            "motivator": "Мотиватор, который вдохновляет и поддерживает волонтеров",
            "teacher": "Учитель, который обучает волонтерским навыкам и лучшим практикам",
            "coordinator": "Координатор, который помогает организовать волонтерскую деятельность",
            "mentor": "Ментор, который дает рекомендации по личностному росту в волонтерстве"
        }

        # Регистрация инструментов
        self.register_tool(
            "detect_sentiment",
            self._detect_sentiment,
            "Определяет эмоциональный тон сообщения пользователя"
        )

        self.register_tool(
            "identify_question_type",
            self._identify_question_type,
            "Определяет тип вопроса пользователя"
        )

        self.register_tool(
            "respond_to_gratitude",
            self._respond_to_gratitude,
            "Генерирует ответ на благодарность пользователя"
        )

        self.register_tool(
            "get_general_info_about_volunteering",
            self._get_general_info_about_volunteering,
            "Предоставляет общую информацию о волонтерстве"
        )

    def _detect_sentiment(self, text: str) -> Dict:
        """
        Определяет эмоциональный тон сообщения пользователя

        Args:
            text: Текст сообщения

        Returns:
            Dict: Информация об эмоциональном тоне
        """
        prompt = f"""
        Проанализируй эмоциональный тон следующего сообщения и определи:
        1. Основное настроение (позитивное, негативное, нейтральное)
        2. Основную эмоцию (радость, грусть, злость, страх, удивление, интерес и т.д.)
        3. Уровень энергии (высокий, средний, низкий)

        Сообщение: "{text}"

        Формат ответа - только JSON:
        {{
            "mood": "позитивное/негативное/нейтральное",
            "emotion": "основная эмоция",
            "energy_level": "высокий/средний/низкий",
            "confidence": 0.8  // число от 0 до 1
        }}
        """

        try:
            response = self.llm.generate(prompt)

            # Пытаемся извлечь JSON из ответа
            json_match = re.search(r'({.*})', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                sentiment = json.loads(json_str)
                return sentiment
            else:
                # Если не удалось извлечь JSON, возвращаем значения по умолчанию
                return {
                    "mood": "нейтральное",
                    "emotion": "интерес",
                    "energy_level": "средний",
                    "confidence": 0.5
                }
        except Exception as e:
            logger.error(f"Ошибка при определении эмоционального тона: {e}")
            return {
                "mood": "нейтральное",
                "emotion": "интерес",
                "energy_level": "средний",
                "confidence": 0.3
            }

    def _identify_question_type(self, text: str) -> Dict:
        """
        Определяет тип вопроса пользователя

        Args:
            text: Текст вопроса

        Returns:
            Dict: Информация о типе вопроса
        """
        prompt = f"""
        Определи тип вопроса/запроса в следующем сообщении:

        Сообщение: "{text}"

        Возможные типы:
        - factual (запрос фактической информации)
        - opinion (запрос мнения или совета)
        - procedural (как что-то сделать)
        - clarification (запрос на уточнение)
        - personal (личный вопрос)
        - hypothetical (гипотетический вопрос)
        - gratitude (выражение благодарности)
        - greeting (приветствие)

        Формат ответа - только JSON:
        {{
            "question_type": "тип вопроса",
            "requires_expertise": true/false,
            "confidence": 0.8  // число от 0 до 1
        }}
        """

        try:
            response = self.llm.generate(prompt)

            # Пытаемся извлечь JSON из ответа
            json_match = re.search(r'({.*})', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                question_info = json.loads(json_str)
                return question_info
            else:
                # Если не удалось извлечь JSON, возвращаем значения по умолчанию
                return {
                    "question_type": "factual",
                    "requires_expertise": False,
                    "confidence": 0.5
                }
        except Exception as e:
            logger.error(f"Ошибка при определении типа вопроса: {e}")
            return {
                "question_type": "factual",
                "requires_expertise": False,
                "confidence": 0.3
            }

    def _respond_to_gratitude(self, history: List = None) -> str:
        """
        Генерирует ответ на благодарность пользователя

        Args:
            history: История разговора

        Returns:
            str: Ответ на благодарность
        """
        # Варианты ответов на благодарность
        responses = [
            "Всегда рад помочь! Если у вас возникнут еще вопросы о волонтерстве, обращайтесь.",
            "Пожалуйста! Рад, что смог быть полезным. Есть ли еще что-то, с чем я могу помочь?",
            "Не за что! Я здесь, чтобы помочь вам с любыми вопросами о волонтерской деятельности.",
            "Рад был помочь! Если понадобится дополнительная информация о мероприятиях, дайте знать.",
            "Всегда к вашим услугам! Надеюсь, вы найдете подходящее волонтерское мероприятие."
        ]

        # Добавляем немного вариативности с эмодзи
        emojis = ["😊", "👍", "✨", "🌟", "🙂"]

        # Выбираем случайный ответ и эмодзи
        response = random.choice(responses)
        emoji = random.choice(emojis)

        return f"{emoji} {response}"

    def _get_general_info_about_volunteering(self, query: str) -> str:
        """
        Предоставляет общую информацию о волонтерстве

        Args:
            query: Запрос пользователя

        Returns:
            str: Информация о волонтерстве
        """
        # Проверяем тип запроса и извлекаем соответствующую информацию
        lower_query = query.lower()

        # Определяем, что конкретно спрашивает пользователь
        if "что такое" in lower_query or "что означает" in lower_query or "определение" in lower_query:
            return get_volunteering_definition()

        if "регистрация" in lower_query or "как зарегистрироваться" in lower_query:
            return f"📝 **Регистрация в боте**\n\n{get_bot_info('registration_process')}"

        if "куратор" in lower_query or "организатор" in lower_query or "кто отвечает" in lower_query:
            return f"👨‍💼 **Информация о кураторах**\n\n{get_bot_info('curator_info')}"

        if "мероприятие" in lower_query and ("запись" in lower_query or "регистр" in lower_query):
            return f"🎯 **Регистрация на мероприятия**\n\n{get_bot_info('event_registration')}"

        if "балл" in lower_query or "бонус" in lower_query or "очк" in lower_query:
            return f"🏆 **Система баллов**\n\n{get_bot_info('points_system')}"

        if "регион" in lower_query or "город" in lower_query or "область" in lower_query:
            regions = get_bot_info('available_regions')
            regions_text = "\n".join([f"• {region}" for region in regions])
            return f"🌍 **Доступные регионы**\n\n{regions_text}"

        if "вид" in lower_query or "тип" in lower_query or "направлен" in lower_query:
            types = get_bot_info('volunteering_types')
            types_text = "\n".join([f"• {vtype}" for vtype in types])
            return f"🔖 **Виды волонтерства**\n\n{types_text}"

        # Если запрос не удалось точно классифицировать, отправляем общую информацию
        try:
            prompt = f"""
            Пользователь задал следующий вопрос о волонтерстве:

            Вопрос: "{query}"

            Предоставь информативный, полезный и дружелюбный ответ о волонтерстве. Используй эмодзи для создания позитивного тона.
            Ответ должен быть информативным, но не слишком длинным (до 250 слов).

            ВАЖНО: Отвечай ТОЛЬКО на вопросы, связанные с волонтерством, благотворительностью, общественной деятельностью, 
            социальной помощью и мероприятиями. Если вопрос не связан с этими темами, вежливо ответь, что ты специализируешься
            на темах волонтерства и можешь помочь найти подходящие мероприятия или ответить на вопросы в этой сфере.

            Базовая информация о боте:
            - Название: {get_bot_info('name')}
            - Описание: {get_bot_info('description')}
            - Виды волонтерства: {', '.join(get_bot_info('volunteering_types'))}
            - Регионы работы: {', '.join(get_bot_info('available_regions'))}
            """

            response = self.llm.generate(prompt)
            return response
        except Exception as e:
            logger.error(f"Ошибка при получении информации о волонтерстве: {e}")
            # Возвращаем базовое определение волонтерства в случае ошибки
            return get_volunteering_definition()

    def reason(self, query: str, context: Dict = None) -> List[str]:
        """
        Построение цепочки рассуждений для формирования ответа на запрос

        Args:
            query: Запрос пользователя
            context: Контекст запроса

        Returns:
            List[str]: Цепочка рассуждений
        """
        conversation_history = context.get("conversation_history", []) if context else []

        reasoning_steps = [
            f"Получен запрос: '{query}'",
            "Анализ эмоционального тона запроса"
        ]

        # Определяем тип вопроса
        if "спасиб" in query.lower() or "благодар" in query.lower():
            reasoning_steps.append("Запрос определен как выражение благодарности")
            reasoning_steps.append("Будет выбрана подходящая вежливая форма ответа")

        elif "привет" in query.lower() or "здравствуй" in query.lower() or "добрый день" in query.lower():
            reasoning_steps.append("Запрос определен как приветствие")
            reasoning_steps.append("Будет выбрана подходящая форма приветствия с предложением помощи")

        elif "что такое волонтерство" in query.lower() or "расскажи о волонтерстве" in query.lower():
            reasoning_steps.append("Запрос на общую информацию о волонтерстве")
            reasoning_steps.append("Будет предоставлена общая информация о концепции волонтерства")

        else:
            # Оцениваем эмоциональный тон
            if "не могу" in query.lower() or "проблема" in query.lower() or "трудно" in query.lower():
                reasoning_steps.append("В запросе выражены трудности, что может указывать на негативный тон")

            # Определяем тип вопроса
            if query.startswith("Как ") or query.startswith("Что "):
                reasoning_steps.append(
                    "Вопрос начинается с 'Как' или 'Что', что может указывать на запрос процедурной информации")
            elif query.startswith("Почему "):
                reasoning_steps.append(
                    "Вопрос начинается с 'Почему', что может указывать на запрос причинно-следственных связей")

        reasoning_steps.append("Анализ истории разговора для понимания контекста")

        # Анализируем историю разговора
        if conversation_history:
            reasoning_steps.append(f"Найдена история разговора из {len(conversation_history)} сообщений")

            # Проверяем наличие предыдущих вопросов по той же теме
            same_topic = False
            if len(conversation_history) >= 2:
                prev_query = conversation_history[-2].get("content", "") if conversation_history[-2].get(
                    "role") == "user" else ""
                for word in query.lower().split():
                    if word in prev_query.lower() and len(word) > 3:  # Игнорируем короткие слова
                        same_topic = True
                        break

            if same_topic:
                reasoning_steps.append("Текущий запрос связан с предыдущим вопросом")
            else:
                reasoning_steps.append("Текущий запрос не связан напрямую с предыдущими вопросами")
        else:
            reasoning_steps.append("История разговора отсутствует, это первое сообщение")

        reasoning_steps.append("Определение наиболее подходящей роли для ответа")
        reasoning_steps.append("Формирование информативного и полезного ответа")

        self.current_reasoning = reasoning_steps
        return reasoning_steps

    def process_query(self, query: str, conversation_history: list = None, user_id: int = None, **kwargs) -> str:
        """
        Обрабатывает запрос пользователя и формирует ответ

        Args:
            query: Запрос пользователя
            conversation_history: История разговора
            user_id: ID пользователя
            **kwargs: Дополнительные аргументы

        Returns:
            str: Ответ на запрос
        """
        try:
            if conversation_history is None:
                conversation_history = []

            # Сохраняем запрос в истории разговора
            if user_id:
                self.memory_store.store_conversation(user_id, query, "user")

            # Начинаем цепочку рассуждений
            reasoning = self.reason(query, {"conversation_history": conversation_history})
            logger.info(f"Рассуждение: {reasoning}")

            # Сохраняем цепочку рассуждений в хранилище
            self.memory_store.store_reasoning_chain(self.name, query, reasoning)

            # Определяем эмоциональный тон сообщения
            sentiment = self.use_tool("detect_sentiment", query)
            logger.info(f"Эмоциональный тон: {sentiment}")

            # Определяем тип вопроса
            question_type = self.use_tool("identify_question_type", query)
            logger.info(f"Тип вопроса: {question_type}")

            # Обработка благодарностей
            if question_type.get(
                    "question_type") == "gratitude" or "спасиб" in query.lower() or "благодар" in query.lower():
                response = self.use_tool("respond_to_gratitude", conversation_history)

                # Сохраняем ответ в истории
                if user_id:
                    self.memory_store.store_conversation(user_id, response, "assistant")

                return response

            # Проверяем на запросы о волонтерстве и о боте
            lower_query = query.lower()
            bot_related_keywords = ["бот", "регистрация", "как", "куратор", "организатор", "запись", "мероприят",
                                    "регион", "город", "балл", "бонус", "волонтер", "волонтёр", "табельный", "меню",
                                    "код", "подтвержден"]

            volunteering_keywords = ["волонтерство", "волонтёрство", "благотворительность", "помощь", "добровольчество",
                                    "социальный", "экологический", "медицинский", "спортивный", "культурный"]

            if any(keyword in lower_query for keyword in bot_related_keywords) or \
                    any(keyword in lower_query for keyword in volunteering_keywords) or \
                    "что такое" in lower_query or "как" in lower_query:
                response = self.use_tool("get_general_info_about_volunteering", query)

                # Сохраняем ответ в истории
                if user_id:
                    self.memory_store.store_conversation(user_id, response, "assistant")

                return response

            # Выбираем наиболее подходящую роль в зависимости от запроса
            best_role = "consultant"  # По умолчанию

            if sentiment["mood"] == "негативное" or sentiment["emotion"] in ["грусть", "злость", "страх"]:
                best_role = "motivator"  # Для негативных эмоций лучше подходит мотиватор

            if question_type["question_type"] == "opinion":
                best_role = "mentor"  # Для запросов мнения подходит ментор

            if question_type["question_type"] == "procedural":
                best_role = "teacher"  # Для процедурных вопросов подходит учитель

            # Адаптируем роль агента
            self.adapt_role(best_role)

            # Добавляем всю информацию в память
            self.add_to_memory("sentiment", sentiment)
            self.add_to_memory("question_type", question_type)
            self.add_to_memory("selected_role", best_role)

            # Выполняем рефлексию
            reflection = self.reflect()
            logger.info(f"Рефлексия: {reflection}")

            # Формируем системный промпт с учетом выбранной роли
            role_description = self.available_roles.get(best_role, "эксперт в волонтёрстве")

            system_prompt = f"""
            Ты — {role_description}. Твоя задача - помогать пользователям в вопросах волонтёрства.

            Эмоциональный тон пользователя: {sentiment['mood']}, эмоция: {sentiment['emotion']}

            Отвечай дружелюбно, информативно и с учетом эмоционального состояния пользователя.
            Используй эмодзи для создания позитивной атмосферы.

            ВАЖНАЯ ИНФОРМАЦИЯ О БОТЕ:
            - Название: {get_bot_info('name')}
            - Описание: {get_bot_info('description')}
            - Процесс регистрации: Ввести пароль "Волонтёр", указать табельный номер, выбрать регион и интересы
            - Регистрация на мероприятия: В меню "Текущие мероприятия" выбрать мероприятие и нажать "Зарегистрироваться"
            - Виды волонтерства: {', '.join(get_bot_info('volunteering_types'))}
            - Подтверждение участия: После мероприятия нужно ввести код, который даёт организатор

            ВАЖНО: Отвечай ТОЛЬКО на вопросы, связанные с волонтерством, благотворительностью, 
            общественной деятельностью, социальной помощью и мероприятиями в этих сферах.

            Если вопрос не связан с этими темами, вежливо ответь, что ты специализируешься на темах 
            волонтерства и можешь помочь найти подходящие мероприятия или ответить на вопросы в этой сфере.

            Не обсуждай политику, религию, неоднозначные общественные вопросы, и не давай инструкций, 
            которые могут причинить вред.
            """

            # Формируем сообщения для запроса к LLM
            messages = [{"role": "system", "content": system_prompt}]

            # Добавляем историю разговора (ограничиваем последними 5 сообщениями)
            if conversation_history:
                messages.extend(conversation_history[-5:])

            # Добавляем текущий запрос
            messages.append({"role": "user", "content": query})

            # Формируем единый текстовый промпт из истории
            prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])

            response = self.llm.generate(prompt)

            # Сохраняем ответ в истории разговора
            if user_id:
                self.memory_store.store_conversation(user_id, response, "assistant")

            return response
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа: {e}")
            return self.safe_response(query,
                                    "Приношу извинения, но я специализируюсь на вопросах, связанных с волонтерством. Я могу помочь вам найти подходящие мероприятия, рассказать о волонтерстве или ответить на вопросы в этой сфере.")