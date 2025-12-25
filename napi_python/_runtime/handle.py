"""
Handle store for mapping integer IDs to Python values.

Reference: https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/Handle.ts
"""

from typing import Any, Optional, Dict
import weakref

from .store import BaseArrayStore, CountIdAllocator
from .disposable import Disposable
from .._napi.types import Constant


class HandleStore(BaseArrayStore):
    """
    Maps integer IDs to Python values.

    Constants 0-7 are reserved for special values (undefined, null, true, false, etc.)
    Regular handles start from MIN_ID (8).
    """

    MIN_ID = 8

    def __init__(self):
        super().__init__(self.MIN_ID)
        self._allocator = CountIdAllocator(self.MIN_ID)

        # Store for persistent/reference values (high bit set)
        self._ref_values: Dict[int, Any] = {}

        # Initialize constant values
        self._values[Constant.UNDEFINED] = Undefined
        self._values[Constant.NULL] = None
        self._values[Constant.FALSE] = False
        self._values[Constant.TRUE] = True
        self._values[Constant.GLOBAL] = GlobalObject()
        self._values[Constant.EMPTY_STRING] = ""

    @property
    def next_id(self) -> int:
        """Get the next ID that will be allocated."""
        return self._allocator.next

    def is_out_of_scope(self, id: int) -> bool:
        """Check if handle ID is beyond current scope."""
        return id >= self._allocator.next

    def push(self, value: Any) -> int:
        """Add a value and return its handle ID."""
        id = self._allocator.acquire()
        # Grow if needed
        while id >= len(self._values):
            self._values.extend([None] * (len(self._values) // 2 + 16))
        self._values[id] = value
        return id

    def get(self, id: int) -> Any:
        """Get value by handle ID."""
        # Check if it's a reference (high bit set)
        if id < 0 or id > 0x7FFFFFFF:
            ref_id = id & 0x7FFFFFFF
            ref = self._ref_values.get(ref_id)
            if ref is None:
                return None
            # Dereference if it's a weakref
            if isinstance(ref, weakref.ref):
                return ref()
            return ref

        if 0 <= id < len(self._values):
            value = self._values[id]
            # Check for weak reference
            if isinstance(value, weakref.ref) and self.is_out_of_scope(id):
                return value()
            return value
        return None

    def erase(self, start: int, end: int, weak: bool = False) -> None:
        """
        Erase handles in range [start, end).

        If weak=True, convert to weak references instead of deleting.
        """
        self._allocator.next = start

        if not weak:
            for i in range(start, end):
                if i < len(self._values):
                    self._values[i] = None
        else:
            # Convert to weak references where possible
            for i in range(start, end):
                if i < len(self._values):
                    value = self._values[i]
                    if value is not None:
                        try:
                            # Only objects can be weakly referenced
                            self._values[i] = weakref.ref(value)
                        except TypeError:
                            # Primitives can't be weakly referenced
                            pass

    def swap(self, a: int, b: int) -> None:
        """Swap values at two handle positions."""
        if a < len(self._values) and b < len(self._values):
            self._values[a], self._values[b] = self._values[b], self._values[a]

    def set_ref_value(self, id: int, value: Any) -> None:
        """Set a reference value (for persistent handles)."""
        self._ref_values[id] = value

    def get_ref_value(self, id: int) -> Any:
        """Get a reference value."""
        return self._ref_values.get(id)

    def delete_ref_value(self, id: int) -> None:
        """Delete a reference value."""
        self._ref_values.pop(id, None)


class Undefined:
    """Singleton representing JavaScript undefined."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "undefined"

    def __bool__(self):
        return False


# Singleton instance
Undefined = Undefined()


class GlobalObject(dict):
    """
    Global object that acts like JavaScript's globalThis.
    Used as a container for global properties.
    """

    def __init__(self):
        super().__init__()
        # Add some common global properties
        self["undefined"] = Undefined
        self["NaN"] = float("nan")
        self["Infinity"] = float("inf")

    def __repr__(self):
        return "<GlobalObject>"
