from collections import defaultdict
import asyncio
from typing import Callable, DefaultDict, Type, List
from .event_base import Event

class EventBus:
    def __init__(self):
        self.handlers: DefaultDict[Type[Event], List[Callable]] = defaultdict(list)

    def subscribe(self, event_type: Type[Event], handler: Callable):
        self.handlers[event_type].append(handler)
        print(f"Handler {handler.__name__} subscribed to {event_type.__name__}")

    async def publish(self, event: Event):
        event_type = type(event)
        print(f"Publishing event {event_type.__name__} with data {event}")
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                await handler(event)

# Global instance of the EventBus
event_bus = EventBus() 