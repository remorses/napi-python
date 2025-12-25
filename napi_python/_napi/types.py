"""
NAPI type definitions for Python.

Reference: https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/typings/napi.d.ts
"""

from ctypes import (
    Structure,
    CFUNCTYPE,
    POINTER,
    c_void_p,
    c_char_p,
    c_int,
    c_uint,
    c_int32,
    c_uint32,
    c_int64,
    c_uint64,
    c_double,
    c_size_t,
    c_bool,
    c_char,
    sizeof,
    addressof,
)
from enum import IntEnum
from typing import Callable, Any
import struct
import sys

# Platform detection
POINTER_SIZE = struct.calcsize("P")
IS_64BIT = POINTER_SIZE == 8

# Basic pointer types
napi_env = c_void_p
napi_value = c_void_p
napi_ref = c_void_p
napi_handle_scope = c_void_p
napi_escapable_handle_scope = c_void_p
napi_callback_info = c_void_p
napi_deferred = c_void_p
napi_async_work = c_void_p
napi_threadsafe_function = c_void_p
napi_async_context = c_void_p
napi_callback_scope = c_void_p


class napi_status(IntEnum):
    """NAPI status codes."""

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
    """NAPI value types."""

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


class napi_typedarray_type(IntEnum):
    """TypedArray types."""

    napi_int8_array = 0
    napi_uint8_array = 1
    napi_uint8_clamped_array = 2
    napi_int16_array = 3
    napi_uint16_array = 4
    napi_int32_array = 5
    napi_uint32_array = 6
    napi_float32_array = 7
    napi_float64_array = 8
    napi_bigint64_array = 9
    napi_biguint64_array = 10


class napi_property_attributes(IntEnum):
    """Property attributes."""

    napi_default = 0
    napi_writable = 1 << 0
    napi_enumerable = 1 << 1
    napi_configurable = 1 << 2
    napi_static = 1 << 10
    # Default for class methods
    napi_default_method = (1 << 0) | (1 << 2)  # writable | configurable
    # Default for object properties
    napi_default_jsproperty = (
        (1 << 0) | (1 << 1) | (1 << 2)
    )  # writable | enumerable | configurable


class napi_key_collection_mode(IntEnum):
    napi_key_include_prototypes = 0
    napi_key_own_only = 1


class napi_key_filter(IntEnum):
    napi_key_all_properties = 0
    napi_key_writable = 1
    napi_key_enumerable = 1 << 1
    napi_key_configurable = 1 << 2
    napi_key_skip_strings = 1 << 3
    napi_key_skip_symbols = 1 << 4


class napi_key_conversion(IntEnum):
    napi_key_keep_numbers = 0
    napi_key_numbers_to_strings = 1


class napi_threadsafe_function_release_mode(IntEnum):
    napi_tsfn_release = 0
    napi_tsfn_abort = 1


class napi_threadsafe_function_call_mode(IntEnum):
    napi_tsfn_nonblocking = 0
    napi_tsfn_blocking = 1


# Callback function types
# napi_callback: (env, info) -> napi_value
napi_callback = CFUNCTYPE(c_void_p, c_void_p, c_void_p)

# napi_finalize: (env, finalize_data, finalize_hint) -> void
napi_finalize = CFUNCTYPE(None, c_void_p, c_void_p, c_void_p)

# napi_async_execute_callback: (env, data) -> void
napi_async_execute_callback = CFUNCTYPE(None, c_void_p, c_void_p)

# napi_async_complete_callback: (env, status, data) -> void
napi_async_complete_callback = CFUNCTYPE(None, c_void_p, c_int, c_void_p)

# napi_threadsafe_function_call_js: (env, js_callback, context, data) -> void
napi_threadsafe_function_call_js = CFUNCTYPE(
    None, c_void_p, c_void_p, c_void_p, c_void_p
)


class napi_extended_error_info(Structure):
    """Extended error information structure."""

    _fields_ = [
        ("error_message", c_char_p),
        ("engine_reserved", c_void_p),
        ("engine_error_code", c_uint32),
        ("error_code", c_int),  # napi_status
    ]


class napi_property_descriptor(Structure):
    """Property descriptor structure."""

    _fields_ = [
        ("utf8name", c_char_p),
        ("name", c_void_p),  # napi_value
        ("method", c_void_p),  # napi_callback
        ("getter", c_void_p),  # napi_callback
        ("setter", c_void_p),  # napi_callback
        ("value", c_void_p),  # napi_value
        ("attributes", c_uint32),  # napi_property_attributes
        ("data", c_void_p),
    ]


class napi_node_version(Structure):
    """Node.js version structure."""

    _fields_ = [
        ("major", c_uint32),
        ("minor", c_uint32),
        ("patch", c_uint32),
        ("release", c_char_p),
    ]


# Constants (matching emnapi)
class Constant(IntEnum):
    """Handle ID constants."""

    HOLE = 0
    EMPTY = 1
    UNDEFINED = 2
    NULL = 3
    FALSE = 4
    TRUE = 5
    GLOBAL = 6
    EMPTY_STRING = 7


# Version constants
NODE_API_SUPPORTED_VERSION_MIN = 1
NODE_API_SUPPORTED_VERSION_MAX = 9
NODE_API_DEFAULT_MODULE_API_VERSION = 8
NAPI_VERSION_EXPERIMENTAL = 2147483647  # INT_MAX
NODE_MODULE_VERSION = 127


# Error messages for each status code
NAPI_ERROR_MESSAGES = {
    napi_status.napi_ok: "",
    napi_status.napi_invalid_arg: "Invalid argument",
    napi_status.napi_object_expected: "An object was expected",
    napi_status.napi_string_expected: "A string was expected",
    napi_status.napi_name_expected: "A string or symbol was expected",
    napi_status.napi_function_expected: "A function was expected",
    napi_status.napi_number_expected: "A number was expected",
    napi_status.napi_boolean_expected: "A boolean was expected",
    napi_status.napi_array_expected: "An array was expected",
    napi_status.napi_generic_failure: "Unknown failure",
    napi_status.napi_pending_exception: "An exception is pending",
    napi_status.napi_cancelled: "The async work item was cancelled",
    napi_status.napi_escape_called_twice: "napi_escape_handle already called on scope",
    napi_status.napi_handle_scope_mismatch: "Invalid handle scope usage",
    napi_status.napi_callback_scope_mismatch: "Invalid callback scope usage",
    napi_status.napi_queue_full: "Thread-safe function queue is full",
    napi_status.napi_closing: "Thread-safe function handle is closing",
    napi_status.napi_bigint_expected: "A bigint was expected",
    napi_status.napi_date_expected: "A date was expected",
    napi_status.napi_arraybuffer_expected: "An arraybuffer was expected",
    napi_status.napi_detachable_arraybuffer_expected: "A detachable arraybuffer was expected",
    napi_status.napi_would_deadlock: "Main thread would deadlock",
    napi_status.napi_no_external_buffers_allowed: "External buffers are not allowed",
    napi_status.napi_cannot_run_js: "Cannot run JavaScript",
}
