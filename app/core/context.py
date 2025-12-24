# @description: 
# @author: licanglong
# @date: 2025/12/23 13:49
import threading
from typing import Optional

from app.core.configs import ConfigEnvironmentInstance


class AppContext:
    _instance_lock = threading.Lock()
    _instance: Optional["AppContext"] = None

    DEFAULT_CONFIG_FILE = "env/env.yml"
    DEFAULT_LOG_FILE = "logs/app.log"

    def __new__(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        self.ENV = ConfigEnvironmentInstance()
        self._initialized = True


CTX = AppContext()
