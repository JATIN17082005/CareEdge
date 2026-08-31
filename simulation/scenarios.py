import random

from simulation.events import EVENTS, apply_event


class ScenarioManager:
    def __init__(self):
        self.current_event = "normal"

    def set_event(self, event_name):
        if event_name not in EVENTS:
            raise ValueError(f"Unknown event: {event_name}")

        self.current_event = event_name

    def apply_current_event(self, reading):
        return apply_event(reading, self.current_event)

    def random_event(self):
        self.current_event = random.choice(list(EVENTS.keys()))
        return self.current_event

    def get_current_event(self):
        return self.current_event