"""通用装饰器集合。"""

import functools
import warnings


def legacy_only(func):
    """标记仅作遗留参考的函数，调用时打印 DeprecationWarning。

    与 typing_extensions.deprecated 不同，此装饰器明确表示函数
    不再维护、不应被新代码调用，仅保留作参考或单元测试对照组。

    用法:
        @legacy_only
        def old_function():
            ...
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        warnings.warn(
            f"{func.__name__} 已废弃，仅作参考保留",
            DeprecationWarning,
            stacklevel=2,
        )
        return func(*args, **kwargs)

    return wrapper


def placeholder(func):
    """标记占位函数，表示功能已实现但尚未接入调用方，预留供后续扩展。

    与 legacy_only 不同，placeholder 表示"待接入的未来功能"，
    而非"已废弃的旧代码"。

    用法:
        @placeholder
        def future_feature():
            ...
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        warnings.warn(
            f"{func.__name__} 是占位函数，尚未接入实际调用",
            UserWarning,
            stacklevel=2,
        )
        return func(*args, **kwargs)

    return wrapper
