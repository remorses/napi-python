"""
Global context for the NAPI runtime.

Reference: https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/Context.ts
"""

from typing import Optional, Dict, Any, Callable, List
import asyncio

from .store import ArrayStore
from .handle import HandleStore
from .handle_scope import HandleScope, CallbackInfo
from .scope_store import ScopeStore
from .env import Env
from .ref_tracker import RefTracker
from .external import External, is_external, get_external_value
from .._napi.types import (
    napi_status,
    Constant,
    NODE_API_SUPPORTED_VERSION_MAX,
    NODE_API_DEFAULT_MODULE_API_VERSION,
    NAPI_VERSION_EXPERIMENTAL,
)


class CleanupHookCallback:
    """Cleanup hook callback data."""

    def __init__(self, env: Env, fn: Callable, arg: int, order: int):
        self.env = env
        self.fn = fn
        self.arg = arg
        self.order = order


class CleanupQueue:
    """Queue of cleanup hooks."""

    def __init__(self):
        self._hooks: List[CleanupHookCallback] = []
        self._counter = 0

    def empty(self) -> bool:
        return len(self._hooks) == 0

    def add(self, env: Env, fn: Callable, arg: int) -> None:
        """Add a cleanup hook."""
        # Check for duplicates
        for hook in self._hooks:
            if hook.env is env and hook.fn is fn and hook.arg == arg:
                raise ValueError("Cannot add same fn and arg twice")

        self._hooks.append(CleanupHookCallback(env, fn, arg, self._counter))
        self._counter += 1

    def remove(self, env: Env, fn: Callable, arg: int) -> None:
        """Remove a cleanup hook."""
        for i, hook in enumerate(self._hooks):
            if hook.env is env and hook.fn is fn and hook.arg == arg:
                self._hooks.pop(i)
                return

    def drain(self) -> None:
        """Execute all cleanup hooks in reverse order."""
        hooks = sorted(self._hooks, key=lambda h: -h.order)
        for hook in hooks:
            if callable(hook.fn):
                hook.fn(hook.arg)
            self._hooks.remove(hook)

    def dispose(self) -> None:
        self._hooks.clear()
        self._counter = 0


