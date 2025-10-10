# @description: 
# @author: licanglong
# @date: 2025/9/24 14:04
import logging
import os
import sys

from concurrent_log import ConcurrentTimedRotatingFileHandler

import app.logs  # noqa
from .configs import getpath, FileResolver, ConfigEnvironmentInstance

ENV = ConfigEnvironmentInstance()
DEFAULT_CONFIG_FILE = "env/env.yml"


def _init_logger():
    logpath = ENV.getprop('log.path', 'logs/app.log')
    custom_stream_handler = logging.StreamHandler()
    if getattr(sys, 'frozen', False):  # 打包后的环境
        log_path = os.path.join(os.path.dirname(sys.executable), logpath)
    else:  # 开发环境
        custom_stream_handler.setFormatter(logs.ColorConsoleFormatter())
        log_path = os.path.join(os.getenv('APP_PATH'), logpath)
    if not os.path.exists(os.path.dirname(log_path)):
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
    file_handler = ConcurrentTimedRotatingFileHandler(
        filename=log_path,
        when='midnight',  # 每天午夜切割
        backupCount=30,  # 保留最近30天的日志
        encoding='utf-8',
    )
    logging.info(f"日志文件路径：{log_path}")
    # 确保日志路径
    logging.basicConfig(
        level=ENV.getprop('log.level', logging.INFO),
        format="{asctime} {levelname:>7} {threadName:^10} [{filename}#{funcName}:{lineno}]: {message}",
        style="{",
        encoding='utf-8',
        handlers=[file_handler, custom_stream_handler],
        force=True
    )
    logging.info(f"日志级别：{logging.getLevelName(logging.getLogger().level)}")


def _init_config():
    """加载并初始化"""

    # 初始配置文件

    config_path = getpath(DEFAULT_CONFIG_FILE, raise_error=False)
    if not os.path.exists(config_path):
        logging.warning(f"no config file：{DEFAULT_CONFIG_FILE}")
        return
    if getattr(sys, 'frozen', False):
        extract_config_path = os.path.join(os.path.dirname(sys.executable), DEFAULT_CONFIG_FILE)
        # 如果文件不存在，解压并复制到当前工作目录
        if not os.path.exists(extract_config_path):
            os.makedirs(os.path.dirname(extract_config_path), exist_ok=True)
            # 避免权限问题：用二进制读写方式复制
            with open(config_path, 'rb') as fsrc, open(extract_config_path, 'wb') as fdst:
                fdst.write(fsrc.read())
        config_path = extract_config_path
    ENV.merge_source(FileResolver().resolve(config_path))


def _init_nacos():
    from .configs import ImportResolver
    from .handler import NacosClient, NacosResolver
    nacos_clent = NacosClient(server_addresses=ENV.getprop("nacos.server.server_addresses", raise_error=True),
                              namespace=ENV.getprop("nacos.server.namespace"),
                              username=ENV.getprop("nacos.server.username", raise_error=True),
                              password=ENV.getprop("nacos.server.password", raise_error=True))
    ImportResolver.register("nacos", NacosResolver(nacos_clent))


def init_app():  # noqa
    _init_logger()
    _init_config()
    # _init_nacos()


init_app()  # noqa
