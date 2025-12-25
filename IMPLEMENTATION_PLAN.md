# napi-python Implementation Plan

A Python runtime for loading and executing Node-API (NAPI) native addons.

## Project Overview

**Goal**: Create a Python library that can load `.node` shared libraries (native addons built with Node-API) and expose their functionality as Python modules with classes, functions, async support, etc.

**Approach**: Port the [emnapi runtime](https://github.com/toyobayashi/emnapi) concepts from TypeScript/JavaScript to Python, adapting for Python's object model, GC, and GIL.

---

## Project Structure

```
napi_python/
├── __init__.py              # Public API: load_addon()
├── _loader.py               # dlopen, symbol resolution, module init
├── _runtime/
│   ├── __init__.py
│   ├── context.py           # Context - global state manager
│   ├── env.py               # Env - per-module environment
│   ├── isolate.py           # Isolate - handle/scope storage
│   ├── handle.py            # HandleStore - ID-to-value mapping
│   ├── handle_scope.py      # HandleScope - scope-based lifecycle
│   ├── scope_store.py       # ScopeStore - nested scope management
│   ├── reference.py         # Reference, Persistent - prevent GC
│   ├── ref_tracker.py       # RefTracker - linked list for refs
│   ├── finalizer.py         # Finalizer - invoke callbacks on GC
│   ├── external.py          # External - opaque pointer wrapper
│   ├── try_catch.py         # TryCatch - exception scope
│   ├── function_template.py # FunctionTemplate - class/func creation
│   ├── object_template.py   # ObjectTemplate - instance templates
│   └── disposable.py        # Disposable - resource cleanup base
├── _values/
│   ├── __init__.py
│   ├── primitives.py        # null, undefined, bool, number, string
│   ├── objects.py           # Object, Array, Map, Set
│   ├── functions.py         # Function, callable wrappers
│   ├── typed_arrays.py      # ArrayBuffer, TypedArray, DataView
│   ├── external.py          # External value wrapper
│   ├── symbol.py            # Symbol implementation
│   ├── date.py              # Date wrapper
│   ├── bigint.py            # BigInt wrapper
│   └── promise.py           # Promise -> asyncio.Future
├── _napi/
│   ├── __init__.py
│   ├── types.py             # ctypes structures, enums
│   ├── status.py            # napi_status enum
│   ├── functions.py         # All NAPI function implementations
│   ├── env_lifecycle.py     # napi_get_version, etc.
│   ├── value_operations.py  # napi_typeof, napi_is_*, etc.
│   ├── value_creation.py    # napi_create_*, napi_get_*
│   ├── property.py          # napi_get/set_property, define_properties
│   ├── function.py          # napi_create_function, call_function
│   ├── class.py             # napi_define_class, wrap/unwrap
│   ├── error.py             # napi_throw, get_last_error_info
│   ├── reference.py         # napi_create_reference, ref/unref
│   ├── scope.py             # napi_open/close_handle_scope
│   ├── promise.py           # napi_create_promise, resolve/reject
│   ├── arraybuffer.py       # napi_create_arraybuffer, etc.
│   ├── threadsafe.py        # napi_create_threadsafe_function
│   └── async_work.py        # napi_create_async_work
├── _threading/
│   ├── __init__.py
│   ├── gil.py               # GIL acquisition helpers
│   ├── async_work.py        # AsyncWork with thread pool
│   └── threadsafe_function.py # TSFN implementation
└── _utils/
    ├── __init__.py
    ├── memory.py            # Memory alignment, struct packing
    └── compat.py            # Python version compatibility
```

---

## Reference: emnapi Source Files

The JavaScript/TypeScript implementation we're porting from. Use these as reference when implementing Python equivalents.

**Base URL**: `https://github.com/toyobayashi/emnapi/blob/main/packages`

### Runtime Core (`packages/runtime/src/`)

| Python Module | JS Reference | Description |
|---------------|--------------|-------------|
| `_runtime/context.py` | [Context.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/Context.ts) | Global state, env store, cleanup hooks |
| `_runtime/env.py` | [env.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/env.ts) | Per-module environment, error state |
| `_runtime/isolate.py` | [Isolate.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/Isolate.ts) | Handle/scope storage, value conversion |
| `_runtime/handle.py` | [Handle.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/Handle.ts) | ID-to-value mapping with constants |
| `_runtime/handle_scope.py` | [HandleScope.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/HandleScope.ts) | Scope-based handle lifecycle |
| `_runtime/scope_store.py` | [ScopeStore.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/ScopeStore.ts) | Nested scope management |
| `_runtime/reference.py` | [Reference.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/Reference.ts) | prevent GC, ref counting, weak refs |
| `_runtime/persistent.py` | [Persistent.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/Persistent.ts) | Strong/weak ref wrapper with callbacks |
| `_runtime/ref_tracker.py` | [RefTracker.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/RefTracker.ts) | Linked list for reference tracking |
| `_runtime/finalizer.py` | [Finalizer.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/Finalizer.ts) | invoke destructor callbacks |
| `_runtime/tracked_finalizer.py` | [TrackedFinalizer.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/TrackedFinalizer.ts) | Ref-tracked finalizer |
| `_runtime/external.py` | [External.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/External.ts) | Opaque pointer wrapper |
| `_runtime/try_catch.py` | [TryCatch.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/TryCatch.ts) | Exception scope stack |
| `_runtime/function_template.py` | [FunctionTemplate.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/FunctionTemplate.ts) | Create functions/constructors |
| `_runtime/object_template.py` | [ObjectTemplate.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/ObjectTemplate.ts) | Instance template with accessors |
| `_runtime/template.py` | [Template.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/Template.ts) | Base template class |
| `_runtime/private.py` | [Private.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/Private.ts) | Private property keys |
| `_runtime/store.py` | [Store.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/Store.ts) | Array store, ID allocators |
| `_runtime/disposable.py` | [Disaposable.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/Disaposable.ts) | Resource cleanup base class |
| `_utils/features.py` | [util.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/util.ts) | Feature detection, version constants |

### NAPI Function Implementations (`packages/emnapi/src/`)

| Python Module | JS Reference | Functions |
|---------------|--------------|-----------|
| `_napi/function.py` | [function.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/emnapi/src/function.ts) | `napi_create_function`, `napi_call_function`, `napi_get_cb_info` |
| `_napi/class.py` | [wrap.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/emnapi/src/wrap.ts) | `napi_define_class`, `napi_wrap`, `napi_unwrap` |
| `_napi/promise.py` | [promise.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/emnapi/src/promise.ts) | `napi_create_promise`, `napi_resolve_deferred` |
| `_napi/property.py` | [property.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/emnapi/src/property.ts) | `napi_define_properties`, `napi_get/set_property` |
| `_napi/error.py` | [error.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/emnapi/src/error.ts) | `napi_throw_error`, `napi_get_last_error_info` |
| `_napi/reference.py` | [life.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/emnapi/src/life.ts) | `napi_create_reference`, `napi_ref/unref` |
| `_napi/arraybuffer.py` | [memory.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/emnapi/src/memory.ts) | `napi_create_arraybuffer`, `napi_create_buffer` |
| `_napi/value_creation.py` | [value/create.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/emnapi/src/value/create.ts) | `napi_create_*` functions |
| `_napi/value_operations.py` | [value-operation.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/emnapi/src/value-operation.ts) | `napi_typeof`, `napi_is_*`, `napi_strict_equals` |
| `_napi/string.py` | [string.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/emnapi/src/string.ts) | `napi_create_string_*`, `napi_get_value_string_*` |
| `_napi/env_lifecycle.py` | [env.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/emnapi/src/env.ts) | `napi_get_version`, `napi_get_node_version` |
| `_napi/miscellaneous.py` | [miscellaneous.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/emnapi/src/miscellaneous.ts) | `napi_get_boolean`, `napi_get_global` |
| `_threading/async_work.py` | [async-work.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/emnapi/src/async-work.ts) | `napi_create_async_work`, `napi_queue_async_work` |
| `_threading/threadsafe_function.py` | [threadsafe-function.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/emnapi/src/threadsafe-function.ts) | `napi_create_threadsafe_function` |

### Type Definitions (`packages/runtime/src/typings/`)

| Python Module | JS Reference | Description |
|---------------|--------------|-------------|
| `_napi/types.py` | [napi.d.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/typings/napi.d.ts) | NAPI enums, status codes, callback types |
| `_napi/types.py` | [ctype.d.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/typings/ctype.d.ts) | C type aliases (int32_t, void_p, etc.) |
| `_napi/types.py` | [common.d.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/typings/common.d.ts) | Constants (UNDEFINED, NULL, etc.) |

### Internal Helpers (`packages/emnapi/src/`)

| Python Module | JS Reference | Description |
|---------------|--------------|-------------|
| `_napi/_internal.py` | [internal.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/emnapi/src/internal.ts) | Shared helpers, `emnapiCreateFunction` |
| `_napi/_macros.py` | [macro.ts](https://github.com/toyobayashi/emnapi/blob/main/packages/emnapi/src/macro.ts) | `$PREAMBLE`, `$CHECK_ARG`, `$CHECK_ENV` |
| `_napi/v8/*.py` | [v8/](https://github.com/toyobayashi/emnapi/tree/main/packages/emnapi/src/v8) | V8-style API wrappers |

### Key Implementation Patterns

**1. Handle Scope Pattern** (from [HandleScope.ts:23-92](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/HandleScope.ts#L23-L92))
```typescript
// JS: Creates scope, tracks start/end, disposes handles
public static create(parentScope, handleStore, start, end): HandleScope
public add<V>(value: V): number  // Returns handle ID
public escape(handle: number): number  // Move to parent scope
public dispose(): void  // Cleanup handles in range
```

**2. Reference Weak Callback** (from [Reference.ts:19-23](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/Reference.ts#L19-L23))
```typescript
// JS: When weak ref dies, reset persistent and invoke finalizer
private static weakCallback(ref: Reference): void {
  const persistent = ref.getPersistent()
  persistent.reset()
  ref.invokeFinalizerFromGC()
}
```

**3. Function Creation** (from [function.ts:7-25](https://github.com/toyobayashi/emnapi/blob/main/packages/emnapi/src/function.ts#L7-L25))
```typescript
// JS: Creates wrapper that manages scope/callback lifecycle
export function napi_create_function(env, utf8name, length, cb, data, result) {
  return $PREAMBLE!(env, (envObject) => {
    const fresult = emnapiCreateFunction(envObject, utf8name, length, cb, data)
    // ... store result
  })
}
```

**4. Context.createFunction** (from [Context.ts:283-329](https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/Context.ts#L283-L329))
```typescript
// JS: The actual function wrapper factory
public createFunction(envObject, napiCallback, data, name, dynamicExecution) {
  // Creates a JS function that:
  // 1. Opens a scope
  // 2. Sets up callbackInfo (this, args, data)
  // 3. Calls native callback
  // 4. Closes scope
  // 5. Returns result or handles exception
}
```

**5. Class Definition** (from [wrap.ts:11-80](https://github.com/toyobayashi/emnapi/blob/main/packages/emnapi/src/wrap.ts#L11-L80))
```typescript
// JS: napi_define_class creates constructor with prototype methods
export function napi_define_class(env, utf8name, length, constructor, 
                                  callback_data, property_count, properties, result) {
  // 1. Create constructor function via emnapiCreateFunction
  // 2. For each property:
  //    - If static: add to constructor
  //    - If instance: add to prototype
  // 3. Return constructor handle
}
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal**: Minimal runtime that can load a module and call a simple function.

#### 1.1 Core Types (`_napi/types.py`)
```python
# Priority: CRITICAL
# These must be correct for ABI compatibility

from ctypes import *
from enum import IntEnum

class napi_status(IntEnum):
    napi_ok = 0
    napi_invalid_arg = 1
    napi_object_expected = 2
    napi_string_expected = 3
    napi_name_expected = 4
    napi_function_expected = 5
    napi_number_expected = 6
    napi_boolean_expected = 7
    napi_array_expected = 8
    napi_generic_failure = 9
    napi_pending_exception = 10
    napi_cancelled = 11
    napi_escape_called_twice = 12
    napi_handle_scope_mismatch = 13
    napi_callback_scope_mismatch = 14
    napi_queue_full = 15
    napi_closing = 16
    napi_bigint_expected = 17
    napi_date_expected = 18
    napi_arraybuffer_expected = 19
    napi_detachable_arraybuffer_expected = 20
    napi_would_deadlock = 21
    napi_no_external_buffers_allowed = 22
    napi_cannot_run_js = 23

class napi_valuetype(IntEnum):
    napi_undefined = 0
    napi_null = 1
    napi_boolean = 2
    napi_number = 3
    napi_string = 4
    napi_symbol = 5
    napi_object = 6
    napi_function = 7
    napi_external = 8
    napi_bigint = 9

# Pointer types
napi_env = c_void_p
napi_value = c_void_p
napi_ref = c_void_p
napi_handle_scope = c_void_p
napi_callback_info = c_void_p
napi_deferred = c_void_p

# Callback signature
napi_callback = CFUNCTYPE(napi_value, napi_env, napi_callback_info)
napi_finalize = CFUNCTYPE(None, napi_env, c_void_p, c_void_p)
```

#### 1.2 Handle System (`_runtime/handle.py`, `_runtime/handle_scope.py`)

```python
# Priority: CRITICAL
# This is the core of value management

class HandleStore:
    """Maps integer IDs to Python values."""
    MIN_ID = 8  # Reserve 0-7 for constants
    
    # Constants (same IDs as emnapi)
    UNDEFINED = 2
    NULL = 3
    FALSE = 4
    TRUE = 5
    GLOBAL = 6
    EMPTY_STRING = 7
    
    def push(self, value: Any) -> int: ...
    def get(self, handle_id: int) -> Any: ...
    def erase(self, start: int, end: int): ...

class HandleScope:
    """Scope for automatic handle cleanup."""
    def __init__(self, parent: Optional['HandleScope'], store: HandleStore): ...
    def add(self, value: Any) -> int: ...
    def escape(self, handle: int) -> int: ...
    def dispose(self): ...
```

#### 1.3 Environment (`_runtime/env.py`)

```python
# Priority: CRITICAL

class Env:
    """Per-module NAPI environment."""
    def __init__(self, ctx: 'Context', module_api_version: int): ...
    
    # Error handling
    last_error: LastErrorInfo
    last_exception: Optional[Exception]
    
    # Scope tracking
    open_handle_scopes: int
    
    # Reference tracking
    reflist: RefTracker
    finalizing_reflist: RefTracker
    
    def set_last_error(self, code: napi_status) -> napi_status: ...
    def clear_last_error(self) -> napi_status: ...
    def call_into_module(self, fn: Callable) -> Any: ...
```

#### 1.4 Module Loader (`_loader.py`)

```python
# Priority: CRITICAL

import ctypes
from pathlib import Path

def load_addon(path: str | Path) -> ModuleProxy:
    """Load a .node file and return a Python module-like object."""
    lib = ctypes.CDLL(str(path))
    
    # Find init function (napi_register_module_v1)
    init_fn = lib.napi_register_module_v1
    init_fn.argtypes = [napi_env, napi_value]
    init_fn.restype = napi_value
    
    # Create context and env
    ctx = Context()
    env = ctx.create_env(str(path), 8)  # NAPI version 8
    
    # Create exports object
    exports = {}
    exports_handle = ctx.add_value(exports)
    
    # Call init
    result = init_fn(env.id, exports_handle)
    
    return ModuleProxy(ctx, env, exports)
```

---

### Phase 2: Value Operations (Week 2-3)

**Goal**: Full support for primitive values and basic objects.

#### NAPI Functions to Implement (Priority Order)

**Tier 1 - Absolute Minimum** (implement first):
```
napi_get_undefined          # Return undefined constant
napi_get_null               # Return null constant
napi_get_boolean            # Get bool from napi_value
napi_get_global             # Get global object
napi_create_int32           # Create number
napi_create_uint32          # Create number
napi_create_int64           # Create number
napi_create_double          # Create number
napi_create_string_utf8     # Create string
napi_get_value_int32        # Extract int from napi_value
napi_get_value_uint32       # Extract uint from napi_value
napi_get_value_int64        # Extract int64 from napi_value
napi_get_value_double       # Extract float from napi_value
napi_get_value_string_utf8  # Extract string from napi_value
napi_typeof                 # Get type of value
napi_is_array               # Check if array
```

**Tier 2 - Basic Objects**:
```
napi_create_object          # Create empty object (dict)
napi_create_array           # Create array (list)
napi_create_array_with_length
napi_get_array_length
napi_get_element            # Get array[index]
napi_set_element            # Set array[index]
napi_has_element
napi_delete_element
napi_get_property           # Get obj[key]
napi_set_property           # Set obj[key]
napi_has_property
napi_delete_property
napi_get_named_property     # Get obj.name (string key)
napi_set_named_property     # Set obj.name
napi_has_named_property
napi_get_property_names     # Object.keys()
napi_define_properties      # Define multiple properties
```

**Tier 3 - Functions**:
```
napi_create_function        # Create function from callback
napi_call_function          # Call a function
napi_get_cb_info            # Get callback arguments
napi_get_new_target         # Check if called with 'new'
napi_new_instance           # Call as constructor
```

---

### Phase 3: Classes & Wrap (Week 3-4)

**Goal**: Support defining classes and wrapping native data.

```
napi_define_class           # Create a class constructor
napi_wrap                   # Associate native pointer with object
napi_unwrap                 # Get native pointer from object
napi_remove_wrap            # Remove native pointer association
napi_type_tag_object        # Tag object with type UUID
napi_check_object_type_tag  # Verify object type tag
napi_add_finalizer          # Add destructor callback
```

#### Class Implementation Strategy

```python
class NapiClass:
    """Python class generated from napi_define_class."""
    
    _constructor_callback: Callable
    _native_destructor: Optional[Callable]
    _methods: Dict[str, Callable]
    _static_methods: Dict[str, Callable]
    _getters: Dict[str, Callable]
    _setters: Dict[str, Callable]
    
    def __init__(self, *args):
        # Call native constructor
        self._native_ptr = self._constructor_callback(self, args)
    
    def __del__(self):
        # Call destructor if set
        if self._native_destructor:
            self._native_destructor(self._native_ptr)
```

---

### Phase 4: Handle Scopes & References (Week 4-5)

**Goal**: Proper memory management and prevent premature GC.

```
napi_open_handle_scope      # Create new scope
napi_close_handle_scope     # Close scope
napi_open_escapable_handle_scope
napi_close_escapable_handle_scope
napi_escape_handle          # Move handle to parent scope
napi_create_reference       # Create ref-counted reference
napi_delete_reference       # Delete reference
napi_reference_ref          # Increment refcount
napi_reference_unref        # Decrement refcount
napi_get_reference_value    # Get value from reference
```

#### Reference Implementation

```python
class Reference:
    """Prevent garbage collection of a value."""
    
    def __init__(self, ctx: Context, env: Env, value: Any, initial_refcount: int):
        self._value_ref = value if initial_refcount > 0 else weakref.ref(value)
        self._refcount = initial_refcount
        self._weak = initial_refcount == 0
        
        if self._weak:
            # Register weak callback
            weakref.finalize(value, self._invoke_weak_callback)
    
    def ref(self) -> int:
        self._refcount += 1
        if self._refcount == 1 and self._weak:
            # Convert from weak to strong
            value = self._value_ref()
            if value is not None:
                self._value_ref = value
                self._weak = False
        return self._refcount
    
    def unref(self) -> int:
        self._refcount -= 1
        if self._refcount == 0 and not self._weak:
            # Convert from strong to weak
            self._value_ref = weakref.ref(self._value_ref)
            self._weak = True
        return self._refcount
```

---

### Phase 5: Error Handling (Week 5)

**Goal**: Bidirectional exception translation.

```
napi_throw                  # Throw exception
napi_throw_error            # Throw Error with message
napi_throw_type_error       # Throw TypeError
napi_throw_range_error      # Throw RangeError
napi_is_error               # Check if value is Error
napi_create_error           # Create Error object
napi_create_type_error      # Create TypeError object
napi_create_range_error     # Create RangeError object
napi_get_and_clear_last_exception
napi_is_exception_pending
napi_fatal_error            # Abort with message
napi_fatal_exception        # Trigger uncaught exception
napi_get_last_error_info    # Get last error details
```

#### Error Mapping

| NAPI Error              | Python Exception      |
|-------------------------|----------------------|
| `Error`                 | `RuntimeError`       |
| `TypeError`             | `TypeError`          |
| `RangeError`            | `ValueError`         |
| `SyntaxError`           | `SyntaxError`        |
| Generic failure         | `NapiError`          |

---

### Phase 6: ArrayBuffer & TypedArrays (Week 6)

**Goal**: Zero-copy buffer sharing where possible.

```
napi_create_arraybuffer     # Create new ArrayBuffer
napi_create_external_arraybuffer  # Wrap existing memory
napi_get_arraybuffer_info   # Get pointer and length
napi_is_arraybuffer
napi_is_detached_arraybuffer
napi_detach_arraybuffer
napi_create_typedarray      # Create TypedArray view
napi_get_typedarray_info    # Get type, length, buffer
napi_is_typedarray
napi_create_dataview
napi_get_dataview_info
napi_is_dataview
napi_create_buffer          # Node.js Buffer
napi_create_buffer_copy
napi_create_external_buffer
napi_get_buffer_info
napi_is_buffer
```

#### Memory Strategy

```python
class ArrayBufferView:
    """Python wrapper for NAPI ArrayBuffer."""
    
    def __init__(self, size: int):
        # Allocate aligned memory
        self._buffer = (c_uint8 * size)()
        self._ptr = ctypes.addressof(self._buffer)
        self._size = size
        self._detached = False
    
    @classmethod
    def from_external(cls, ptr: int, size: int, hint: Any, 
                      finalizer: Optional[Callable]) -> 'ArrayBufferView':
        """Wrap existing memory (caller owns it)."""
        view = cls.__new__(cls)
        view._ptr = ptr
        view._size = size
        view._external = True
        view._finalizer = finalizer
        view._hint = hint
        return view
    
    def as_memoryview(self) -> memoryview:
        return memoryview((c_uint8 * self._size).from_address(self._ptr))
```

---

### Phase 7: Promises & Async (Week 7)

**Goal**: Integrate with Python asyncio.

```
napi_create_promise         # Create promise + deferred
napi_resolve_deferred       # Resolve promise
napi_reject_deferred        # Reject promise
napi_is_promise             # Check if promise
napi_run_script             # (Skip - not needed for addons)
```

#### Promise Implementation

```python
class NapiDeferred:
    """Represents a deferred promise resolution."""
    
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.future = loop.create_future()
        self._loop = loop
    
    def resolve(self, value: Any):
        self._loop.call_soon_threadsafe(
            self.future.set_result, value
        )
    
    def reject(self, error: Exception):
        self._loop.call_soon_threadsafe(
            self.future.set_exception, error
        )

def napi_create_promise(env: napi_env, deferred_out: POINTER(napi_deferred),
                        promise_out: POINTER(napi_value)) -> napi_status:
    loop = asyncio.get_event_loop()
    deferred = NapiDeferred(loop)
    
    # Store and return handles
    ctx = get_context(env)
    deferred_id = ctx.store_deferred(deferred)
    promise_id = ctx.add_value(deferred.future)
    
    deferred_out[0] = deferred_id
    promise_out[0] = promise_id
    return napi_status.napi_ok
```

---

### Phase 8: Async Work (Week 8)

**Goal**: Support napi_async_work for background tasks.

```
napi_create_async_work      # Create async work item
napi_delete_async_work      # Delete async work
napi_queue_async_work       # Queue for execution
napi_cancel_async_work      # Cancel pending work
```

#### Async Work Implementation

```python
import concurrent.futures

class AsyncWork:
    """Background work with callback."""
    
    def __init__(self, env: Env, resource: Any, resource_name: str,
                 execute: Callable, complete: Callable, data: int):
        self.env = env
        self.execute_cb = execute
        self.complete_cb = complete
        self.data = data
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._future: Optional[concurrent.futures.Future] = None
    
    def queue(self):
        self._future = self._executor.submit(self._run)
    
    def _run(self):
        # Release GIL during native work
        status = napi_status.napi_ok
        try:
            # Call execute (no Python objects!)
            self.execute_cb(self.env.id, self.data)
        except Exception:
            status = napi_status.napi_generic_failure
        
        # Schedule complete on main thread
        asyncio.get_event_loop().call_soon_threadsafe(
            self._complete, status
        )
    
    def _complete(self, status: napi_status):
        # Re-acquire GIL (automatic in Python)
        scope = self.env.ctx.open_scope(self.env)
        try:
            self.complete_cb(self.env.id, status, self.data)
        finally:
            self.env.ctx.close_scope(self.env, scope)
```

---

### Phase 9: Threadsafe Functions (Week 9-10)

**Goal**: Call Python from any thread safely.

```
napi_create_threadsafe_function
napi_get_threadsafe_function_context
napi_call_threadsafe_function
napi_acquire_threadsafe_function
napi_release_threadsafe_function
napi_ref_threadsafe_function
napi_unref_threadsafe_function
```

#### Threading Model

```
┌────────────────────────────────────────────────────────────────┐
│                      Main Thread (GIL)                         │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  asyncio event loop                                       │ │
│  │  ├── napi callbacks (always here)                         │ │
│  │  ├── TSFN.call_js_cb (dispatched here)                   │ │
│  │  └── async_work.complete (dispatched here)               │ │
│  └──────────────────────────────────────────────────────────┘ │
│                              ▲                                 │
│                              │ queue.put() + call_soon_safe   │
│  ┌───────────────────────────┴─────────────────────────────┐  │
│  │                  Thread-Safe Queue                       │  │
│  └───────────────────────────┬─────────────────────────────┘  │
│                              │                                 │
├──────────────────────────────┼─────────────────────────────────┤
│  Worker Thread 1             │  Worker Thread 2                │
│  ┌─────────────────┐         │  ┌─────────────────┐            │
│  │ async_work      │─────────┘  │ native code     │            │
│  │ execute()       │  TSFN call │ tsfn.call()     │────────────│
│  │ (no GIL)        │            │ (no GIL)        │            │
│  └─────────────────┘            └─────────────────┘            │
└────────────────────────────────────────────────────────────────┘
```

#### TSFN Implementation

```python
import threading
import queue

class ThreadsafeFunction:
    def __init__(self, env: Env, func: Any, resource: Any,
                 max_queue_size: int, initial_thread_count: int,
                 context: int, finalizer: Callable,
                 call_js_callback: Callable):
        self._env = env
        self._func = func
        self._queue: queue.Queue = queue.Queue(max_queue_size or 0)
        self._thread_count = initial_thread_count
        self._context = context
        self._call_js_cb = call_js_callback
        self._finalizer = finalizer
        self._closing = False
        self._lock = threading.Lock()
        self._loop = asyncio.get_event_loop()
    
    def call(self, data: int, mode: int) -> napi_status:
        """Called from any thread."""
        if self._closing:
            return napi_status.napi_closing
        
        try:
            if mode == 0:  # napi_tsfn_nonblocking
                self._queue.put_nowait(data)
            else:  # napi_tsfn_blocking
                self._queue.put(data)
        except queue.Full:
            return napi_status.napi_queue_full
        
        # Dispatch to main thread
        self._loop.call_soon_threadsafe(self._dispatch)
        return napi_status.napi_ok
    
    def _dispatch(self):
        """Called on main thread with GIL."""
        while not self._queue.empty():
            try:
                data = self._queue.get_nowait()
            except queue.Empty:
                break
            
            scope = self._env.ctx.open_scope(self._env)
            try:
                if self._call_js_cb:
                    self._call_js_cb(
                        self._env.id,
                        self._func,
                        self._context,
                        data
                    )
            finally:
                self._env.ctx.close_scope(self._env, scope)
```

---

### Phase 10: Testing & Validation (Week 10-11)

#### Test Strategy

1. **Unit Tests**: Each NAPI function in isolation
2. **Integration Tests**: Load simple test addons
3. **Compatibility Tests**: Run against real packages

#### Test Packages (Priority Order)

1. **Custom Test Addon** - Build minimal test cases
   ```rust
   #[napi]
   fn add(a: i32, b: i32) -> i32 { a + b }
   
   #[napi]
   fn greet(name: String) -> String { format!("Hello, {}!", name) }
   
   #[napi]
   struct Counter { value: i32 }
   
   #[napi]
   impl Counter {
       #[napi(constructor)]
       pub fn new() -> Self { Counter { value: 0 } }
       
       #[napi]
       pub fn increment(&mut self) { self.value += 1; }
       
       #[napi(getter)]
       pub fn value(&self) -> i32 { self.value }
   }
   ```

2. **@napi-rs/simple-test** - Basic function calls
3. **@napi-rs/bcrypt** - Async work (CPU-intensive)
4. **@napi-rs/webcodecs** - Complex classes + buffers

---

## WASM vs Native .node Differences

The emnapi runtime was designed for WASM. Loading native `.node` files in Python has different requirements.

### Memory Model Comparison

| Aspect | WASM (emnapi) | Native .node (Python) |
|--------|---------------|----------------------|
| **Memory** | Linear ArrayBuffer, JS manages | Real process memory, OS manages |
| **Pointer size** | Always 32-bit offsets | Platform-native (32 or 64-bit) |
| **Address space** | Isolated sandbox | Shared with Python process |
| **Alignment** | WASM handles automatically | Must match platform ABI |
| **Endianness** | Little-endian (WASM spec) | Platform-native |

### Function Calling Differences

| Aspect | WASM (emnapi) | Native .node (Python) |
|--------|---------------|----------------------|
| **Call mechanism** | WASM imports/exports table | `dlsym()` + ctypes CFUNCTYPE |
| **Callback creation** | `makeDynCall_vppp(ptr)` | `CFUNCTYPE(...)` wrapper |
| **ABI** | WASM call conventions | Platform C ABI (cdecl/stdcall) |
| **Stack** | WASM shadow stack | Native C stack |
| **Error handling** | WASM traps | Signals (SIGSEGV, etc.) |

### Key Adaptations for Python

**1. Pointer Handling**

```python
# WASM (emnapi): Pointers are 32-bit offsets into memory
ptr = memory_offset  # Just a number

# Python (native): Pointers are platform-native
ptr = ctypes.c_void_p(address)  # Must use ctypes

# Converting napi_value (which is a pointer)
# In WASM: just pass the number
# In Python: ensure proper c_void_p type
```

**2. Callback Registration**

```python
# WASM (emnapi): Uses makeDynCall pattern
# makeDynCall_vppp(cb) returns (a, b, c) => void

# Python (native): Use CFUNCTYPE
napi_callback = CFUNCTYPE(c_void_p, c_void_p, c_void_p)

def make_callback(python_func):
    """Create a C-callable function pointer."""
    @napi_callback
    def wrapper(env, info):
        # Called from native code
        return python_func(env, info)
    return wrapper

# IMPORTANT: Must keep reference to prevent GC!
_callback_refs = []
def register_callback(func):
    cb = make_callback(func)
    _callback_refs.append(cb)  # prevent GC
    return cb
```

**3. Memory Safety**

```python
# WASM: Memory is isolated, safe to access any offset
value = memory[offset]

# Python: Must validate pointers, wrap in try/except
def safe_read(ptr, size):
    try:
        return ctypes.string_at(ptr, size)
    except OSError:
        raise NapiError("Invalid memory access")

# Use mmap for ArrayBuffer to control memory region
```

**4. Module Loading**

```python
# WASM (emnapi): Module instantiation with imports
imports = {
    "napi": {
        "napi_create_string_utf8": napi_create_string_utf8,
        # ... all NAPI functions as imports
    }
}
instance = WebAssembly.instantiate(module, imports)

# Python (native): dlopen + symbol table injection
lib = ctypes.CDLL(path)

# The .node file expects NAPI symbols to exist
# Option 1: Link against node.lib (Windows)
# Option 2: Use LD_PRELOAD with our NAPI implementation
# Option 3: Use dlmopen with custom symbol resolution

# Our approach: Provide NAPI functions via a separate shared lib
# that the .node can link against
```

**5. Thread Safety**

```python
# WASM: Typically single-threaded (main thread only)
# SharedArrayBuffer + Atomics for multi-threading

# Python: GIL + native threads
# Native code can release GIL and run in parallel

class GILContext:
    """Manage GIL for native callbacks."""
    
    def __enter__(self):
        # Acquire GIL before calling Python
        self._state = PyGILState_Ensure()
        return self
    
    def __exit__(self, *args):
        # Release GIL when done
        PyGILState_Release(self._state)
```

### Symbol Resolution Strategy

The core challenge: `.node` files expect NAPI functions to be available at load time.

**Option A: Stub Library (Recommended)**
```
1. Build a shared library (libnapi_python.so) that exports all NAPI symbols
2. These symbols call into our Python implementation
3. Use LD_PRELOAD or equivalent to inject before loading .node
```

**Option B: Dynamic Symbol Injection**
```python
# Linux: Use dlmopen with RTLD_DEEPBIND
# macOS: Use DYLD_INSERT_LIBRARIES
# Windows: Use DLL import redirection
```

**Option C: Source-Compatible Rebuild**
```
1. Rebuild the addon with our headers
2. Headers define NAPI functions to call our Python runtime
3. Requires source access and rebuild
```

We'll start with **Option A** as it works with pre-built addons.

---

## Byte Alignment & ABI

### Structure Alignment Rules

```python
# Platform detection
import struct
import sys

POINTER_SIZE = struct.calcsize('P')  # 4 or 8
IS_64BIT = POINTER_SIZE == 8

# Alignment helpers
def align_to(offset: int, alignment: int) -> int:
    return (offset + alignment - 1) & ~(alignment - 1)

# Example: napi_property_descriptor
class napi_property_descriptor(Structure):
    _fields_ = [
        ("utf8name", c_char_p),           # offset 0, size 8
        ("name", c_void_p),               # offset 8, size 8
        ("method", c_void_p),             # offset 16, size 8
        ("getter", c_void_p),             # offset 24, size 8
        ("setter", c_void_p),             # offset 32, size 8
        ("value", c_void_p),              # offset 40, size 8
        ("attributes", c_uint32),         # offset 48, size 4
        ("data", c_void_p),               # offset 56, size 8 (after padding!)
    ]
    # Total: 64 bytes on 64-bit

# Verify at runtime
assert sizeof(napi_property_descriptor) == 64, "ABI mismatch!"
```

### Memory Safety Rules

1. **Never hold raw pointers across GC boundaries**
2. **Use ctypes.py_object for Python object pointers**
3. **Pin objects before passing to native code**
4. **Release pins in try/finally blocks**

---

## NAPI API Implementation Priority Matrix

### Tier 1: Critical Path (Must Have)

| Function | Category | Complexity | Notes |
|----------|----------|------------|-------|
| `napi_get_undefined` | Value | Low | Return constant |
| `napi_get_null` | Value | Low | Return constant |
| `napi_get_boolean` | Value | Low | Extract bool |
| `napi_create_int32` | Value | Low | Create number |
| `napi_create_double` | Value | Low | Create number |
| `napi_create_string_utf8` | Value | Medium | Handle encoding |
| `napi_get_value_int32` | Value | Low | Extract int |
| `napi_get_value_double` | Value | Low | Extract float |
| `napi_get_value_string_utf8` | Value | Medium | Copy to buffer |
| `napi_typeof` | Value | Low | Type check |
| `napi_create_object` | Object | Low | Create dict |
| `napi_get_property` | Object | Medium | Key lookup |
| `napi_set_property` | Object | Medium | Key assign |
| `napi_create_function` | Function | High | Callback wrapper |
| `napi_call_function` | Function | High | Invoke + args |
| `napi_get_cb_info` | Function | High | Parse callback |
| `napi_open_handle_scope` | Scope | Medium | Create scope |
| `napi_close_handle_scope` | Scope | Medium | Cleanup scope |
| `napi_throw_error` | Error | Medium | Set exception |
| `napi_get_last_error_info` | Error | Low | Return struct |

### Tier 2: Essential Features

| Function | Category | Complexity |
|----------|----------|------------|
| `napi_create_array` | Object | Low |
| `napi_get_array_length` | Object | Low |
| `napi_get_element` | Object | Low |
| `napi_set_element` | Object | Low |
| `napi_define_properties` | Object | High |
| `napi_define_class` | Class | High |
| `napi_wrap` | Class | High |
| `napi_unwrap` | Class | Medium |
| `napi_create_reference` | Reference | Medium |
| `napi_delete_reference` | Reference | Low |
| `napi_get_reference_value` | Reference | Low |
| `napi_create_promise` | Async | High |
| `napi_resolve_deferred` | Async | Medium |
| `napi_reject_deferred` | Async | Medium |

### Tier 3: Advanced Features

| Function | Category | Complexity |
|----------|----------|------------|
| `napi_create_arraybuffer` | Buffer | Medium |
| `napi_get_arraybuffer_info` | Buffer | Medium |
| `napi_create_typedarray` | Buffer | High |
| `napi_create_buffer` | Buffer | Medium |
| `napi_create_external` | External | Medium |
| `napi_get_value_external` | External | Low |
| `napi_create_bigint_int64` | BigInt | Medium |
| `napi_create_date` | Date | Medium |
| `napi_create_symbol` | Symbol | Medium |

### Tier 4: Threading (Deferred)

| Function | Category | Complexity |
|----------|----------|------------|
| `napi_create_async_work` | Async | Very High |
| `napi_queue_async_work` | Async | High |
| `napi_cancel_async_work` | Async | High |
| `napi_create_threadsafe_function` | TSFN | Very High |
| `napi_call_threadsafe_function` | TSFN | Very High |
| `napi_acquire_threadsafe_function` | TSFN | Medium |
| `napi_release_threadsafe_function` | TSFN | Medium |

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| ABI incompatibility | High | Medium | Test on multiple platforms early |
| GIL deadlocks | High | Medium | Careful lock ordering, async dispatch |
| Memory leaks | Medium | High | Use weakref.finalize extensively |
| Performance | Medium | Medium | Profile hotpaths, minimize copying |
| Callback lifetime | High | Medium | prevent GC of closures via ref storage |
| NAPI version drift | Low | Low | Target stable NAPI 8 |

---

## Development Milestones

| Week | Milestone | Deliverable |
|------|-----------|-------------|
| 1-2 | Foundation | Load addon, call simple function |
| 3 | Values | All primitive value operations |
| 4 | Objects | Property access, arrays |
| 5 | Functions | Create + call functions |
| 6 | Classes | Define class, wrap/unwrap |
| 7 | References | Prevent GC, weak refs |
| 8 | Errors | Full exception translation |
| 9 | Buffers | ArrayBuffer, TypedArray |
| 10 | Promises | asyncio integration |
| 11 | Async Work | Background tasks |
| 12 | TSFN | Thread-safe functions |
| 13+ | Polish | Test real packages, fix bugs |

---

## Success Criteria

1. **Load a napi-rs addon** without crashes
2. **Call functions** with numbers, strings, objects
3. **Define classes** with constructors, methods, properties
4. **Use async** with Promises becoming Futures
5. **Run @napi-rs/bcrypt** hash function
6. **Pass 90%+ of napi-rs test suite** relevant tests

---

## Next Steps

1. Create project skeleton with module structure
2. Implement `_napi/types.py` with all ctypes definitions
3. Implement `HandleStore` and `HandleScope`
4. Implement minimal `Env` and `Context`
5. Create test addon with simple function
6. Implement `napi_create_function` + `napi_call_function`
7. Iterate until test addon works!