class Context:
    """
    Global context for the NAPI runtime.

    Manages:
    - Handle storage and scopes
    - Environment storage
    - Reference storage
    - Cleanup hooks
    """

    def __init__(self):
        self._is_stopping = False
        self._can_call_into_js = True

        # Stores
        self._handle_store = HandleStore()
        self._scope_store = ScopeStore(self._handle_store)
        self._env_store: ArrayStore[Env] = ArrayStore()
        self._ref_store: Dict[int, Any] = {}  # Reference objects by ID
        self._deferred_store: Dict[int, Any] = {}  # Deferred promises

        # Cleanup
        self._cleanup_queue = CleanupQueue()

        # ID counters
        self._next_ref_id = 1
        self._next_deferred_id = 1

        # Callback storage to prevent GC
        self._callback_refs: List[Any] = []

    def create_env(
        self,
        filename: str,
        module_api_version: int = NODE_API_DEFAULT_MODULE_API_VERSION,
    ) -> Env:
        """Create a new environment."""
        # Validate version
        if module_api_version < NODE_API_DEFAULT_MODULE_API_VERSION:
            module_api_version = NODE_API_DEFAULT_MODULE_API_VERSION
        elif module_api_version > NODE_API_SUPPORTED_VERSION_MAX:
            if module_api_version != NAPI_VERSION_EXPERIMENTAL:
                raise ValueError(
                    f"{filename} requires Node-API version {module_api_version}, "
                    f"but only version {NODE_API_SUPPORTED_VERSION_MAX} is supported"
                )

        env = Env(self, module_api_version, filename)
        env.id = self._env_store.insert(env)

        # Add cleanup hook
        self.add_cleanup_hook(env, lambda _: env.unref(), 0)

        return env

    def get_env(self, env_id: int) -> Optional[Env]:
        """Get environment by ID."""
        return self._env_store.deref(env_id)

    # Handle scope management

    def open_scope(self, env: Env) -> HandleScope:
        """Open a new handle scope."""
        scope = self._scope_store.open_scope()
        env.open_handle_scopes += 1
        return scope

    def close_scope(self, env: Env, scope: Optional[HandleScope] = None) -> None:
        """Close the current handle scope."""
        self._scope_store.close_scope()
        env.open_handle_scopes -= 1

    def get_current_scope(self) -> HandleScope:
        """Get the current handle scope."""
        return self._scope_store.current_scope

    def get_handle_scope(self, scope_id: int) -> Optional[HandleScope]:
        """Get handle scope by ID."""
        return self._scope_store.deref(scope_id)

    def get_callback_info(self, info_id: int) -> CallbackInfo:
        """Get callback info from scope ID."""
        scope = self._scope_store.deref(info_id)
        if scope:
            return scope.callback_info
        return CallbackInfo()

    # Value operations

    def napi_value_from_python(self, value: Any) -> int:
        """Convert Python value to napi_value handle."""
        # Check for constants
        if value is None:
            return Constant.NULL
        if value is False:
            return Constant.FALSE
        if value is True:
            return Constant.TRUE
        if value == "":
            return Constant.EMPTY_STRING

        # Check for undefined
        from .handle import Undefined

        if value is Undefined:
            return Constant.UNDEFINED

        # Check for global
        if isinstance(value, dict) and value is self._handle_store.get(Constant.GLOBAL):
            return Constant.GLOBAL

        # Add to current scope
        return self._scope_store.current_scope.add(value)

    def python_value_from_napi(self, handle: int) -> Any:
        """Convert napi_value handle to Python value."""
        return self._handle_store.get(handle)

    def add_value(self, value: Any) -> int:
        """Add value to current scope (alias for napi_value_from_python)."""
        return self.napi_value_from_python(value)

    # External values

    def create_external(self, data: int) -> External:
        """Create an external value wrapper."""
        return External(data)

    def get_external_value(self, external: External) -> int:
        """Get value from external wrapper."""
        return get_external_value(external)

    def is_external(self, value: Any) -> bool:
        """Check if value is an external."""
        return is_external(value)

    # Reference management

    def store_ref(self, ref: Any) -> int:
        """Store a reference and return its ID."""
        ref_id = self._next_ref_id
        self._next_ref_id += 1
        self._ref_store[ref_id] = ref
        return ref_id

    def get_ref(self, ref_id: int) -> Optional[Any]:
        """Get reference by ID."""
        return self._ref_store.get(ref_id)

    def delete_ref(self, ref_id: int) -> None:
        """Delete reference by ID."""
        self._ref_store.pop(ref_id, None)

    # Deferred (Promise) management

    def store_deferred(self, deferred: Any) -> int:
        """Store a deferred and return its ID."""
        deferred_id = self._next_deferred_id
        self._next_deferred_id += 1
        self._deferred_store[deferred_id] = deferred
        return deferred_id

    def get_deferred(self, deferred_id: int) -> Optional[Any]:
        """Get deferred by ID."""
        return self._deferred_store.get(deferred_id)

    def delete_deferred(self, deferred_id: int) -> None:
        """Delete deferred by ID."""
        self._deferred_store.pop(deferred_id, None)

    # Cleanup hooks

    def add_cleanup_hook(self, env: Env, fn: Callable, arg: int) -> None:
        """Add a cleanup hook."""
        self._cleanup_queue.add(env, fn, arg)

    def remove_cleanup_hook(self, env: Env, fn: Callable, arg: int) -> None:
        """Remove a cleanup hook."""
        self._cleanup_queue.remove(env, fn, arg)

    def run_cleanup(self) -> None:
        """Run all cleanup hooks."""
        while not self._cleanup_queue.empty():
            self._cleanup_queue.drain()

    # State management

    def can_call_into_js(self) -> bool:
        """Check if we can call into runtime."""
        return self._can_call_into_js and not self._is_stopping

    def set_can_call_into_js(self, value: bool) -> None:
        """Set whether we can call into runtime."""
        self._can_call_into_js = value

    def set_stopping(self, value: bool) -> None:
        """Set stopping state."""
        self._is_stopping = value

    def destroy(self) -> None:
        """Destroy the context and run cleanup."""
        self.set_stopping(True)
        self.set_can_call_into_js(False)
        self.run_cleanup()

    # Callback reference management (prevent GC)

    def add_callback_ref(self, callback: Any) -> None:
        """Add a callback reference to prevent GC."""
        self._callback_refs.append(callback)

    def remove_callback_ref(self, callback: Any) -> None:
        """Remove a callback reference."""
        if callback in self._callback_refs:
            self._callback_refs.remove(callback)


# Global default context
_default_context: Optional[Context] = None


def get_default_context() -> Context:
    """Get or create the default context."""
    global _default_context
    if _default_context is None:
        _default_context = Context()
    return _default_context


def create_context() -> Context:
    """Create a new context."""
    return Context()
