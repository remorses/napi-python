"""
Reference tracker for linked list of references.

Reference: https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/RefTracker.ts
"""

from typing import Optional, TYPE_CHECKING

from .disposable import Disposable


class RefTracker(Disposable):
    """
    Doubly-linked list node for tracking references.

    Used to track all references that need finalization
    when an environment is destroyed.
    """

    def __init__(self):
        self._next: Optional["RefTracker"] = None
        self._prev: Optional["RefTracker"] = None

    def link(self, list_head: "RefTracker") -> None:
        """Link this tracker into a list after the given head."""
        self._prev = list_head
        self._next = list_head._next
        if self._next is not None:
            self._next._prev = self
        list_head._next = self

    def unlink(self) -> None:
        """Remove this tracker from its list."""
        if self._prev is not None:
            self._prev._next = self._next
        if self._next is not None:
            self._next._prev = self._prev
        self._prev = None
        self._next = None

    def finalize(self) -> None:
        """Override in subclass to perform finalization."""
        pass

    def dispose(self) -> None:
        """Clean up this tracker."""
        self.unlink()

    @staticmethod
    def finalize_all(list_head: "RefTracker") -> None:
        """Finalize all trackers in the list."""
        while list_head._next is not None:
            list_head._next.finalize()
