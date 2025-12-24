# @description: 
# @author: licanglong
# @date: 2025/9/25 14:26
import logging
import threading
from typing import Callable, Optional, Dict

import nacos

from app.core import ConfigDataResource, ConfigDataLocationResolver
from app.handler.event_handler import ApplicationStartupEvent

log = logging.getLogger(__name__)


class NacosClient:
    _instance_lock = threading.Lock()
    _instance: Optional["NacosClient"] = None

    def __new__(cls, server_addresses: str, namespace: str = "", username: str = "", password: str = ""):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._client = nacos.NacosClient(
                        server_addresses=server_addresses,
                        namespace=namespace or "",
                        username=username,
                        password=password
                    )
        return cls._instance

    def get_config(self, data_id: str, group: str = "DEFAULT_GROUP") -> Optional[str]:
        """获取配置，可能返回 None"""
        try:
            return self._client.get_config(data_id, group)
        except Exception as e:
            log.error(f"获取配置失败 data_id={data_id}, group={group}: {e}")
            return None

    def add_listener(self, data_id: str, group: str, callback: Callable[[dict], None], log_change: bool = True):
        """
        添加配置变更监听器
        :param data_id: 配置 ID
        :param group: 分组
        :param callback: 回调函数，参数为 dict，包含 data_id, group, content 等
        :param log_change: 是否打印日志
        """

        def inner_callback(args: dict):
            if log_change:
                log.info(f"[配置变化] data_id={args.get('data_id')}, 内容={args.get('content')}")
            callback(args)

        try:
            self._client.add_config_watcher(data_id, group, inner_callback)
        except Exception as e:
            log.error(f"添加配置监听失败 data_id={data_id}, group={group}: {e}")

    def register_service(self, service_name: str, ip: str, port: int, metadata: Optional[Dict] = None, retry: int = 0):
        """
        注册服务到 Nacos
        :param service_name: 服务名
        :param ip: IP 地址
        :param port: 端口
        :param metadata: 可选元数据
        :param retry: 注册失败重试次数
        """
        for attempt in range(retry + 1):
            try:
                result = self._client.add_naming_instance(service_name=service_name, ip=ip, port=port,
                                                          metadata=metadata)
                if result:
                    log.info(f"成功注册服务到 Nacos：{service_name} ({ip}:{port})")
                    return True
                else:
                    log.warning(f"注册服务失败 {service_name} ({ip}:{port}), 第 {attempt + 1} 次尝试")
            except Exception as e:
                log.error(f"Nacos注册服务异常: {e}, 第 {attempt + 1} 次尝试")
        return False


# -----------------------------
# Nacos 配置源（支持热更新）
# -----------------------------
import yaml
import json


class NacosResource(ConfigDataResource):
    def __init__(self, client: NacosClient, data_id: str):
        self.client = client
        self.data_id = data_id
        self.latest_data = {}

    def load(self) -> dict:
        raw = self.client.get_config(self.data_id)
        if not raw:
            return {}

        data = {}
        # 尝试解析为 YAML
        try:
            data = yaml.safe_load(raw)
        except Exception:
            # 如果 YAML 解析失败，尝试 JSON
            try:
                data = json.loads(raw)
            except Exception:
                # 最终失败，返回空字典
                data = {}

        if not isinstance(data, dict):
            data = {}

        self.latest_data = data
        return data


class NacosResolver(ConfigDataLocationResolver):
    def __init__(self, client: NacosClient):
        self.client = client

    def resolve(self, location: str) -> ConfigDataResource:
        return NacosResource(self.client, location)


# @EM.subscribe(ApplicationStartupEvent, priority=sys.maxsize - 2)
def init_nacos_onstartup(event: ApplicationStartupEvent):
    """加载并初始化配置"""
    from app.handler import NacosClient, NacosResolver
    from app.core import ImportResolver, CTX
    nacos_clent = NacosClient(server_addresses=CTX.ENV.getprop("nacos.server.server_addresses", raise_error=True),
                              namespace=CTX.ENV.getprop("nacos.server.namespace"),
                              username=CTX.ENV.getprop("nacos.server.username", raise_error=True),
                              password=CTX.ENV.getprop("nacos.server.password", raise_error=True))
    ImportResolver.register("nacos", NacosResolver(nacos_clent))
