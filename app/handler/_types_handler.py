# @description: 
# @author: licanglong
# @date: 2025/9/29 16:15

import threading
from collections import UserDict
from typing import Literal


class PropertyDict(UserDict):
    """
    增强版字典：
    - 继承自 UserDict，保留原生 dict 功能
    - 增加 getprop 方法，支持点分路径取值
    """

    def __init__(self, initial_data=None):
        super().__init__(initial_data or {})
        self._lock = threading.RLock()

    def merge(self, override: dict, none_mode: Literal['ignore', 'delete', 'override'] = 'ignore'):
        """
        递归合并 override 到 self.data
        :param none_mode:
            - 'ignore'  遇到 None 时跳过，不覆盖原值
            - 'delete'  遇到 None 时删除对应键
            - 'override' 默认行为，直接覆盖
        """

        def _merge(base, override):
            for k, v in override.items():
                if v is None:
                    if none_mode == 'ignore':
                        continue
                    elif none_mode == 'delete':
                        base.pop(k, None)
                        continue
                    # else 'override'，直接覆盖 None

                if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                    _merge(base[k], v)
                else:
                    base[k] = v

        with self._lock:
            _merge(self.data, override)

    def getprop(self, key: str, default=None, *, raise_error: bool = False, delimiter: str = "."):
        """
        从嵌套字典中获取指定 key 的值。
        - key 支持分隔符路径，例如 "database.host" -> config["database"]["host"]
        - 分隔符默认是 '.'，可以通过参数 delimiter 指定
        - 如果路径不存在，或最终值为 None，返回 default
        - 禁止 key 中出现空片段（如 "a..b"、".a"、"a."），一旦出现返回 default
        - raise_error=True 时，如果路径不存在则抛 KeyError
        """
        if not isinstance(self.data, dict):
            if raise_error:
                raise KeyError(f"Config is not a dict, cannot get key '{key}'")
            return default

        if not isinstance(key, str) or not key:
            if raise_error:
                raise KeyError(f"Invalid key: '{key}'")
            return default

        key_args = [p.strip() for p in key.split(delimiter)]
        if any(not part for part in key_args):  # 禁止空片段
            if raise_error:
                raise KeyError(f"Key contains empty segment: '{key}'")
            return default

        current = self.data
        for part in key_args:
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    if raise_error:
                        raise KeyError(f"Key path not found: '{key}'")
                    return default
            else:
                if raise_error:
                    raise KeyError(f"Key path not found: '{key}'")
                return default

        return default if current is None else current
