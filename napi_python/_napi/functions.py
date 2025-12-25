"""
Core NAPI function implementations.

These functions implement the Node-API specification for Python.
Reference: https://nodejs.org/api/n-api.html
"""

from typing import Optional, Any, List
from ctypes import (
    c_void_p,
    c_int32,
    c_uint32,
    c_int64,
    c_uint64,
    c_double,
    c_size_t,
    c_char_p,
    c_bool,
    POINTER,
    cast,
    sizeof,
    byref,
    create_string_buffer,
    addressof,
    string_at,
)

from .types import (
    napi_status,
    napi_valuetype,
    napi_property_attributes,
    napi_env,
    napi_value,
    napi_ref,
    napi_handle_scope,
    napi_callback_info,
    napi_deferred,
    napi_callback,
    napi_finalize,
    napi_extended_error_info,
    napi_property_descriptor,
    Constant,
    NAPI_ERROR_MESSAGES,
    NODE_API_SUPPORTED_VERSION_MAX,
)
from .._runtime.context import Context, get_default_context
from .._runtime.env import Env
from .._runtime.handle import Undefined
from .._runtime.handle_scope import HandleScope, CallbackInfo


# Global context (initialized on first use)
_ctx: Optional[Context] = None


def _get_ctx() -> Context:
    """Get or create the global context."""
    global _ctx
    if _ctx is None:
        _ctx = get_default_context()
    return _ctx


def _get_env(env: int) -> Optional[Env]:
    """Get environment from handle."""
    return _get_ctx().get_env(env)


def _check_env(env: int) -> Optional[Env]:
    """Check and get environment, return None if invalid."""
    if not env:
        return None
    return _get_env(env)


def _check_arg(env_obj: Env, arg: Any) -> bool:
    """Check if argument is valid."""
    return arg is not None and arg != 0


# =============================================================================
# Environment Lifecycle
# =============================================================================


def napi_get_version(env: int, result: POINTER(c_uint32)) -> int:
    """Get the highest supported NAPI version."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    result[0] = NODE_API_SUPPORTED_VERSION_MAX
    return env_obj.clear_last_error()


def napi_get_last_error_info(
    env: int, result: POINTER(POINTER(napi_extended_error_info))
) -> int:
    """Get information about the last error."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    # Create error info structure
    error_info = napi_extended_error_info()
    error_code = env_obj.last_error.error_code
    error_info.error_code = error_code
    error_info.engine_error_code = env_obj.last_error.engine_error_code
    error_info.engine_reserved = env_obj.last_error.engine_reserved

    # Get error message
    msg = NAPI_ERROR_MESSAGES.get(error_code, "Unknown error")
    error_info.error_message = msg.encode("utf-8")

    # Store and return pointer
    # Note: In real implementation, this should be stored in env
    result[0] = cast(byref(error_info), POINTER(napi_extended_error_info))

    return napi_status.napi_ok


# =============================================================================
# Handle Scope
# =============================================================================


def napi_open_handle_scope(env: int, result: POINTER(napi_handle_scope)) -> int:
    """Open a new handle scope."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    scope = _get_ctx().open_scope(env_obj)
    result[0] = scope.id
    return env_obj.clear_last_error()


def napi_close_handle_scope(env: int, scope: int) -> int:
    """Close a handle scope."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    _get_ctx().close_scope(env_obj)
    return env_obj.clear_last_error()


def napi_open_escapable_handle_scope(
    env: int, result: POINTER(napi_handle_scope)
) -> int:
    """Open an escapable handle scope."""
    return napi_open_handle_scope(env, result)


def napi_close_escapable_handle_scope(env: int, scope: int) -> int:
    """Close an escapable handle scope."""
    return napi_close_handle_scope(env, scope)


def napi_escape_handle(
    env: int, scope: int, escapee: int, result: POINTER(napi_value)
) -> int:
    """Escape a handle to the parent scope."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    scope_obj = _get_ctx().get_handle_scope(scope)
    if not scope_obj:
        return env_obj.set_last_error(napi_status.napi_handle_scope_mismatch)

    escaped = scope_obj.escape(escapee)
    if escaped == 0:
        return env_obj.set_last_error(napi_status.napi_escape_called_twice)

    result[0] = escaped
    return env_obj.clear_last_error()


# =============================================================================
# Value Operations - Type Checking
# =============================================================================


def napi_typeof(env: int, value: int, result: POINTER(c_int32)) -> int:
    """Get the type of a value."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    py_value = _get_ctx().python_value_from_napi(value)

    if py_value is Undefined:
        result[0] = napi_valuetype.napi_undefined
    elif py_value is None:
        result[0] = napi_valuetype.napi_null
    elif isinstance(py_value, bool):
        result[0] = napi_valuetype.napi_boolean
    elif isinstance(py_value, (int, float)):
        result[0] = napi_valuetype.napi_number
    elif isinstance(py_value, str):
        result[0] = napi_valuetype.napi_string
    elif callable(py_value):
        result[0] = napi_valuetype.napi_function
    elif _get_ctx().is_external(py_value):
        result[0] = napi_valuetype.napi_external
    else:
        result[0] = napi_valuetype.napi_object

    return env_obj.clear_last_error()


