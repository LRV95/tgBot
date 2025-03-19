import logging
import traceback
from functools import wraps

logger = logging.getLogger(__name__)


class AIError(Exception):
    """Базовый класс для ошибок AI-агентов"""
    pass


class APIConnectionError(AIError):
    """Ошибка соединения с API"""
    pass


class APIResponseError(AIError):
    """Ошибка в ответе API"""
    pass


class DatabaseAccessError(AIError):
    """Ошибка доступа к базе данных"""
    pass


class ClassificationError(AIError):
    """Ошибка классификации запроса"""
    pass


def safe_ai_operation(
        default_response="Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."):
    """
    Декоратор для безопасного выполнения операций AI-агентов.
    Перехватывает все исключения, логирует их и возвращает дружественное сообщение.

    Args:
        default_response (str): Сообщение по умолчанию при возникновении ошибки
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except APIConnectionError as e:
                logger.error(f"Ошибка соединения с API: {e}")
                logger.debug(traceback.format_exc())
                return "Извините, не удалось подключиться к службе ИИ. Пожалуйста, попробуйте позже."
            except APIResponseError as e:
                logger.error(f"Ошибка в ответе API: {e}")
                logger.debug(traceback.format_exc())
                return "Извините, служба ИИ временно недоступна. Мы работаем над решением проблемы."
            except DatabaseAccessError as e:
                logger.error(f"Ошибка доступа к базе данных: {e}")
                logger.debug(traceback.format_exc())
                return "Извините, не удалось получить информацию о мероприятиях. Пожалуйста, попробуйте позже."
            except ClassificationError as e:
                logger.error(f"Ошибка классификации запроса: {e}")
                logger.debug(traceback.format_exc())
                return "Извините, не удалось точно понять ваш запрос. Пожалуйста, сформулируйте его иначе."
            except Exception as e:
                logger.error(f"Непредвиденная ошибка в {func.__name__}: {e}")
                logger.error(traceback.format_exc())
                return default_response

        return wrapper

    return decorator