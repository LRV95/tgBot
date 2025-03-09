from .base import AIAgent
from .recommendation import RecommendationAgent
from .dialogue import DialogueAgent
from .event_info import EventInfoAgent
from .random_events import RandomEventsAgent


class ContextRouterAgent(AIAgent):
    def __init__(self):
        self.recommendation_agent = RecommendationAgent()
        self.dialogue_agent = DialogueAgent()
        self.event_info_agent = EventInfoAgent()
        self.random_events_agent = RandomEventsAgent()

    def process_query(self, query: str, user_id: int = None, conversation_history: list = None, **kwargs) -> str:
        lower_query = query.lower()
        # Простейшая логика определения темы запроса:
        if "информация" in lower_query or "подробнее" in lower_query:
            topic = "event_info"
        elif "рекомендация" in lower_query:
            topic = "events_recommendation"
        elif "случайное" in lower_query or "рандом" in lower_query:
            topic = "random_events"
        else:
            topic = "small_talk"

        if topic == "event_info":
            return self.event_info_agent.process_query(query)
        elif topic == "events_recommendation":
            return self.recommendation_agent.process_query(query, user_id)
        elif topic == "random_events":
            return self.random_events_agent.process_query(query)
        else:
            return self.dialogue_agent.process_query(query, conversation_history)
