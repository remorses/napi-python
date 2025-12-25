"""
Scope store for managing nested handle scopes.

Reference: https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/ScopeStore.ts
"""

from typing import Optional, TYPE_CHECKING

from .store import BaseArrayStore
from .handle_scope import HandleScope

if TYPE_CHECKING:
    from .handle import HandleStore


class ScopeStore(BaseArrayStore[HandleScope]):
    """
    Manages a stack of nested handle scopes.

    Scopes are nested like a call stack - opening a new scope
    creates a child of the current scope.
    """

    def __init__(self, handle_store: "HandleStore"):
        super().__init__()
        self._handle_store = handle_store

        # Root scope (never closed)
        self._root_scope = HandleScope(
            parent=None, handle_store=handle_store, start=1, end=handle_store.MIN_ID
        )
        self._root_scope.id = 0
        self.current_scope = self._root_scope

    def open_scope(self) -> HandleScope:
        """Open a new handle scope."""
        current = self.current_scope

        # Try to reuse existing child scope
        scope = current.child
        if scope is not None:
            scope.reuse(current)
        else:
            scope = HandleScope(current, self._handle_store)
            scope.id = current.id + 1
            self._values.append(scope)

        self.current_scope = scope
        return scope

    def close_scope(self) -> None:
        """Close the current scope."""
        scope = self.current_scope
        if scope.parent is not None:
            self.current_scope = scope.parent
        scope.dispose()

    def is_empty(self) -> bool:
        """Check if we're at the root scope."""
        return self.current_scope is self._root_scope

    def deref(self, scope_id: int) -> Optional[HandleScope]:
        """Get scope by ID."""
        if scope_id == 0:
            return self._root_scope
        if 0 < scope_id < len(self._values):
            return self._values[scope_id]
        return None
