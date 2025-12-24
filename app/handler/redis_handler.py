# @description: 
# @author: licanglong
# @date: 2025/9/29 15:05
import logging
import threading
from typing import Any, Optional, List, Set, Union

import redis

log = logging.getLogger(__name__)


class RedisClient:
    """
    Redis 单例客户端封装 + 常用方法

    特性：
    - 线程安全单例
    - 支持 String, Hash, List, Set 基本操作
    - 支持 Key 操作（过期时间、TTL）
    - 支持获取分布式锁（Lock 对象）
    """

    _instance_lock = threading.Lock()
    _instance: "RedisClient" = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._instance_lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    # 使用连接池创建 redis.Redis 实例，提高性能
                    cls._instance._client = redis.Redis(connection_pool=redis.ConnectionPool(*args, **kwargs))
        return cls._instance

    @property
    def client(self) -> redis.Redis:
        """
        获取原生 redis.Redis 客户端实例。
        可以直接使用 Redis 的原生 API。
        """
        return self._client

    # ------------------- String 操作 -------------------
    def set(self, key: str, value: Any, ex: Optional[int] = None, nx: bool = False) -> Any:
        """
        设置键值对
        :param key: 键名
        :param value: 值
        :param ex: 过期时间，单位秒（可选）
        :param nx: True 表示仅在键不存在时设置
        :return: 设置是否成功
        """
        return self._client.set(name=key, value=value, ex=ex, nx=nx)

    def get(self, key: str) -> Any:
        """
        获取键对应的值
        :param key: 键名
        :return: 值，如果不存在返回 None
        """
        return self._client.get(name=key)

    def keys(self, pattern: str = "*") -> Any:
        """
        查找所有匹配指定模式的 key。

        :param pattern: 匹配模式，支持通配符:
                        '*' 匹配任意字符
                        '?' 匹配单个字符
                        '[a-z]' 匹配字符集合
        :return: key 列表
        """
        return self._client.keys(pattern)

    def delete(self, key: str) -> Any:
        """
        删除指定 key
        :param key: 键名
        :return: 删除的数量（0 或 1）
        """
        return self._client.delete(key)

    def exists(self, key: str) -> Any:
        """
        判断 key 是否存在
        :param key: 键名
        :return: True/False
        """
        return self._client.exists(key) > 0

    # ------------------- Hash 操作 -------------------
    def hset(self, name: str, key: str, value: Any) -> int:
        """
        Hash 设置字段值
        :param name: Hash 名
        :param key: 字段名
        :param value: 值
        :return: 新增字段数量
        """
        return self._client.hset(name, key, value)

    def hget(self, name: str, key: str) -> Optional[str]:
        """
        获取 Hash 中字段值
        :param name: Hash 名
        :param key: 字段名
        :return: 值，如果不存在返回 None
        """
        return self._client.hget(name, key)

    def hgetall(self, name: str) -> dict:
        """
        获取整个 Hash
        :param name: Hash 名
        :return: 字段-值字典
        """
        return self._client.hgetall(name)

    def hdel(self, name: str, *keys: str) -> int:
        """
        删除 Hash 中的字段
        :param name: Hash 名
        :param keys: 字段列表
        :return: 删除的字段数量
        """
        return self._client.hdel(name, *keys)

    # ------------------- List 操作 -------------------
    def lpush(self, name: str, *values: Any) -> int:
        """
        从左插入 List
        :param name: List 名
        :param values: 值
        :return: List 当前长度
        """
        return self._client.lpush(name, *values)

    def rpush(self, name: str, *values: Any) -> int:
        """
        从右插入 List
        :param name: List 名
        :param values: 值
        :return: List 当前长度
        """
        return self._client.rpush(name, *values)

    def lpop(self, name: str) -> Union[str, List, None]:
        """
        从左弹出 List 元素
        :param name: List 名
        :return: 弹出元素，如果为空返回 None
        """
        return self._client.lpop(name)

    def rpop(self, name: str) -> Union[str, List, None]:
        """
        从右弹出 List 元素
        :param name: List 名
        :return: 弹出元素，如果为空返回 None
        """
        return self._client.rpop(name)

    def lrange(self, name: str, start: int, end: int) -> list:
        """
        获取 List 指定范围元素
        :param name: List 名
        :param start: 起始索引
        :param end: 结束索引（-1 表示末尾）
        :return: 元素列表
        """
        return self._client.lrange(name, start, end)

    # ------------------- Set 操作 -------------------
    def sadd(self, name: str, *values: Any) -> int:
        """
        向 Set 添加元素
        :param name: Set 名
        :param values: 值
        :return: 新增元素数量
        """
        return self._client.sadd(name, *values)

    def srem(self, name: str, *values: Any) -> int:
        """
        从 Set 删除元素
        :param name: Set 名
        :param values: 值
        :return: 删除元素数量
        """
        return self._client.srem(name, *values)

    def smembers(self, name: str) -> Set:
        """
        获取 Set 所有元素
        :param name: Set 名
        :return: 元素集合
        """
        return self._client.smembers(name)

    # ------------------- Key 操作 -------------------
    def expire(self, key: str, time: int) -> Any:
        """
        设置 key 过期时间
        :param key: 键名
        :param time: 过期时间（秒）
        :return: 是否设置成功
        """
        return self._client.expire(key, time)

    def ttl(self, key: str) -> Any:
        """
        获取 key 剩余过期时间
        :param key: 键名
        :return: 剩余时间（秒），-2 表示不存在，-1 表示无过期时间
        """
        return self._client.ttl(key)

    # ------------------- 分布式锁 -------------------
    def lock(
            self,
            name: str,
            timeout: Optional[float] = None,
            sleep: float = 0.1,
            blocking: bool = True,
            blocking_timeout: Optional[float] = None,
            lock_class: Union[None, Any] = None,
            thread_local: bool = True,
    ):
        """
        获取一个 Redis 分布式锁对象，行为类似 threading.Lock。

        :param name: 锁名，对应 Redis key
        :param timeout: 锁最大持有时间（秒），超时自动释放。默认 None 表示直到 release() 才释放。
        :param sleep: 当锁被占用时，每次循环等待时间（秒），用于阻塞模式。
        :param blocking: acquire 是否阻塞等待锁，False 表示立即返回 False。
        :param blocking_timeout: 阻塞模式下获取锁的最大等待时间（秒）。None 表示一直等待。
        :param lock_class: 自定义锁实现类，默认使用 redis-py 的 Lock（Lua-based）。
        :param thread_local: 是否在线程本地存储锁 token，避免跨线程误释放。

        :return: redis.lock.Lock 对象，可调用 acquire/release。
        """
        return self._client.lock(
            name=name,
            timeout=timeout,
            sleep=sleep,
            blocking=blocking,
            blocking_timeout=blocking_timeout,
            lock_class=lock_class,
            thread_local=thread_local
        )
