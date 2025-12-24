# @description: 
# @author: licanglong
# @date: 2025/10/11 11:10

import logging
import threading
from abc import ABC, abstractmethod
from typing import Optional

from app.core import EM
from app.handler import ApplicationStartupEvent

_log = logging.getLogger(__name__)


class App(ABC):
    """
    app 模块
    """

    _instance_lock = threading.Lock()
    _instance: Optional["App"] = None

    def __new__(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def startup(self):  # noqa
        EM.emit(ApplicationStartupEvent())

    @abstractmethod
    def run(self, *args, **kwargs):
        pass

    def start(self, *args, **kwargs):
        self.startup()
        self.run(*args, **kwargs)
