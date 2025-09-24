# @description: 
# @author: licanglong
# @date: 2025/9/24 14:04
def init_app():  # noqa
    from .configs import init_config

    # 初始化配置文件
    init_config()

    from .logs import init_logger

    # 初始化日志配置
    init_logger()


init_app()  # noqa