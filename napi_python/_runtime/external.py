"""
External value wrapper for opaque native pointers.

Reference: https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/External.ts
"""

from typing import Any
import weakref


# WeakMap equivalent for storing external values
_external_values: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


class External:
    """
    Wrapper for opaque native pointer values.

    In JavaScript, External is used to wrap native pointers that
    should be opaque to JavaScript code. In Python, we use this
    to wrap ctypes pointers or integer addresses.
    """

    __slots__ = ()

    def __new__(cls, value: int):
        instance = object.__new__(cls)
        # Store value in weak map
        _external_values[instance] = value
        return instance

    def __repr__(self):
        value = _external_values.get(self, "<invalid>")
        return (
            f"<External {value:#x}>"
            if isinstance(value, int)
            else f"<External {value}>"
        )


def is_external(obj: Any) -> bool:
    """Check if object is an External."""
    return obj in _external_values


def get_external_value(external: External) -> int:
    """Get the native pointer value from an External."""
    if not is_external(external):
        raise TypeError("not external")
    return _external_values[external]
