"""通用装饰器集合。"""

import functools
import warnings


def deprecated(func):
    """标记函数已废弃的装饰器，调用时打印 DeprecationWarning。

    用法:
        @deprecated
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