def napi_is_array(env: int, value: int, result: POINTER(c_bool)) -> int:
    """Check if value is an array."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    py_value = _get_ctx().python_value_from_napi(value)
    result[0] = isinstance(py_value, list)
    return env_obj.clear_last_error()


def napi_is_arraybuffer(env: int, value: int, result: POINTER(c_bool)) -> int:
    """Check if value is an ArrayBuffer."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    py_value = _get_ctx().python_value_from_napi(value)
    result[0] = isinstance(py_value, (bytearray, memoryview))
    return env_obj.clear_last_error()


def napi_is_buffer(env: int, value: int, result: POINTER(c_bool)) -> int:
    """Check if value is a Buffer."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    py_value = _get_ctx().python_value_from_napi(value)
    result[0] = isinstance(py_value, (bytes, bytearray))
    return env_obj.clear_last_error()


def napi_is_error(env: int, value: int, result: POINTER(c_bool)) -> int:
    """Check if value is an Error."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    py_value = _get_ctx().python_value_from_napi(value)
    result[0] = isinstance(py_value, Exception)
    return env_obj.clear_last_error()


def napi_is_function(env: int, value: int, result: POINTER(c_bool)) -> int:
    """Check if value is a function."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    py_value = _get_ctx().python_value_from_napi(value)
    result[0] = callable(py_value)
    return env_obj.clear_last_error()


def napi_is_object(env: int, value: int, result: POINTER(c_bool)) -> int:
    """Check if value is an object."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    py_value = _get_ctx().python_value_from_napi(value)
    # In JS, arrays and functions are also objects
    result[0] = (
        py_value is not None
        and py_value is not Undefined
        and not isinstance(py_value, (bool, int, float, str))
    )
    return env_obj.clear_last_error()


def napi_is_promise(env: int, value: int, result: POINTER(c_bool)) -> int:
    """Check if value is a Promise."""
    import asyncio

    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    py_value = _get_ctx().python_value_from_napi(value)
    result[0] = isinstance(py_value, asyncio.Future)
    return env_obj.clear_last_error()


def napi_strict_equals(env: int, lhs: int, rhs: int, result: POINTER(c_bool)) -> int:
    """Check strict equality."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    lhs_val = _get_ctx().python_value_from_napi(lhs)
    rhs_val = _get_ctx().python_value_from_napi(rhs)

    # Strict equality - same type and value
    result[0] = lhs_val is rhs_val or (
        type(lhs_val) == type(rhs_val) and lhs_val == rhs_val
    )
    return env_obj.clear_last_error()


# =============================================================================
# Value Creation - Primitives
# =============================================================================


def napi_get_undefined(env: int, result: POINTER(napi_value)) -> int:
    """Get undefined value."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    result[0] = Constant.UNDEFINED
    return env_obj.clear_last_error()


def napi_get_null(env: int, result: POINTER(napi_value)) -> int:
    """Get null value."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    result[0] = Constant.NULL
    return env_obj.clear_last_error()


def napi_get_global(env: int, result: POINTER(napi_value)) -> int:
    """Get global object."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    result[0] = Constant.GLOBAL
    return env_obj.clear_last_error()


def napi_get_boolean(env: int, value: bool, result: POINTER(napi_value)) -> int:
    """Get boolean value."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    result[0] = Constant.TRUE if value else Constant.FALSE
    return env_obj.clear_last_error()


def napi_create_int32(env: int, value: int, result: POINTER(napi_value)) -> int:
    """Create int32 value."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    handle = _get_ctx().add_value(int(value))
    result[0] = handle
    return env_obj.clear_last_error()


def napi_create_uint32(env: int, value: int, result: POINTER(napi_value)) -> int:
    """Create uint32 value."""
    return napi_create_int32(env, value & 0xFFFFFFFF, result)


def napi_create_int64(env: int, value: int, result: POINTER(napi_value)) -> int:
    """Create int64 value."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    handle = _get_ctx().add_value(int(value))
    result[0] = handle
    return env_obj.clear_last_error()


def napi_create_double(env: int, value: float, result: POINTER(napi_value)) -> int:
    """Create double value."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    handle = _get_ctx().add_value(float(value))
    result[0] = handle
    return env_obj.clear_last_error()


