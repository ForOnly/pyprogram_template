# @description: 
# @author: licanglong
# @date: 2025/10/11 10:44
import logging
import os
import sys
import threading
from abc import ABC, abstractmethod
from pathlib import Path

import requests
import yaml

from app.core import PropertyDict, EventBusInstance, Event
from app.handler._event_handler import ApplicationStartupEvent
from app.utils.pathutils import getpath

CONFIG_IMPORT = "config.imports"
_EM = EventBusInstance()
_log = logging.getLogger(__name__)


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
        _log.info(f"Register resolver for protocol: {protocol}")
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


@_EM.subscribe(ApplicationStartupEvent, priority=sys.maxsize - 1)
def init_config_onstartup(event: ApplicationStartupEvent):
    """加载并初始化配置"""
    from app.App import App
    _APP = App()
    # 初始配置文件
    config_path = getpath(_APP.DEFAULT_CONFIG_FILE, raise_error=False)
    if not os.path.exists(config_path):
        _log.warning(f"no config file：{_APP.DEFAULT_CONFIG_FILE}")
        return
    if getattr(sys, 'frozen', False):
        extract_config_path = os.path.join(os.path.dirname(sys.executable), _APP.DEFAULT_CONFIG_FILE)
        # 如果文件不存在，解压并复制到当前工作目录
        if not os.path.exists(extract_config_path):
            os.makedirs(os.path.dirname(extract_config_path), exist_ok=True)
            # 避免权限问题：用二进制读写方式复制
            with open(config_path, 'rb') as fsrc, open(extract_config_path, 'wb') as fdst:
                fdst.write(fsrc.read())
        config_path = extract_config_path
    _APP.ENV.merge_source(FileResolver().resolve(config_path))
