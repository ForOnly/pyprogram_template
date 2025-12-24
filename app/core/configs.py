# @description: 
# @author: licanglong
# @date: 2025/12/23 13:52
import logging
import threading
from abc import ABC, abstractmethod
from pathlib import Path

import requests
import yaml

from app.core.events import Event, EM
from app.core.property import PropertyDict

CONFIG_IMPORT = "config.imports"
_log = logging.getLogger(__name__)


class ConfigEnvironment(PropertyDict):

    def merge_source(self, source):
        """接受 ConfigDataResource 对象"""
        if not hasattr(source, "load"):
            raise TypeError(f"Source must have load() method, got {type(source)}")
        data = source.load()
        if not isinstance(data, dict):
            data = {}

        # 自动提取 import
        imports = self.extract_imports(data)
        if imports:
            ImportResolver.add_imports(imports)

        self.merge(data)

    def extract_imports(self, data: dict) -> list:
        """
        从配置数据中提取 import 条目
        返回列表，如果没有 import 返回空列表
        """
        if not isinstance(data, dict):
            return []
        data_config = PropertyDict(data)
        return data_config.getprop(CONFIG_IMPORT, [])


class ConfigEnvironmentInstance:
    """
    ConfigEnvironment 的单例代理
    """
    _instance_lock = threading.Lock()
    _instance: ConfigEnvironment = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = ConfigEnvironment(*args, **kwargs)
        return cls._instance


class ConfigDataResource(ABC):
    @abstractmethod
    def load(self) -> dict:
        pass


class ConfigDataLocationResolver(ABC):
    @abstractmethod
    def resolve(self, location: str) -> ConfigDataResource:
        pass


class RegisterResolverEvent(Event):
    """
    注册解析器事件
    """

    def __init__(self, protocol, **kwargs):
        super().__init__(**kwargs)
        self.protocol = protocol


class ImportResolver:
    resolvers = {}  # protocol -> resolver
    cached_imports = []  # 未解析的 import 条目

    @classmethod
    def register(cls, protocol: str, resolver: ConfigDataLocationResolver):
        """注册解析器"""
        _log.info(f"Register resolver for protocol: {protocol}")
        cls.resolvers[protocol] = resolver
        EM.emit(RegisterResolverEvent(protocol))

    @classmethod
    def add_imports(cls, imports: list[str]):
        """添加新的 import 条目到缓存"""
        cls.cached_imports.extend(imports)
        for protocol in cls.resolvers.keys():
            EM.emit(RegisterResolverEvent(protocol))

    @classmethod
    def resolve(cls, import_str: str):
        if ":" not in import_str:
            cls.cached_imports.append(import_str)
            return None
        protocol, target = import_str.split(":", 1)
        if protocol not in cls.resolvers:
            cls.cached_imports.append(import_str)
            return None
        resolver = cls.resolvers[protocol]
        return resolver.resolve(target.strip())


class FileResource(ConfigDataResource):
    def __init__(self, path: str):
        self.path = Path(path)

    def load(self) -> dict:
        if not self.path.exists():
            return {}
        with open(self.path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        # if isinstance(data, dict) and "config" in data and isinstance(data["config"], dict):
        #     return data["config"]
        return data


class FileResolver(ConfigDataLocationResolver):
    def resolve(self, location: str) -> ConfigDataResource:
        return FileResource(location)


class HttpResource(ConfigDataResource):
    def __init__(self, url: str):
        self.url = url

    def load(self) -> dict:
        resp = requests.get(self.url)
        resp.raise_for_status()
        import yaml
        data = yaml.safe_load(resp.text) or {}
        if isinstance(data, dict) and "config" in data and isinstance(data["config"], dict):
            return data["config"]
        return data


class HttpResolver(ConfigDataLocationResolver):
    def resolve(self, location: str) -> ConfigDataResource:
        return HttpResource(location)