def napi_create_string_utf8(
    env: int, string: bytes, length: int, result: POINTER(napi_value)
) -> int:
    """Create UTF-8 string value."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    # Handle length
    if length < 0:  # NAPI_AUTO_LENGTH
        if isinstance(string, bytes):
            py_str = string.decode("utf-8")
        else:
            py_str = str(string)
    else:
        if isinstance(string, bytes):
            py_str = string[:length].decode("utf-8")
        else:
            py_str = str(string)[:length]

    handle = _get_ctx().add_value(py_str)
    result[0] = handle
    return env_obj.clear_last_error()


# =============================================================================
# Value Extraction - Primitives
# =============================================================================


def napi_get_value_bool(env: int, value: int, result: POINTER(c_bool)) -> int:
    """Get boolean value."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    py_value = _get_ctx().python_value_from_napi(value)
    if not isinstance(py_value, bool):
        return env_obj.set_last_error(napi_status.napi_boolean_expected)

    result[0] = py_value
    return env_obj.clear_last_error()


def napi_get_value_int32(env: int, value: int, result: POINTER(c_int32)) -> int:
    """Get int32 value."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    py_value = _get_ctx().python_value_from_napi(value)
    if not isinstance(py_value, (int, float)):
        return env_obj.set_last_error(napi_status.napi_number_expected)

    result[0] = int(py_value) & 0xFFFFFFFF
    if result[0] > 0x7FFFFFFF:
        result[0] -= 0x100000000
    return env_obj.clear_last_error()


def napi_get_value_uint32(env: int, value: int, result: POINTER(c_uint32)) -> int:
    """Get uint32 value."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    py_value = _get_ctx().python_value_from_napi(value)
    if not isinstance(py_value, (int, float)):
        return env_obj.set_last_error(napi_status.napi_number_expected)

    result[0] = int(py_value) & 0xFFFFFFFF
    return env_obj.clear_last_error()


def napi_get_value_int64(env: int, value: int, result: POINTER(c_int64)) -> int:
    """Get int64 value."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    py_value = _get_ctx().python_value_from_napi(value)
    if not isinstance(py_value, (int, float)):
        return env_obj.set_last_error(napi_status.napi_number_expected)

    result[0] = int(py_value)
    return env_obj.clear_last_error()


def napi_get_value_double(env: int, value: int, result: POINTER(c_double)) -> int:
    """Get double value."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    py_value = _get_ctx().python_value_from_napi(value)
    if not isinstance(py_value, (int, float)):
        return env_obj.set_last_error(napi_status.napi_number_expected)

    result[0] = float(py_value)
    return env_obj.clear_last_error()


def napi_get_value_string_utf8(
    env: int, value: int, buf: c_char_p, bufsize: int, result: POINTER(c_size_t)
) -> int:
    """Get UTF-8 string value."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    py_value = _get_ctx().python_value_from_napi(value)
    if not isinstance(py_value, str):
        return env_obj.set_last_error(napi_status.napi_string_expected)

    encoded = py_value.encode("utf-8")

    if result:
        result[0] = len(encoded)

    if buf and bufsize > 0:
        # Copy to buffer
        copy_len = min(len(encoded), bufsize - 1)
        for i in range(copy_len):
            buf[i] = encoded[i]
        buf[copy_len] = 0  # Null terminator

    return env_obj.clear_last_error()


# =============================================================================
# Object Operations
# =============================================================================


def napi_create_object(env: int, result: POINTER(napi_value)) -> int:
    """Create an empty object."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    handle = _get_ctx().add_value({})
    result[0] = handle
    return env_obj.clear_last_error()


def napi_create_array(env: int, result: POINTER(napi_value)) -> int:
    """Create an empty array."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    handle = _get_ctx().add_value([])
    result[0] = handle
    return env_obj.clear_last_error()


def napi_create_array_with_length(
    env: int, length: int, result: POINTER(napi_value)
) -> int:
    """Create an array with specified length."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    handle = _get_ctx().add_value([None] * length)
    result[0] = handle
    return env_obj.clear_last_error()


def napi_get_array_length(env: int, value: int, result: POINTER(c_uint32)) -> int:
    """Get array length."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    py_value = _get_ctx().python_value_from_napi(value)
    if not isinstance(py_value, list):
        return env_obj.set_last_error(napi_status.napi_array_expected)

    result[0] = len(py_value)
    return env_obj.clear_last_error()


def napi_get_element(
    env: int, obj: int, index: int, result: POINTER(napi_value)
) -> int:
    """Get array element at index."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    py_value = _get_ctx().python_value_from_napi(obj)
    if not isinstance(py_value, list):
        return env_obj.set_last_error(napi_status.napi_array_expected)

    if index < 0 or index >= len(py_value):
        result[0] = Constant.UNDEFINED
    else:
        result[0] = _get_ctx().add_value(py_value[index])

    return env_obj.clear_last_error()


