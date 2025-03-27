import time
import requests
import logging
from config import AUTHORIZATION_KEY, GIGACHAT_TOKEN_URL, GIGACHAT_API_URL, MODEL_NAME, TEMPERATURE

logger = logging.getLogger(__name__)

class GigaChatLLM:
    def __init__(self, temperature: float = TEMPERATURE, max_tokens: int = 150):
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.access_token = None
        self.token_expires_at = 0

    def get_access_token(self) -> str:
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token

        payload = {
            'scope': 'GIGACHAT_API_PERS'
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'RqUID': 'ae35b651-55c5-4baa-9e31-9c9a798ad099',
            f'Authorization': f'Basic {AUTHORIZATION_KEY}'
        }

        try:
            response = requests.request("POST", GIGACHAT_TOKEN_URL, headers=headers, data=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении токена: {e}")
            raise Exception(f"Ошибка при получении токена: {e}")

        token_data = response.json()
        self.access_token = token_data.get('access_token')
        expires_in = token_data.get('expires_in', 3600)
        self.token_expires_at = time.time() + expires_in
        return self.access_token

    def generate(self, prompt: str) -> str:
        token = self.get_access_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
        }

        # Добавление инструкций безопасности к промпту
        safety_wrapper = """
        Ты - помощник по волонтерству и благотворительности. Ты должен помогать пользователям находить 
        подходящие мероприятия и отвечать на их вопросы о волонтерстве.

        Ты знаешь, что:
        - Для регистрации нужно ввести пароль "Волонтёр", затем табельный номер, выбрать регион и интересы
        - Регистрация на мероприятия происходит через меню "Текущие мероприятия"
        - После мероприятия нужно ввести код подтверждения, который даёт организатор
        - За участие в мероприятиях волонтеры получают баллы
        - В боте есть лидерборд, показывающий рейтинг волонтеров по регионам

        ВАЖНО: Когда пользователь просит рекомендовать мероприятия, рекомендуй ТОЛЬКО конкретные
        мероприятия, которые указаны в предоставленной информации, а не придумывай новые.

        ВАЖНО: Если пользователь меняет тему разговора и больше не спрашивает о мероприятиях, 
        не пытайся вернуть разговор к теме волонтерства. Реагируй на фактический запрос пользователя.

        Если запрос пользователя совсем не связан с волонтерством, ты можешь ответить на него,
        а затем мягко напомнить, что твоя основная функция - помощь в вопросах волонтерства.

        Вот запрос пользователя:
        """

        enhanced_prompt = safety_wrapper + "\n\n" + prompt

        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": enhanced_prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        try:
            response = requests.post(GIGACHAT_API_URL, headers=headers, json=payload, verify=False)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при запросе к GigaChat API: {e}")
            raise Exception(f"Ошибка при запросе к GigaChat API: {e}")

        result = response.json()
        try:
            response_text = result.get("choices", [])[0].get("message", {}).get("content", "").strip()

            # Проверяем, содержит ли ответ отказ обсуждать неподходящие темы
            refusal_phrases = [
                "не могу ответить", "не отвечаю", "не обсуждаю", "вне моей компетенции",
                "не связано с волонтерством", "не относится к теме", "не имеет отношения"
            ]

            if any(phrase in response_text.lower() for phrase in refusal_phrases):
                return "Я специализируюсь на темах волонтерства и могу помочь вам найти подходящие мероприятия или ответить на вопросы в этой сфере. Чем я могу помочь вам в контексте волонтерской деятельности?"

            return response_text
        except Exception as e:
            logger.error(f"Ошибка при обработке ответа от GigaChat API: {e}")
            return "Извините, произошла ошибка при обработке вашего запроса. Я могу помочь вам с вопросами о волонтерстве и мероприятиях. Пожалуйста, задайте вопрос еще раз."