# @description: 
# @author: licanglong
# @date: 2025/9/28 9:13
import time
from typing import Any, Optional, List


class Event:
    """事件基类，支持携带任意数据"""

    def __init__(self, source: Any = None, tags: Optional[List[str]] = None):
        self.source = source
        self.tags = tags or []
        self.timestamp = time.time()
