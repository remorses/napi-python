"""
NAPI Environment - per-module state.

Reference: https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/env.ts
"""

from typing import Optional, Any, Callable, Dict, TYPE_CHECKING
from dataclasses import dataclass, field
import weakref

from .disposable import Disposable
from .._napi.types import napi_status, NAPI_VERSION_EXPERIMENTAL

if TYPE_CHECKING:
    from .context import Context
    from .ref_tracker import RefTracker


@dataclass
class LastError:
    """Last error information."""

    error_code: napi_status = napi_status.napi_ok
    engine_error_code: int = 0
    engine_reserved: int = 0


@dataclass
class ObjectBinding:
    """Binding data for wrapped objects."""

    wrapped: int = 0  # Reference ID for wrapped native data
    tag: Optional[bytes] = None  # Type tag (16 bytes UUID)


class Env(Disposable):
    """
    Per-module NAPI environment.

    Each loaded native module gets its own Env that tracks:
    - Open handle scopes
    - Last error state
    - References and pointers
    - Instance data
    """

    def __init__(self, ctx: "Context", module_api_version: int, filename: str = ""):
        from .ref_tracker import RefTracker

        self.ctx = ctx
        self.id: int = 0
        self.module_api_version = module_api_version
        self.filename = filename

        # Handle scope tracking
        self.open_handle_scopes: int = 0

        # Error state
        self.last_error = LastError()
        self.last_exception: Optional[Exception] = None

        # Reference tracking
        self.refs: int = 1
        self.reflist = RefTracker()
        self.finalizing_reflist = RefTracker()
        self.pending_finalizers: list = []

        # Instance data
        self.instance_data: Optional[Any] = None
        self._instance_data_ref: int = 0

        # Object bindings (WeakKeyDictionary for wrap/unwrap)
        self._binding_map: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()

        # GC finalizer state
        self.in_gc_finalizer: bool = False

        # Destruction state
        self.destructing: bool = False
        self.finalization_scheduled: bool = False

    def can_call_into_js(self) -> bool:
        """Check if we can call into the runtime."""
        return self.ctx.can_call_into_js()

    def terminated_or_terminating(self) -> bool:
        """Check if environment is terminating."""
        return not self.can_call_into_js()

    def ref(self) -> None:
        """Increment reference count."""
        self.refs += 1

    def unref(self) -> None:
        """Decrement reference count."""
        self.refs -= 1
        if self.refs == 0:
            self.dispose()

    def clear_last_error(self) -> napi_status:
        """Clear the last error."""
        if self.last_error.error_code != napi_status.napi_ok:
            self.last_error.error_code = napi_status.napi_ok
        if self.last_error.engine_error_code != 0:
            self.last_error.engine_error_code = 0
        if self.last_error.engine_reserved != 0:
            self.last_error.engine_reserved = 0
        return napi_status.napi_ok

    def set_last_error(
        self,
        error_code: napi_status,
        engine_error_code: int = 0,
        engine_reserved: int = 0,
    ) -> napi_status:
        """Set the last error."""
        self.last_error.error_code = error_code
        self.last_error.engine_error_code = engine_error_code
        self.last_error.engine_reserved = engine_reserved
        return error_code

    def call_into_module(
        self,
        fn: Callable[["Env"], Any],
        handle_exception: Optional[Callable[["Env", Exception], None]] = None,
    ) -> Any:
        """
        Call a function within this environment's context.

        Manages error state and handle scopes.
        """
        open_before = self.open_handle_scopes
        self.clear_last_error()

        try:
            result = fn(self)
        except Exception as e:
            if handle_exception:
                handle_exception(self, e)
            else:
                self._handle_throw(e)
            return None

        if open_before != self.open_handle_scopes:
            raise RuntimeError("Handle scope mismatch")

        if self.last_exception is not None:
            err = self.last_exception
            self.last_exception = None
            if handle_exception:
                handle_exception(self, err)
            else:
                self._handle_throw(err)

        return result

    def _handle_throw(self, value: Exception) -> None:
        """Handle an exception thrown from module code."""
        if self.terminated_or_terminating():
            return
        raise value

    def check_gc_access(self) -> None:
        """Check if GC-unsafe operations are allowed."""
        if (
            self.module_api_version == NAPI_VERSION_EXPERIMENTAL
            and self.in_gc_finalizer
        ):
            raise RuntimeError(
                "Finalizer is calling a function that may affect GC state.\n"
                "The finalizers are run directly from GC and must not affect GC state.\n"
                "Use `node_api_post_finalizer` from inside of the finalizer to work around this issue."
            )

    def enqueue_finalizer(self, finalizer: "RefTracker") -> None:
        """Queue a finalizer for later execution."""
        if finalizer not in self.pending_finalizers:
            self.pending_finalizers.append(finalizer)

    def dequeue_finalizer(self, finalizer: "RefTracker") -> None:
        """Remove a finalizer from the queue."""
        if finalizer in self.pending_finalizers:
            self.pending_finalizers.remove(finalizer)

    def drain_finalizer_queue(self) -> None:
        """Execute all pending finalizers."""
        while self.pending_finalizers:
            finalizer = self.pending_finalizers.pop(0)
            finalizer.finalize()

    def get_object_binding(self, value: Any) -> ObjectBinding:
        """Get or create binding for an object."""
        if value in self._binding_map:
            return self._binding_map[value]
        binding = ObjectBinding()
        self._binding_map[value] = binding
        return binding

    def init_object_binding(self, value: Any) -> ObjectBinding:
        """Initialize a new binding for an object."""
        binding = ObjectBinding()
        self._binding_map[value] = binding
        return binding

    def set_instance_data(
        self, data: int, finalize_cb: int, finalize_hint: int
    ) -> None:
        """Set instance data for this environment."""
        # TODO: Implement finalizer tracking
        self._instance_data_ref = data

    def get_instance_data(self) -> int:
        """Get instance data for this environment."""
        return self._instance_data_ref

    def dispose(self) -> None:
        """Clean up this environment."""
        if self.id == 0:
            return

        self.destructing = True
        self.drain_finalizer_queue()

        # Finalize all references
        from .ref_tracker import RefTracker

        RefTracker.finalize_all(self.finalizing_reflist)
        RefTracker.finalize_all(self.reflist)

        # Clear exception
        self.last_exception = None

        # Remove from context store
        if self.ctx:
            self.ctx._env_store.dealloc(self.id)

        self.id = 0
