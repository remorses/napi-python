"""
Reference implementation for NAPI persistent handles.

Reference: https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/Reference.ts
"""

from typing import Optional, Any, Callable, TYPE_CHECKING
from enum import IntEnum
import weakref

from .ref_tracker import RefTracker

if TYPE_CHECKING:
    from .context import Context
    from .env import Env


class ReferenceOwnership(IntEnum):
    """Who owns the reference lifecycle."""
    kRuntime = 0  # Runtime will auto-delete when ref hits 0
    kUserland = 1  # User must explicitly delete


def can_be_held_weakly(value: Any) -> bool:
    """Check if a value can be held by a weak reference."""
    if value is None:
        return False
    # In Python, most objects can be weakly referenced except:
    # - Built-in types like int, str, tuple, etc.
    try:
        weakref.ref(value)
        return True
    except TypeError:
        return False


class Reference(RefTracker):
    """
    A persistent reference to a JavaScript value.
    
    References prevent values from being garbage collected and can
    track the value even after handle scopes are closed.
    
    When refcount > 0: Strong reference (prevents GC)
    When refcount == 0: Weak reference (allows GC, returns None if collected)
    """
    
    _next_id = 1  # Class-level ID counter
    
    @classmethod
    def _allocate_id(cls) -> int:
        """Allocate a unique reference ID."""
        ref_id = cls._next_id
        cls._next_id += 1
        return ref_id
    
    @staticmethod
    def weak_callback(ref: "Reference") -> None:
        """Called when a weak reference is collected by GC."""
        ref._persistent_value = None
        ref._invoke_weak_callback()
    
    def __init__(
        self,
        ctx: "Context",
        env: "Env",
        value: Any,
        initial_refcount: int,
        ownership: ReferenceOwnership,
    ):
        super().__init__()
        self.ctx = ctx
        self.env = env
        self.id = self._allocate_id()
        self._refcount = initial_refcount
        self._ownership = ownership
        
        # Store the value
        self._persistent_value: Any = value
        self._weak_ref: Optional[weakref.ref] = None
        self._can_be_weak = can_be_held_weakly(value)
        
        # Weak callback data
        self._weak_callback: Optional[Callable] = None
        self._weak_callback_data: Any = None
        
        # Register in context
        ctx._ref_store[self.id] = self
        
        # If initial refcount is 0, make it weak
        if initial_refcount == 0:
            self._set_weak()
    
    @classmethod
    def create(
        cls,
        ctx: "Context",
        env: "Env",
        value: Any,
        initial_refcount: int,
        ownership: ReferenceOwnership,
    ) -> "Reference":
        """Factory method to create a reference."""
        ref = cls(ctx, env, value, initial_refcount, ownership)
        if env:
            ref.link(env.reflist)
        return ref
    
    def ref(self) -> int:
        """
        Increment reference count.
        
        If transitioning from 0 to 1, converts from weak to strong reference.
        Returns the new refcount.
        """
        if self._is_empty():
            return 0
        
        self._refcount += 1
        if self._refcount == 1 and self._can_be_weak:
            # Transitioning from weak to strong - restore strong reference
            self._clear_weak()
        
        return self._refcount
    
    def unref(self) -> int:
        """
        Decrement reference count.
        
        If transitioning from 1 to 0, converts from strong to weak reference.
        Returns the new refcount.
        """
        if self._is_empty() or self._refcount == 0:
            return 0
        
        self._refcount -= 1
        if self._refcount == 0:
            self._set_weak()
        
        return self._refcount
    
    def get(self) -> Any:
        """
        Get the referenced value.
        
        Returns None if the reference is empty (value was GC'd).
        """
        if self._is_empty():
            return None
        return self._persistent_value
    
    def get_handle(self, ctx: "Context") -> int:
        """
        Get a handle to the referenced value.
        
        Returns 0 if the reference is empty.
        """
        if self._is_empty():
            return 0
        # Add value to current scope and return handle
        return ctx.add_value(self._persistent_value)
    
    def _is_empty(self) -> bool:
        """Check if the reference is empty (value was collected or reset)."""
        if self._persistent_value is None:
            return True
        # If we have a weak reference, check if it's still alive
        if self._weak_ref is not None:
            value = self._weak_ref()
            if value is None:
                self._persistent_value = None
                return True
            self._persistent_value = value
        return False
    
    def _set_weak(self) -> None:
        """Convert to a weak reference."""
        if not self._can_be_weak:
            # Can't make weak, so just clear it
            self._persistent_value = None
            return
        
        if self._persistent_value is not None:
            try:
                # Create weak reference with callback
                self._weak_ref = weakref.ref(
                    self._persistent_value,
                    lambda _: Reference.weak_callback(self)
                )
            except TypeError:
                # Fallback: clear if can't create weak ref
                self._persistent_value = None
    
    def _clear_weak(self) -> None:
        """Convert from weak to strong reference."""
        if self._weak_ref is not None:
            value = self._weak_ref()
            if value is not None:
                self._persistent_value = value
            self._weak_ref = None
    
    def _invoke_weak_callback(self) -> None:
        """Called when the weak reference is collected."""
        if self._weak_callback:
            self._weak_callback(self._weak_callback_data)
        self._invoke_finalizer_from_gc()
    
    def _invoke_finalizer_from_gc(self) -> None:
        """Invoke finalizer after GC collection."""
        self.finalize()
    
    def refcount(self) -> int:
        """Get current reference count."""
        return self._refcount
    
    def ownership(self) -> ReferenceOwnership:
        """Get ownership type."""
        return self._ownership
    
    def data(self) -> int:
        """Get associated data pointer. Override in subclass."""
        return 0
    
    def reset_finalizer(self) -> None:
        """Reset finalizer. Override in subclass."""
        pass
    
    def _call_user_finalizer(self) -> None:
        """Call user-provided finalizer. Override in subclass."""
        pass
    
    def finalize(self) -> None:
        """Finalize this reference."""
        self._persistent_value = None
        self._weak_ref = None
        
        delete_me = self._ownership == ReferenceOwnership.kRuntime
        self.unlink()
        self._call_user_finalizer()
        
        if delete_me:
            self.dispose()
    
    def dispose(self) -> None:
        """Clean up this reference."""
        if self.id == 0:
            return
        
        self.unlink()
        
        # Remove from context store
        if self.ctx and self.id in self.ctx._ref_store:
            del self.ctx._ref_store[self.id]
        
        super().dispose()
        
        self.ctx = None
        self.env = None
        self.id = 0
        self._persistent_value = None
        self._weak_ref = None


