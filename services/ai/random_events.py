import random
from .base import AIAgent
from database.core import Database

class RandomEventsAgent(AIAgent):
    def __init__(self):
        self.db = Database()

    def process_query(self, query: str, **kwargs) -> str:
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, event_date, start_time, city FROM events")
            events = cursor.fetchall()
        if not events:
            return "На данный момент нет доступных мероприятий."
        selected_events = random.sample(events, min(5, len(events)))
        output = "\n\n".join([
            f"✨ {event[0]} – {event[1]} {event[2]} в {event[3]}"
            for event in selected_events
        ])
        return f"Случайные мероприятия:\n{output}"
