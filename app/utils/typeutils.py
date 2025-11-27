# @description: 
# @author: licanglong
# @date: 2025/6/9 11:39
import json
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
        type_registry[(to_type, from_type)] = converter_func

    as_dataclass.register_type_converter = register_type_converter

    def _get_fields(c):
        if c not in _FIELD_CACHE:
            _FIELD_CACHE[c] = fields(c)
        return _FIELD_CACHE[c]

    def _convert_value(field_type, value, path="root", ignore_case_local: bool = True):
        if value is None:
            return None

        origin = get_origin(field_type) or getattr(field_type, "__origin__", None)
        args = get_args(field_type)

        # Union / Optional
        if origin is Union:
            non_none_args = [arg for arg in args if arg is not type(None)]
            # 优先尝试 dataclass
            for typ in non_none_args:
                if is_dataclass(typ):
                    try:
                        return _as_dataclass(typ, value, path, ignore_case_local)
                    except Exception:
                        continue
            # 尝试其他类型
            for typ in non_none_args:
                try:
                    return _convert_value(typ, value, path, ignore_case_local)
                except Exception:
                    continue
            return value

        # dataclass
        if is_dataclass(field_type):
            if not isinstance(value, dict):
                raise TypeError(f"{path}: Expected dict for dataclass {field_type}, got {type(value)}")
            return _as_dataclass(field_type, value, path, ignore_case_local)

        # 自定义类型转换器
        converter = type_registry.get((field_type, type(value)))
        if converter:
            return converter(value)

        # List
        if origin in (list, List):
            item_type = args[0] if args else Any
            if not isinstance(value, list):
                raise TypeError(f"{path}: Expected list, got {type(value)}")
            return [_convert_value(item_type, v, f"{path}[]", ignore_case_local) for v in value]

        # Tuple
        if origin in (tuple, Tuple):
            item_type = args[0] if args else Any
            if not isinstance(value, (list, tuple)):
                raise TypeError(f"{path}: Expected tuple/list, got {type(value)}")
            return tuple(_convert_value(item_type, v, f"{path}[]", ignore_case_local) for v in value)

        # Set / FrozenSet
        if origin in (set, Set):
            item_type = args[0] if args else Any
            if not isinstance(value, Iterable) or isinstance(value, str):
                raise TypeError(f"{path}: Expected iterable for set, got {type(value)}")
            return {_convert_value(item_type, v, f"{path}[]", ignore_case_local) for v in value}

        if origin in (frozenset, FrozenSet):
            item_type = args[0] if args else Any
            if not isinstance(value, Iterable) or isinstance(value, str):
                raise TypeError(f"{path}: Expected iterable for frozenset, got {type(value)}")
            return frozenset(_convert_value(item_type, v, f"{path}[]", ignore_case_local) for v in value)

        # Dict
        if origin in (dict, Dict):
            key_type, val_type = args if args else (Any, Any)
            if not isinstance(value, dict):
                raise TypeError(f"{path}: Expected dict, got {type(value)}")
            #  修复：在嵌套 Dict 时继续传递 ignore_case_local，保证内部 dataclass 解析依然大小写不敏感
            return {k: _convert_value(val_type, v, f"{path}[{k}]", ignore_case_local) for k, v in value.items()}

        # datetime
        if field_type is datetime and isinstance(value, str):
            return datetime.fromisoformat(value)

        # Decimal
        if field_type is Decimal:
            return Decimal(str(value))

        return value

    def _as_dataclass(cls_inner, data_inner, path="root", ignore_case_local: bool = True):
        if not is_dataclass(cls_inner):
            raise TypeError(f"{cls_inner} must be a dataclass")
        if not isinstance(data_inner, dict):
            raise TypeError(f"{path}: Expected dict, got {type(data_inner)}")

        data_map = {k.lower(): v for k, v in data_inner.items()} if ignore_case_local else data_inner
        kwargs = {}
        for field in _get_fields(cls_inner):
            name = field.name
            field_type = field.type
            key = name.lower() if ignore_case_local else name
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

            kwargs[name] = _convert_value(field_type, value, f"{path}.{name}", ignore_case_local)

        return cls_inner(**kwargs)

    # 默认简单类型转换
    register_type_converter(str, int, lambda v: int(v))
    register_type_converter(int, str, lambda v: str(v))
    register_type_converter(float, int, lambda v: round(v))

    #  新增：支持 List / Dict / Set 等容器类型作为顶层类型
    root_origin = get_origin(cls)
    if root_origin in (list, List, tuple, Tuple, set, Set, frozenset, FrozenSet, dict, Dict, Union):
        #  传递 ignore_case 参数，确保顶层容器内 dataclass 也能无视 key 大小写
        return _convert_value(cls, data, "root", ignore_case)

    return _as_dataclass(cls, data, "root", ignore_case)


def asjson(data: dict):
    """转为 JSON 字符串（QML 最安全）"""

    def datetime_serializable(obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        return None  # 继续下一个规则

    def set_serializable(obj):
        if isinstance(obj, set):
            return list(obj)  # 将 set 转换为 list
        return None

    def default_serializable(obj):
        # 默认的序列化方式，返回 None 让 json 处理其他类型
        return None

    # 注册所有序列化规则
    serializers = {
        datetime: datetime_serializable,
        set: set_serializable,
    }

    # 处理自定义序列化的函数
    def custom_serializer(obj):
        # 查找适用的自定义序列化规则
        for typ, serializer in serializers.items():
            if isinstance(obj, typ):
                return serializer(obj)  # 使用对应类型的序列化方法
        return default_serializable(obj)  # 如果没有找到，则使用默认序列化

    return json.dumps(data, ensure_ascii=False, default=custom_serializer)