class ReferenceWithData(Reference):
    """Reference that stores additional user data."""
    
    def __init__(
        self,
        ctx: "Context",
        env: "Env",
        value: Any,
        initial_refcount: int,
        ownership: ReferenceOwnership,
        data: int,
    ):
        super().__init__(ctx, env, value, initial_refcount, ownership)
        self._data = data
    
    @classmethod
    def create(
        cls,
        ctx: "Context",
        env: "Env",
        value: Any,
        initial_refcount: int,
        ownership: ReferenceOwnership,
        data: int,
    ) -> "ReferenceWithData":
        """Factory method to create a reference with data."""
        ref = cls(ctx, env, value, initial_refcount, ownership, data)
        if env:
            ref.link(env.reflist)
        return ref
    
    def data(self) -> int:
        """Get associated data pointer."""
        return self._data


class ReferenceWithFinalizer(Reference):
    """Reference with a user-provided finalizer callback."""
    
    def __init__(
        self,
        ctx: "Context",
        env: "Env",
        value: Any,
        initial_refcount: int,
        ownership: ReferenceOwnership,
        finalize_callback: int,
        finalize_data: int,
        finalize_hint: int,
    ):
        super().__init__(ctx, env, value, initial_refcount, ownership)
        self._finalize_callback = finalize_callback
        self._finalize_data = finalize_data
        self._finalize_hint = finalize_hint
    
    @classmethod
    def create(
        cls,
        ctx: "Context",
        env: "Env",
        value: Any,
        initial_refcount: int,
        ownership: ReferenceOwnership,
        finalize_callback: int,
        finalize_data: int,
        finalize_hint: int,
    ) -> "ReferenceWithFinalizer":
        """Factory method to create a reference with finalizer."""
        if not env:
            raise TypeError("envObject is required for ReferenceWithFinalizer")
        ref = cls(
            ctx, env, value, initial_refcount, ownership,
            finalize_callback, finalize_data, finalize_hint
        )
        ref.link(env.finalizing_reflist)
        return ref
    
    def data(self) -> int:
        """Get finalize data pointer."""
        return self._finalize_data
    
    def reset_finalizer(self) -> None:
        """Reset the finalizer callback."""
        self._finalize_callback = 0
        self._finalize_data = 0
        self._finalize_hint = 0
    
    def _call_user_finalizer(self) -> None:
        """Call the user-provided finalizer."""
        if self._finalize_callback and self.env:
            # TODO: Call the native finalizer callback
            # This would need ctypes integration
            pass
    
    def _invoke_finalizer_from_gc(self) -> None:
        """Invoke finalizer from GC - queue it for later."""
        if self.env:
            self.env.enqueue_finalizer(self)
    
    def dispose(self) -> None:
        """Clean up this reference."""
        if self.env:
            self.env.dequeue_finalizer(self)
        self._finalize_callback = 0
        self._finalize_data = 0
        self._finalize_hint = 0
        super().dispose()
