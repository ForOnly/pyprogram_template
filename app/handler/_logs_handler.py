# @description: 
# @author: licanglong
# @date: 2025/10/11 11:11
import logging
import os
import sys

from concurrent_log import ConcurrentTimedRotatingFileHandler

from app.core import EventBusInstance, ColorConsoleFormatter
from app.handler._event_handler import ApplicationStartupEvent

_EM = EventBusInstance()
_log = logging.getLogger(__name__)

custom_stream_handler = logging.StreamHandler()
if not getattr(sys, 'frozen', False):  # 开发环境
    custom_stream_handler.setFormatter(ColorConsoleFormatter())
# 确保日志路径
logging.basicConfig(
    level=logging.INFO,
    format="{asctime} {levelname:>7} {threadName:^10} [{filename}#{funcName}:{lineno}]: {message}",
    style="{",
    encoding='utf-8',
    handlers=[custom_stream_handler]
)


@_EM.subscribe(ApplicationStartupEvent, priority=sys.maxsize)
def init_logger_onstartup(event: ApplicationStartupEvent):
    """加载并初始化配置"""
    from app.App import App
    _APP = App()
    logpath = _APP.ENV.getprop('log.path', _APP.DEFAULT_LOG_FILE)
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
        level=_APP.ENV.getprop('log.level', logging.DEBUG),
        format="{asctime} {levelname:>7} {threadName:^10} [{filename}#{funcName}:{lineno}]: {message}",
        style="{",
        encoding='utf-8',
        handlers=[file_handler, custom_stream_handler],
        force=True
    )
    _log.info(f"日志级别：{logging.getLevelName(logging.getLogger().level)}")
