import time
import requests
import logging
from config import AUTHORIZATION_KEY, GIGACHAT_TOKEN_URL, GIGACHAT_API_URL, MODEL_NAME, TEMPERATURE

logger = logging.getLogger(__name__)

class GigaChatLLM:
    def __init__(self, temperature: float = TEMPERATURE, max_tokens: int = 200):
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

        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
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
        return result.get("choices", [])[0].get("message", {}).get("content", "").strip()