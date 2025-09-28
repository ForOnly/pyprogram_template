# @description: 
# @author: licanglong
# @date: 2025/9/28 9:14
from typing import Callable, Type, Optional

from ._event import Event


class Subscriber:
    """
    # ---------------------------
    # 订阅者信息
    # ---------------------------
    """

    def __init__(self, callback: Callable, event_type: Type[Event],
                 condition: Optional[Callable[[Event], bool]] = None,
                 priority: int = 0,
                 async_: bool = False,
                 once: bool = False):
        self.callback = callback
        self.event_type = event_type
        self.condition = condition
        self.priority = priority
        self.async_ = async_
        self.once = once
