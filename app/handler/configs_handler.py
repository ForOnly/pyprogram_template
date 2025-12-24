# @description: 
# @author: licanglong
# @date: 2025/10/11 10:44
import logging
import os
import sys

from app.core import ImportResolver, FileResolver, HttpResolver, EM, RegisterResolverEvent
from app.handler.event_handler import ApplicationStartupEvent
from app.utils.pathutils import getpath

_log = logging.getLogger(__name__)

ImportResolver.register("file", FileResolver())
ImportResolver.register("http", HttpResolver())


@EM.subscribe(RegisterResolverEvent, priority=10)
def on_register_resolver(event: RegisterResolverEvent):
    """
    注册解析器
    """
    from app.core import CTX
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
            CTX.ENV.merge_source(resource)
        else:
            remaining.append(imp)
    ImportResolver.cached_imports = remaining


@EM.subscribe(ApplicationStartupEvent, priority=sys.maxsize - 1)
def init_config_onstartup(event: ApplicationStartupEvent):
    """加载并初始化配置"""
    from app.core import CTX
    # 初始配置文件
    config_path = getpath(CTX.DEFAULT_CONFIG_FILE, raise_error=False)
    if not os.path.exists(config_path):
        _log.warning(f"no config file：{CTX.DEFAULT_CONFIG_FILE}")
        return
    if getattr(sys, 'frozen', False):
        extract_config_path = os.path.join(os.path.dirname(sys.executable), CTX.DEFAULT_CONFIG_FILE)
        # 如果文件不存在，解压并复制到当前工作目录
        if not os.path.exists(extract_config_path):
            os.makedirs(os.path.dirname(extract_config_path), exist_ok=True)
            # 避免权限问题：用二进制读写方式复制
            with open(config_path, 'rb') as fsrc, open(extract_config_path, 'wb') as fdst:
                fdst.write(fsrc.read())
        config_path = extract_config_path
    CTX.ENV.merge_source(FileResolver().resolve(config_path))
