"""
Handle scope for managing handle lifecycles.

Reference: https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/HandleScope.ts
"""

from typing import Optional, Any, List, TYPE_CHECKING
from dataclasses import dataclass, field

from .disposable import Disposable

if TYPE_CHECKING:
    from .handle import HandleStore


@dataclass
class CallbackInfo:
    """Information about the current callback invocation."""

    thiz: Any = None  # 'this' value
    holder: Any = None  # holder object
    data: int = 0  # callback data pointer
    args: List[Any] = field(default_factory=list)  # arguments
    fn: Any = None  # the function being called
    new_target: Any = None  # new.target value


class HandleScope(Disposable):
    """
    Scope for automatic handle cleanup.

    Handles created within a scope are automatically cleaned up
    when the scope is closed, unless escaped to parent scope.
    """

    def __init__(
        self,
        parent: Optional["HandleScope"],
        handle_store: "HandleStore",
        start: Optional[int] = None,
        end: Optional[int] = None,
    ):
        self.handle_store = handle_store
        self.id: int = 0
        self.parent = parent
        self.child: Optional["HandleScope"] = None

        # Handle range
        if start is None:
            start = parent.end if parent else 1
        if end is None:
            end = start

        self.start = start
        self.end = end

        # Link to parent
        if parent is not None:
            parent.child = self

        self._escape_called = False
        self.callback_info = CallbackInfo()

    @classmethod
    def create(
        cls,
        parent: Optional["HandleScope"],
        handle_store: "HandleStore",
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> "HandleScope":
        """Factory method for creating scopes."""
        return cls(parent, handle_store, start, end)

    def reuse(self, parent: "HandleScope") -> None:
        """Reuse this scope with a new parent."""
        self.start = self.end = parent.end
        self._escape_called = False
        self.callback_info = CallbackInfo()

    def add(self, value: Any) -> int:
        """Add a value to this scope and return its handle ID."""
        handle_id = self.handle_store.push(value)
        self.end = handle_id + 1
        return handle_id

    def add_external(self, data: int) -> int:
        """Add an external value wrapper."""
        from .external import External

        return self.add(External(data))

    def escape(self, handle: int) -> int:
        """
        Escape a handle to the parent scope.

        Returns the new handle ID in the parent scope, or 0 on error.
        """
        if handle < self.start or handle >= self.end:
            return handle  # Handle is not in this scope

        if self._escape_called:
            return 0  # Can only escape once

        self._escape_called = True

        if handle < self.start or handle >= self.end:
            return 0

        # Swap handle to start of scope, then move boundary
        id = self.start
        self.handle_store.swap(handle, id)
        self.start += 1

        if self.parent:
            self.parent.end += 1

        return id

    def escape_called(self) -> bool:
        """Check if escape has been called on this scope."""
        return self._escape_called

    def dispose(self) -> None:
        """Clean up handles in this scope."""
        # Determine if we should use weak references
        # (only if this is not a callback scope)
        weak = self.callback_info.fn is None

        if not weak:
            # Clear callback info
            self.callback_info = CallbackInfo()

        if self.start != self.end:
            self.handle_store.erase(self.start, self.end, weak)


class EscapableHandleScope(HandleScope):
    """
    A handle scope that allows escaping one handle to parent scope.

    Identical to HandleScope but semantically indicates escape intent.
    """

    pass
