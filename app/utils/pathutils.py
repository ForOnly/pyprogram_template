# @description: 
# @author: licanglong
# @date: 2025/10/11 10:45

import logging
import os
import sys
from typing import Optional

_log = logging.getLogger(__name__)


def getpath(path: str, raise_error=True) -> Optional[str]:
    """
    获取资源绝对路径，支持开发环境和多种打包工具。

    params: path (str): 资源路径（绝对或相对）
    return: str: 资源绝对路径
    """
    if not path:
        _log.warning("path is empty")
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
