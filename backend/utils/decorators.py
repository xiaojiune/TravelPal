"""通用装饰器集合：legacy_only / placeholder / refactor 三态标记。

三者共同表达一个标记块的「生命周期状态」，语义区分：
- legacy_only 重在「要清理」：已废弃不再维护
- placeholder 重在「未激活/未明确」：存在但去向未定
- refactor 重在「要重构」：去向明确，重构方向已写进被标记函数 docstring

警告统一使用 UserWarning（开发层标记，默认可见；被误调用时能立即感知）。
"""

import functools
import warnings


def legacy_only(func):
    """标记仅作遗留参考的函数，调用时打印 UserWarning。

    特定概念：函数已废弃、不再维护，仅保留作参考或单元测试对照组；
    重在「要清理」——确认无任何调用方且无保留价值后，删除函数与标记。

    触发时机：确认无调用方且无保留价值 → 删函数与标记。
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        warnings.warn(
            f"{func.__name__} 已废弃，仅作参考保留",
            UserWarning,
            stacklevel=2,
        )
        return func(*args, **kwargs)

    return wrapper


def placeholder(func):
    """标记暂未激活的函数：存在但去向未定，预留供后续扩展。

    特定概念：功能可用但无调用方，且未来去向不明——可能是待接线、
    待重构但无明确方向、也可能最终删除；重在「未激活/未明确」。

    触发时机：接入真实调用方或重构方向明确 → 按新状态改标或移除标记；
    确定不需要 → 删除函数与标记。
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        warnings.warn(
            f"{func.__name__} 是未激活函数，去向未定（待接线/待重构/待删除）",
            UserWarning,
            stacklevel=2,
        )
        return func(*args, **kwargs)

    return wrapper


def refactor(func):
    """标记待重构函数：实现可用但结构需重写，重构方向已明确。

    特定概念：适用于「已实现但结构待优化」与「遗留代码但需重写」两类；
    重在「要重构」——重构方向写入被标记函数 docstring（以 TODO 醒目
    标注），不在本装饰器展开。

    触发时机：重构完成、新实现替换旧实现后 → 移除标记。
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        warnings.warn(
            f"{func.__name__} 是待重构函数，重构方向见其 docstring",
            UserWarning,
            stacklevel=2,
        )
        return func(*args, **kwargs)

    return wrapper
