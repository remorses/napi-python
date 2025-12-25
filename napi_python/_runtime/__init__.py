"""Runtime components for NAPI."""

from .context import Context, create_context, get_default_context
from .env import Env
from .handle import HandleStore, Undefined, GlobalObject
from .handle_scope import HandleScope, EscapableHandleScope, CallbackInfo
from .scope_store import ScopeStore
from .store import ArrayStore, BaseArrayStore
from .ref_tracker import RefTracker
from .reference import Reference, ReferenceWithData, ReferenceWithFinalizer, ReferenceOwnership
from .external import External, is_external, get_external_value
from .disposable import Disposable

__all__ = [
    "Context",
    "create_context",
    "get_default_context",
    "Env",
    "HandleStore",
    "HandleScope",
    "EscapableHandleScope",
    "CallbackInfo",
    "ScopeStore",
    "ArrayStore",
    "BaseArrayStore",
    "RefTracker",
    "Reference",
    "ReferenceWithData",
    "ReferenceWithFinalizer",
    "ReferenceOwnership",
    "External",
    "is_external",
    "get_external_value",
    "Disposable",
    "Undefined",
    "GlobalObject",
]
