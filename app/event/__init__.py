# @description: 
# @author: licanglong
# @date: 2025/9/28 9:12
import threading

from ._event import Event
from ._event_bus import EventBus
from ._subscriber import Subscriber

__all__ = ["Event", "EventBus", "Subscriber", "EventBusInstance"]


class EventBusInstance:
    """
    EventBus 的单例类
    """
    _instance_lock = threading.Lock()
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._instance_lock:
                if not cls._instance:
                    cls._instance = EventBus()
        return cls._instance