def napi_set_element(env: int, obj: int, index: int, value: int) -> int:
    """Set array element at index."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    py_obj = _get_ctx().python_value_from_napi(obj)
    if not isinstance(py_obj, list):
        return env_obj.set_last_error(napi_status.napi_array_expected)

    py_value = _get_ctx().python_value_from_napi(value)

    # Extend array if needed
    while len(py_obj) <= index:
        py_obj.append(None)

    py_obj[index] = py_value
    return env_obj.clear_last_error()


def napi_get_property(env: int, obj: int, key: int, result: POINTER(napi_value)) -> int:
    """Get property from object."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    py_obj = _get_ctx().python_value_from_napi(obj)
    py_key = _get_ctx().python_value_from_napi(key)

    if isinstance(py_obj, dict):
        value = py_obj.get(py_key, Undefined)
    elif hasattr(py_obj, "__getitem__"):
        try:
            value = py_obj[py_key]
        except (KeyError, IndexError):
            value = Undefined
    elif hasattr(py_obj, str(py_key)):
        value = getattr(py_obj, str(py_key), Undefined)
    else:
        value = Undefined

    result[0] = _get_ctx().add_value(value)
    return env_obj.clear_last_error()


def napi_set_property(env: int, obj: int, key: int, value: int) -> int:
    """Set property on object."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    py_obj = _get_ctx().python_value_from_napi(obj)
    py_key = _get_ctx().python_value_from_napi(key)
    py_value = _get_ctx().python_value_from_napi(value)

    if isinstance(py_obj, dict):
        py_obj[py_key] = py_value
    elif hasattr(py_obj, "__setitem__"):
        py_obj[py_key] = py_value
    else:
        setattr(py_obj, str(py_key), py_value)

    return env_obj.clear_last_error()


def napi_has_property(env: int, obj: int, key: int, result: POINTER(c_bool)) -> int:
    """Check if object has property."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    py_obj = _get_ctx().python_value_from_napi(obj)
    py_key = _get_ctx().python_value_from_napi(key)

    if isinstance(py_obj, dict):
        result[0] = py_key in py_obj
    elif hasattr(py_obj, "__contains__"):
        result[0] = py_key in py_obj
    else:
        result[0] = hasattr(py_obj, str(py_key))

    return env_obj.clear_last_error()


def napi_get_named_property(
    env: int, obj: int, utf8name: bytes, result: POINTER(napi_value)
) -> int:
    """Get named property from object."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not result:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    py_obj = _get_ctx().python_value_from_napi(obj)
    key = utf8name.decode("utf-8") if isinstance(utf8name, bytes) else utf8name

    if isinstance(py_obj, dict):
        value = py_obj.get(key, Undefined)
    elif hasattr(py_obj, key):
        value = getattr(py_obj, key)
    else:
        value = Undefined

    result[0] = _get_ctx().add_value(value)
    return env_obj.clear_last_error()


def napi_set_named_property(env: int, obj: int, utf8name: bytes, value: int) -> int:
    """Set named property on object."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    py_obj = _get_ctx().python_value_from_napi(obj)
    key = utf8name.decode("utf-8") if isinstance(utf8name, bytes) else utf8name
    py_value = _get_ctx().python_value_from_napi(value)

    if isinstance(py_obj, dict):
        py_obj[key] = py_value
    else:
        setattr(py_obj, key, py_value)

    return env_obj.clear_last_error()


# =============================================================================
# Function Operations
# =============================================================================


def napi_get_cb_info(
    env: int,
    cbinfo: int,
    argc: POINTER(c_size_t),
    argv: POINTER(napi_value),
    this_arg: POINTER(napi_value),
    data: POINTER(c_void_p),
) -> int:
    """Get callback info."""
    env_obj = _check_env(env)
    if not env_obj:
        return napi_status.napi_invalid_arg

    if not cbinfo:
        return env_obj.set_last_error(napi_status.napi_invalid_arg)

    cb_info = _get_ctx().get_callback_info(cbinfo)

    if argv and argc:
        argc_val = argc[0]
        args = cb_info.args
        arr_len = min(argc_val, len(args))

        for i in range(arr_len):
            argv[i] = _get_ctx().add_value(args[i])

        # Fill remaining with undefined
        for i in range(arr_len, argc_val):
            argv[i] = Constant.UNDEFINED

    if argc:
        argc[0] = len(cb_info.args)

    if this_arg:
        if cb_info.thiz is not None:
            this_arg[0] = _get_ctx().add_value(cb_info.thiz)
        else:
            this_arg[0] = Constant.UNDEFINED

    if data:
        data[0] = cb_info.data

    return env_obj.clear_last_error()


# TODO: Add more NAPI function implementations...
