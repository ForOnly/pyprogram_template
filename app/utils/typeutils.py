# @description: 
# @author: licanglong
# @date: 2025/6/9 11:39

from dataclasses import is_dataclass, fields, MISSING
from datetime import datetime
from decimal import Decimal
from typing import Type, TypeVar, get_args, get_origin, Union, List, Tuple, Dict, Any, Set, Iterable, FrozenSet

T = TypeVar('T')


def as_dataclass(cls: Type[T], data, ignore_case: bool = True) -> T:
    """
    将 dict / list / Dict[str, dict] 转换为 dataclass 实例，支持嵌套和类型转换。

    特性：
    - 支持 dataclass、List、Tuple、Set、FrozenSet、Dict、Union 类型。
    - 支持嵌套 dataclass、datetime、Decimal 转换。
    - 支持通过 `as_dataclass.register_type_converter` 注册自定义类型转换器。
    - ignore_case=True 时，支持字典 key 不区分大小写。

    参数：
        cls: 目标 dataclass 类型
        data: 输入数据 (dict, list 等)
        ignore_case: 是否忽略 dict key 大小写

    返回：
        cls 类型实例
    """

    # dataclass 字段缓存，提高性能
    _FIELD_CACHE = {}
    # 自定义类型转换注册表
    type_registry = {}

    def register_type_converter(from_type, to_type, converter_func):
        """
        注册自定义类型转换器
        示例：
            as_dataclass.register_type_converter(str, int, lambda v: int(v))
            as_dataclass.register_type_converter(Color, str, lambda v: v.hex)
        """
        type_registry[(to_type, from_type)] = converter_func

    def _get_fields(c):
        """获取 dataclass 字段并缓存"""
        if c not in _FIELD_CACHE:
            _FIELD_CACHE[c] = fields(c)
        return _FIELD_CACHE[c]

    def _convert_value(field_type, value, path="root"):
        """内部函数：将单个值转换为目标类型"""
        origin = get_origin(field_type) or getattr(field_type, "__origin__", None)
        args = get_args(field_type)

        if value is None:
            return None

        # 如果已经是目标类型，直接返回
        if isinstance(value, field_type):
            return value

        # 尝试匹配 (目标类型, 输入类型)
        converter = type_registry.get((field_type, type(value)))
        if converter:
            try:
                return converter(value)
            except Exception as e:
                raise TypeError(f"{path}: converter for {type(value)} -> {field_type} failed: {e}")

        # Union 类型处理
        if origin is Union:
            non_none_args = [arg for arg in args if arg is not type(None)]
            for typ in non_none_args:
                try:
                    return _convert_value(typ, value, path)
                except Exception:
                    continue
            return value

        # List 类型
        if origin in (list, List):
            item_type = args[0] if args else Any
            if not isinstance(value, list):
                raise TypeError(f"{path}: Expected list, got {type(value)}")
            return [_convert_value(item_type, item, f"{path}[]") for item in value]

        # Tuple 类型
        if origin in (tuple, Tuple):
            item_type = args[0] if args else Any
            if not isinstance(value, (tuple, list)):
                raise TypeError(f"{path}: Expected tuple/list, got {type(value)}")
            return tuple(_convert_value(item_type, item, f"{path}[]") for item in value)

        # Set / FrozenSet 类型
        if origin in (set, Set):
            item_type = args[0] if args else Any
            if not isinstance(value, Iterable):
                raise TypeError(f"{path}: Expected iterable for set, got {type(value)}")
            return {_convert_value(item_type, item, f"{path}[]") for item in value}

        if origin in (frozenset, FrozenSet):
            item_type = args[0] if args else Any
            if not isinstance(value, Iterable):
                raise TypeError(f"{path}: Expected iterable for frozenset, got {type(value)}")
            return frozenset(_convert_value(item_type, item, f"{path}[]") for item in value)

        # Dict 类型
        if origin in (dict, Dict):
            key_type, val_type = args if args else (Any, Any)
            if not isinstance(value, dict):
                raise TypeError(f"{path}: Expected dict, got {type(value)}")
            return {k: _convert_value(val_type, v, f"{path}[{k}]") for k, v in value.items()}

        # dataclass 类型
        if is_dataclass(field_type):
            if not isinstance(value, dict):
                raise TypeError(f"{path}: Expected dict for dataclass {field_type}, got {type(value)}")
            return _as_dataclass(field_type, value, path)

        # datetime 类型处理
        if field_type is datetime and isinstance(value, str):
            return datetime.fromisoformat(value)

        # Decimal 类型处理
        if field_type is Decimal:
            return Decimal(str(value))

        # 其他类型直接返回
        return value

    # --- 内部函数：将 dict 转换为 dataclass 实例 ---
    def _as_dataclass(cls_inner, data_inner, path="root"):
        origin = get_origin(cls_inner) or getattr(cls_inner, "__origin__", None)

        # 顶层 List
        if origin in (list, List):
            item_type = get_args(cls_inner)[0] if get_args(cls_inner) else Any
            if data_inner is None:
                return []
            if not isinstance(data_inner, list):
                raise TypeError(f"{path}: Expected list, got {type(data_inner)}")
            return [_convert_value(item_type, item, f"{path}[]") for item in data_inner]

        # 顶层 Dict
        if origin in (dict, Dict):
            key_type, val_type = get_args(cls_inner) if get_args(cls_inner) else (Any, Any)
            if data_inner is None:
                return {}
            if not isinstance(data_inner, dict):
                raise TypeError(f"{path}: Expected dict, got {type(data_inner)}")
            return {k: _convert_value(val_type, v, f"{path}[{k}]") for k, v in data_inner.items()}

        # 顶层 Union
        if origin is Union:
            args = get_args(cls_inner)
            non_none_args = [arg for arg in args if arg is not type(None)]
            for typ in non_none_args:
                try:
                    return _convert_value(typ, data_inner, path)
                except Exception:
                    continue
            return data_inner

        # dataclass
        if not is_dataclass(cls_inner):
            raise TypeError(f"{cls_inner} must be a dataclass or parseable type")
        if not isinstance(data_inner, dict):
            raise TypeError(f"{path}: data must be a dict, got {type(data_inner)}")

        # 忽略大小写映射
        data_map = {k.lower(): v for k, v in data_inner.items()} if ignore_case else data_inner
        kwargs = {}

        for field in _get_fields(cls_inner):
            name = field.name
            field_type = field.type
            key = name.lower() if ignore_case else name
            value = data_map.get(key, MISSING)

            if value is MISSING:
                if field.default is not MISSING:
                    continue
                elif field.default_factory is not MISSING:
                    kwargs[name] = field.default_factory()
                    continue
                else:
                    kwargs[name] = None
                    continue

            if value is None:
                if field.default_factory is not MISSING:
                    kwargs[name] = field.default_factory()
                else:
                    kwargs[name] = None
                continue

            kwargs[name] = _convert_value(field_type, value, f"{path}.{name}")

        return cls_inner(**kwargs)

    def _str_to_int(v):
        """str -> int，不能转换时抛异常"""
        if v is None:
            return None
        try:
            return int(v)
        except Exception:
            raise ValueError(f"Cannot convert value '{v}' to int")

    # 暴露注册接口
    as_dataclass.register_type_converter = register_type_converter

    # 注册
    register_type_converter(str, int, _str_to_int)
    register_type_converter(int, str, lambda v: str(v))
    register_type_converter(float, int, lambda v: round(v))

    # 执行转换
    return _as_dataclass(cls, data)
