# @description: 
# @author: licanglong
# @date: 2025/9/12 17:19
import logging
import os
import sys
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import requests
import yaml

from .handler import EventBusInstance, Event, PropertyDict

CONFIG_IMPORT = "config.imports"
_EM = EventBusInstance()


def getpath(path: str, raise_error=True) -> Optional[str]:
    """
    获取资源绝对路径，支持开发环境和多种打包工具。

    params: path (str): 资源路径（绝对或相对）
    return: str: 资源绝对路径
    """
    if not path:
        logging.warning("path is empty")
        if raise_error:
            raise ValueError("path is empty")
        return None

    path = os.path.normpath(path)

    # 绝对路径直接返回
    if os.path.isabs(path):
        abs_path = path
    else:
        # 判断打包环境
        if getattr(sys, "frozen", False):
            # PyInstaller/Nuitka/PyOxidizer 单文件模式
            base_path = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        else:
            # 开发环境：APP_PATH 或当前脚本目录
            base_path = os.getenv("APP_PATH", os.path.dirname(os.path.abspath(__file__)))
        abs_path = os.path.join(base_path, path)

    abs_path = os.path.normpath(abs_path)

    # 检查路径存在性（读资源时启用）
    if not os.path.exists(abs_path) and raise_error:
        if raise_error:
            raise FileNotFoundError(abs_path)
        return None

    return abs_path


class ConfigUpdateEvent(Event):
    """
    配置文件更新事件
    """
    pass


class RegisterResolverEvent(Event):
    """
    注册解析器事件
    """

    def __init__(self, protocol, **kwargs):
        super().__init__(**kwargs)
        self.protocol = protocol


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


_environment = ConfigEnvironmentInstance()


class ConfigDataResource(ABC):
    @abstractmethod
    def load(self) -> dict:
        pass


class ConfigDataLocationResolver(ABC):
    @abstractmethod
    def resolve(self, location: str) -> ConfigDataResource:
        pass


class ImportResolver:
    environment: ConfigEnvironment = None
    resolvers = {}  # protocol -> resolver
    cached_imports = []  # 未解析的 import 条目

    @classmethod
    def register(cls, protocol: str, resolver: ConfigDataLocationResolver):
        """注册解析器"""
        logging.info(f"Register resolver for protocol: {protocol}")
        cls.resolvers[protocol] = resolver
        _EM.emit(RegisterResolverEvent(protocol))

    @classmethod
    def add_imports(cls, imports: list[str]):
        """添加新的 import 条目到缓存"""
        cls.cached_imports.extend(imports)
        for protocol in cls.resolvers.keys():
            _EM.emit(RegisterResolverEvent(protocol))

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


ImportResolver.environment = _environment


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


ImportResolver.register("file", FileResolver())
ImportResolver.register("http", HttpResolver())


@_EM.subscribe(RegisterResolverEvent, priority=10)
def on_register_resolver(event: RegisterResolverEvent):
    """
    注册解析器
    """
    remaining = []
    for imp in ImportResolver.cached_imports:
        if not imp:
            continue
        if ":" not in imp:
            remaining.append(imp)
            continue
        pfx, target = imp.split(":", 1)
        if pfx == event.protocol:
            resolver = ImportResolver.resolvers[pfx]
            resource = resolver.resolve(target.strip())
            ImportResolver.environment.merge_source(resource)
        else:
            remaining.append(imp)
    ImportResolver.cached_imports = remaining
