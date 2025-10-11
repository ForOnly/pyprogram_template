# @description: 
# @author: licanglong
# @date: 2025/10/11 11:10

import logging
import os
import sys
import threading
from typing import Optional

from concurrent_log import ConcurrentTimedRotatingFileHandler

from app.handler import FileResolver, ConfigEnvironmentInstance, ColorConsoleFormatter
from app.utils.pathutils import getpath

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

    def __new__(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def _init_logger(self):
        logpath = App.ENV.getprop('log.path', App.DEFAULT_LOG_FILE)
        custom_stream_handler = logging.StreamHandler()
        if getattr(sys, 'frozen', False):  # 打包后的环境
            log_path = os.path.join(os.path.dirname(sys.executable), logpath)
        else:  # 开发环境
            custom_stream_handler.setFormatter(ColorConsoleFormatter())
            log_path = os.path.join(os.getenv('APP_PATH'), logpath)
        if not os.path.exists(os.path.dirname(log_path)):
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
        file_handler = ConcurrentTimedRotatingFileHandler(
            filename=log_path,
            when='midnight',  # 每天午夜切割
            backupCount=30,  # 保留最近30天的日志
            encoding='utf-8',
        )
        _log.info(f"日志文件路径：{log_path}")
        # 确保日志路径
        logging.basicConfig(
            level=App.ENV.getprop('log.level', logging.DEBUG),
            format="{asctime} {levelname:>7} {threadName:^10} [{filename}#{funcName}:{lineno}]: {message}",
            style="{",
            encoding='utf-8',
            handlers=[file_handler, custom_stream_handler],
            force=True
        )
        _log.info(f"日志级别：{logging.getLevelName(logging.getLogger().level)}")

    def _init_config(self):
        """加载并初始化"""

        # 初始配置文件
        config_path = getpath(App.DEFAULT_CONFIG_FILE, raise_error=False)
        if not os.path.exists(config_path):
            _log.warning(f"no config file：{App.DEFAULT_CONFIG_FILE}")
            return
        if getattr(sys, 'frozen', False):
            extract_config_path = os.path.join(os.path.dirname(sys.executable), App.DEFAULT_CONFIG_FILE)
            # 如果文件不存在，解压并复制到当前工作目录
            if not os.path.exists(extract_config_path):
                os.makedirs(os.path.dirname(extract_config_path), exist_ok=True)
                # 避免权限问题：用二进制读写方式复制
                with open(config_path, 'rb') as fsrc, open(extract_config_path, 'wb') as fdst:
                    fdst.write(fsrc.read())
            config_path = extract_config_path
        App.ENV.merge_source(FileResolver().resolve(config_path))

    def _init_nacos(self):
        from .handler import NacosClient, NacosResolver, ImportResolver
        nacos_clent = NacosClient(server_addresses=App.ENV.getprop("nacos.server.server_addresses", raise_error=True),
                                  namespace=App.ENV.getprop("nacos.server.namespace"),
                                  username=App.ENV.getprop("nacos.server.username", raise_error=True),
                                  password=App.ENV.getprop("nacos.server.password", raise_error=True))
        ImportResolver.register("nacos", NacosResolver(nacos_clent))

    def _init_app(self):  # noqa
        self._init_logger()
        self._init_config()
        # _init_nacos()

    def run(self):
        pass

    def start(self):
        self._init_app()
        self.run()
