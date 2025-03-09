import random
from .base import AIAgent
from database.core import Database

class RecommendationAgent(AIAgent):
    def __init__(self):
        self.db = Database()

    def process_query(self, query: str, user_id: int, **kwargs) -> str:
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, event_date, start_time, city FROM events")
            events = cursor.fetchall()
        if not events:
            return "На данный момент нет доступных мероприятий."
        events_list = random.sample(events, min(5, len(events)))
        recommendations = "\n\n".join([
            f"✨ {event[0]} – {event[1]} {event[2]} в {event[3]}"
            for event in events_list
        ])
        return f"Вот несколько мероприятий, которые могут вас заинтересовать:\n{recommendations}"
