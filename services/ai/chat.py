from langchain.llms import BaseLLM
import requests

class GigachatLLM(BaseLLM):
    """
    Простейшая обертка для работы с Gigachat через API.
    """
    def __init__(self, api_key, endpoint):
        """
        :param api_key: API ключ для Gigachat.
        :param endpoint: URL эндпоинта Gigachat.
        """
        self.api_key = api_key
        self.endpoint = endpoint

    @property
    def _llm_type(self) -> str:
        return "gigachat"

    def _call(self, prompt, stop=None):
        """
        Отправляет запрос к Gigachat API.
        """
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {"prompt": prompt, "stop": stop}
        response = requests.post(self.endpoint, json=data, headers=headers)
        if response.status_code == 200:
            return response.json().get("response", "")
        else:
            raise Exception(f"Ошибка Gigachat API: {response.status_code} {response.text}")

class ChatService:
    def __init__(self, api_key, endpoint):
        """
        Инициализирует чат-сервис с использованием GigachatLLM.
        """
        self.llm = GigachatLLM(api_key, endpoint)

    def chat(self, prompt):
        """
        Генерирует ответ на заданный prompt.
        """
        return self.llm(prompt)
