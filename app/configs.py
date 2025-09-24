# @description: 
# @author: licanglong
# @date: 2025/9/12 17:19
import os
import sys
from collections import UserDict

import yaml


class ConfigDict(UserDict):
    """
    增强版字典：
    - 继承自 UserDict，保留原生 dict 功能
    - 增加 getconfig 方法，支持点分路径取值
    """

    def getconfig(self, key: str, default=None, *, raise_error: bool = False):
        """
        从嵌套字典中获取指定 key 的值。
        - key 支持点分路径，例如 "database.host" -> config["database"]["host"]
        - 如果路径不存在，或最终值为 None，返回 default
        - 禁止 key 中出现空片段（如 "a..b"、".a"、"a."），一旦出现返回 default
        - raise_error=True 时，如果路径不存在则抛 KeyError
        """
        if not isinstance(self.data, dict):
            if raise_error:
                raise KeyError(f"Config is not a dict, cannot get key '{key}'")
            return default

        if not isinstance(key, str) or not key:
            if raise_error:
                raise KeyError(f"Invalid key: '{key}'")
            return default

        key_args = [p.strip() for p in key.split('.')]
        if any(not part for part in key_args):  # 禁止空片段
            if raise_error:
                raise KeyError(f"Key contains empty segment: '{key}'")
            return default

        current = self.data
        for part in key_args:
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    if raise_error:
                        raise KeyError(f"Key path not found: '{key}'")
                    return default
            else:
                # 中途不是 dict
                if raise_error:
                    raise KeyError(f"Key path not found: '{key}'")
                return default

        return default if current is None else current


def getpath(path: str) -> str:
    """
    获取资源绝对路径，支持开发环境和多种打包工具。

    params: path (str): 资源路径（绝对或相对）
    return: str: 资源绝对路径
    """
    if not path:
        raise ValueError("path can not empty")

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
    if not os.path.exists(abs_path):
        raise FileNotFoundError(abs_path)

    return abs_path


DEFAULT_CONFIG_FILE = "config/config.yml"
INIT_CONFIG: ConfigDict = ConfigDict({})


def init_config():
    """加载并初始化"""

    # 初始配置文件
    global INIT_CONFIG
    config_path = getpath(DEFAULT_CONFIG_FILE)
    if getattr(sys, 'frozen', False):
        extract_config_path = os.path.join(os.path.dirname(sys.executable), DEFAULT_CONFIG_FILE)
        if not os.path.exists(config_path):
            return
        # 如果文件不存在，解压并复制到当前工作目录
        if not os.path.exists(extract_config_path):
            os.makedirs(os.path.dirname(extract_config_path), exist_ok=True)
            # 避免权限问题：用二进制读写方式复制
            with open(config_path, 'rb') as fsrc, open(extract_config_path, 'wb') as fdst:
                fdst.write(fsrc.read())
        config_path = extract_config_path

    with open(config_path, 'r', encoding='utf-8') as ymlfile:
        INIT_CONFIG.update(yaml.safe_load(ymlfile) or {})
