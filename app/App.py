# @description: 
# @author: licanglong
# @date: 2025/10/11 11:10

import logging
import threading
from typing import Optional

from app.core import EventBusInstance
from app.handler import ConfigEnvironmentInstance, ApplicationStartupEvent

_log = logging.getLogger(__name__)


class App:
    """
    app 模块
    """
    ENV = ConfigEnvironmentInstance()
    DEFAULT_CONFIG_FILE = "env/env.yml"
    DEFAULT_LOG_FILE = "logs/app.log"

    _instance_lock = threading.Lock()
    _instance: Optional["App"] = None
    _EM = EventBusInstance()

    def __new__(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def startup(self):  # noqa
        self._EM.emit(ApplicationStartupEvent())

    def run(self):
        pass

    def start(self):
        self.startup()
        self.run()
