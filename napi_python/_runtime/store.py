"""
Storage classes for handles, scopes, and references.

Reference: https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/Store.ts
"""

from typing import TypeVar, Generic, Optional, List, Callable, Any
from .disposable import Disposable

T = TypeVar("T")


class IdAllocator(Disposable):
    """Base ID allocator."""

    def acquire(self) -> int:
        raise NotImplementedError

    def release(self, id: int) -> None:
        raise NotImplementedError

    def dispose(self) -> None:
        pass


class CountIdAllocator(IdAllocator):
    """Simple counting ID allocator."""

    def __init__(self, initial_next: int = 1):
        self.next = initial_next

    def acquire(self) -> int:
        result = self.next
        self.next += 1
        return result

    def release(self, id: int) -> None:
        pass  # No reuse in simple counter


class CountIdReuseAllocator(CountIdAllocator):
    """ID allocator with reuse via free list."""

    def __init__(self, initial_next: int = 1):
        super().__init__(initial_next)
        self._free_list: List[int] = []

    def acquire(self) -> int:
        if self._free_list:
            return self._free_list.pop(0)
        return super().acquire()

    def release(self, id: int) -> None:
        self._free_list.append(id)

    def dispose(self) -> None:
        self._free_list.clear()
        super().dispose()


class BaseArrayStore(Generic[T], Disposable):
    """Base array-based storage."""

    def __init__(self, initial_capacity: int = 1):
        self._values: List[Optional[T]] = [None] * initial_capacity

    def assign(self, id: int, value: T) -> T:
        # Grow if needed
        while id >= len(self._values):
            self._values.extend([None] * (len(self._values) // 2 + 16))
        self._values[id] = value
        return value

    def deref(self, id: int) -> Optional[T]:
        if 0 <= id < len(self._values):
            return self._values[id]
        return None

    def dealloc(self, id: int) -> None:
        if 0 <= id < len(self._values):
            self._values[id] = None

    def dispose(self) -> None:
        for i in range(len(self._values)):
            self.dealloc(i)


class ArrayStore(BaseArrayStore[T]):
    """Array store with ID allocation."""

    def __init__(self, initial_capacity: int = 4):
        super().__init__(initial_capacity)
        self._allocator = CountIdReuseAllocator(1)

    def insert(self, value: Any) -> int:
        """Insert value and return its ID."""
        id = self._allocator.acquire()
        # Grow if needed
        while id >= len(self._values):
            cap = len(self._values)
            self._values.extend([None] * (cap // 2 + 16))
        # Set ID on value if it has an id attribute
        if hasattr(value, "id"):
            value.id = id
        self._values[id] = value
        return id

    def dealloc(self, id: int) -> None:
        self._allocator.release(id)
        super().dealloc(id)
