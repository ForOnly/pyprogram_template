# @description: 日志处理
# @author: licanglong
# @date: 2025/5/8 16:33
import logging
import sys


class ColorConsoleFormatter(logging.Formatter):
    """
    日志模块自定义输出配置
    配置控制台输出的日志颜色
    """

    # ANSI 转义序列颜色代码
    WHITE = " \x1b[0;1m"
    GREY = " \x1b[37;1m"
    YELLOW = " \x1b[33;1m"
    RED = " \x1b[31;1m"
    GREEN = " \x1b[32;1m"
    BLUE = " \x1b[34;1m"
    RESET = " \x1b[0m"

    COMMON_SUFFIX = WHITE + "[{threadName:^10}]" + BLUE + "{location}:"
    FORMATS = {
        logging.DEBUG: WHITE + "{asctime}" + GREY + "{levelname:>7}" + COMMON_SUFFIX + GREY + "{message}" + RESET,
        logging.INFO: WHITE + "{asctime}" + GREEN + "{levelname:>7}" + COMMON_SUFFIX + WHITE + "{message}" + RESET,
        logging.WARNING: WHITE + "{asctime}" + YELLOW + "{levelname:>7}" + COMMON_SUFFIX + YELLOW + "{message}" + RESET,
        logging.WARN: WHITE + "{asctime}" + YELLOW + "{levelname:>7}" + COMMON_SUFFIX + YELLOW + "{message}" + RESET,
        logging.ERROR: WHITE + "{asctime}" + RED + "{levelname:>7}" + COMMON_SUFFIX + RED + "{message}" + RESET,
        logging.CRITICAL: WHITE + "{asctime}" + RED + "{levelname:>7}" + COMMON_SUFFIX + RED + "{message}" + RESET,
    }

    def __init__(self):
        super().__init__(datefmt="%Y-%m-%d %H:%M:%S")
        # 预创建各级别的 Formatter，避免重复实例化
        self._formatters = {}
        for level, formats in self.FORMATS.items():
            self._formatters[level] = logging.Formatter(formats, style="{", datefmt=self.datefmt)

    def format(self, record: logging.LogRecord) -> str:
        location = f"{record.filename}:{record.funcName}:{record.lineno}"
        record.location = f"{location:<40}"
        formatter = self._formatters.get(record.levelno, self._formatters[logging.INFO])
        return formatter.format(record)


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
