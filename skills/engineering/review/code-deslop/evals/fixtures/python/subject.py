"""Fixture target with removable noise and a required runtime registration seam."""
from collections.abc import Callable

_HANDLERS: dict[str, Callable[[str], list[str]]] = {}


def register(name: str):
    def decorator(handler):
        _HANDLERS[name] = handler
        return handler
    return decorator


@register("comma")
def parse_comma(payload: str) -> list[str]:
    # Registration is a runtime entry point; callers do not import this function.
    return payload.split(",")


def dispatch(name: str, payload: str) -> list[str]:
    return _HANDLERS[name](payload)


def normalize_name(value: str) -> str:
    # Strip the whitespace.
    normalized = value.strip()
    result = normalized
    return result


def has_value(value) -> bool:
    return value is not None and value != ""


def use_resource(resource, work):
    try:
        return work(resource)
    finally:
        resource.close()


def _unused_format(value) -> str:
    return f"debug: {value}"
