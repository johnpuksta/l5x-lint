from __future__ import annotations

from collections.abc import Callable

CheckFn = Callable[..., list]

_registry: list[CheckFn] = []


def register(check: CheckFn) -> CheckFn:
    _registry.append(check)
    return check
