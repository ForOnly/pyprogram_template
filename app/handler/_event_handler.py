# @description: 
# @author: licanglong
# @date: 2025/9/29 10:37
import logging
import threading
import time
from collections import defaultdict
from typing import Any, Dict, Type, List, Callable, Optional


class Event:
    """事件基类，支持携带任意数据"""

    def __init__(self, source: Any = None, tags: Optional[List[str]] = None):
        self.source = source
        self.tags = tags or []
        self.timestamp = time.time()


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


class EventBus:
    """
    # ---------------------------
    # 事件总线
    # ---------------------------
    """

    def __init__(self):
        # 事件类型 -> list[Subscriber]
        self._subscribers: Dict[Type[Event], List[Subscriber]] = defaultdict(list)
        self._lock = threading.RLock()

    def subscribe(self, event_type: Type[Event], *,
                  condition: Optional[Callable[[Event], bool]] = None,
                  priority: int = 0,
                  async_: bool = False,
                  once: bool = False):
        """
         # -----------------------
        # 订阅装饰器
        # -----------------------
        :param event_type: 事件类型
        :param condition: 条件
        :param priority: 优先级
        :param async_: 异步模式
        :param once: 一次订阅
        :return:
        """

        def decorator(func: Callable):
            sub = Subscriber(func, event_type, condition, priority, async_, once)
            with self._lock:
                self._subscribers[event_type].append(sub)
                # 按优先级排序，优先级高先执行
                self._subscribers[event_type].sort(key=lambda s: -s.priority)
            return func

        return decorator

    def unsubscribe(self, event_type: Type[Event], callback: Callable):
        """
        # -----------------------
        # 注销订阅者
        # -----------------------
        :param event_type: 事件类型
        :param callback: 回调
        :return:
        """
        with self._lock:
            self._subscribers[event_type] = [
                s for s in self._subscribers[event_type] if s.callback != callback
            ]

    def emit(self, event: Event):
        """
        # -----------------------
        # 触发事件
        # -----------------------
        :param event: 事件
        :return:
        """
        event_type = type(event)
        subscribers_to_remove = []
        with self._lock:
            # 支持子类事件触发父类订阅
            applicable_subs = []
            for etype, subs in self._subscribers.items():
                if issubclass(event_type, etype):
                    applicable_subs.extend(subs)

        # 执行回调
        for sub in sorted(applicable_subs, key=lambda s: -s.priority):
            if sub.condition and not sub.condition(event):
                continue
            try:
                if sub.async_:
                    threading.Thread(target=sub.callback, args=(event,), daemon=True).start()
                else:
                    sub.callback(event)
            except Exception as e:
                logging.info(f"[EventBus] error in subscriber {sub.callback}: {e}")
            if sub.once:
                subscribers_to_remove.append(sub)

        # 移除一次性订阅
        for sub in subscribers_to_remove:
            self.unsubscribe(sub.event_type, sub.callback)

    def clear(self, event_type: Optional[Type[Event]] = None):
        """
        # -----------------------
        # 清理订阅者
        # -----------------------
        :param event_type:
        :return:
        """
        with self._lock:
            if event_type:
                self._subscribers[event_type] = []
            else:
                self._subscribers.clear()


class EventBusInstance:
    """
    EventBus 的单例类
    """
    _instance_lock = threading.Lock()
    _instance: Optional[EventBus] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._instance_lock:
                if not cls._instance:
                    cls._instance = EventBus()
        return cls._instance
