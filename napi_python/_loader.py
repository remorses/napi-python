"""
Native addon loader.

This module handles loading .node files (shared libraries) and
initializing them with our NAPI implementation.
"""

import ctypes
from ctypes import (
    CDLL,
    CFUNCTYPE,
    POINTER,
    Structure,
    c_void_p,
    c_int,
    c_int32,
    c_uint32,
    c_int64,
    c_uint64,
    c_char_p,
    c_size_t,
    c_double,
    c_bool,
    cast,
    byref,
    addressof,
    sizeof,
)
from pathlib import Path
from typing import Optional, Any, Dict, Callable, List
import sys
import os

from ._runtime import Context, Env, get_default_context, Reference, ReferenceOwnership
from ._napi.types import (
    napi_status,
    napi_valuetype,
    napi_value,
    napi_env,
    napi_callback_info,
    napi_callback,
    napi_extended_error_info,
    NODE_API_DEFAULT_MODULE_API_VERSION,
    Constant,
)
from ._napi import functions as napi_funcs


class NapiError(Exception):
    """Error from NAPI addon."""

    def __init__(self, status: napi_status, message: str = ""):
        self.status = status
        self.message = message or f"NAPI error: {status.name}"
        super().__init__(self.message)


class ModuleExports:
    """
    Wrapper for addon exports that allows attribute access.
    """

    def __init__(self, exports: Dict[str, Any], ctx: Context, env: Env):
        object.__setattr__(self, "_exports", exports)
        object.__setattr__(self, "_ctx", ctx)
        object.__setattr__(self, "_env", env)

    def __getattr__(self, name: str) -> Any:
        exports = object.__getattribute__(self, "_exports")
        if name in exports:
            return exports[name]
        raise AttributeError(f"Module has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        exports = object.__getattribute__(self, "_exports")
        exports[name] = value

    def __dir__(self):
        exports = object.__getattribute__(self, "_exports")
        return list(exports.keys())

    def __repr__(self):
        exports = object.__getattribute__(self, "_exports")
        return f"<NapiModule exports={list(exports.keys())}>"


# Define C function pointer types matching the shim
FuncGetVersion = CFUNCTYPE(c_int, c_void_p, POINTER(c_uint32))
FuncGetUndefined = CFUNCTYPE(c_int, c_void_p, POINTER(c_void_p))
FuncGetNull = CFUNCTYPE(c_int, c_void_p, POINTER(c_void_p))
FuncGetGlobal = CFUNCTYPE(c_int, c_void_p, POINTER(c_void_p))
FuncGetBoolean = CFUNCTYPE(c_int, c_void_p, c_bool, POINTER(c_void_p))
FuncCreateInt32 = CFUNCTYPE(c_int, c_void_p, c_int32, POINTER(c_void_p))
FuncCreateUint32 = CFUNCTYPE(c_int, c_void_p, c_uint32, POINTER(c_void_p))
FuncCreateInt64 = CFUNCTYPE(c_int, c_void_p, c_int64, POINTER(c_void_p))
FuncCreateDouble = CFUNCTYPE(c_int, c_void_p, c_double, POINTER(c_void_p))
FuncCreateStringUtf8 = CFUNCTYPE(c_int, c_void_p, c_char_p, c_size_t, POINTER(c_void_p))
FuncGetValueBool = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_bool))
FuncGetValueInt32 = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_int32))
FuncGetValueUint32 = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_uint32))
FuncGetValueInt64 = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_int64))
FuncGetValueDouble = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_double))
FuncGetValueStringUtf8 = CFUNCTYPE(
    c_int, c_void_p, c_void_p, c_void_p, c_size_t, POINTER(c_size_t)
)
FuncTypeof = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_int))
FuncIsArray = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_bool))
FuncIsTypedarray = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_bool))
FuncIsError = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_bool))
FuncCreateObject = CFUNCTYPE(c_int, c_void_p, POINTER(c_void_p))
FuncCreateArray = CFUNCTYPE(c_int, c_void_p, POINTER(c_void_p))
FuncGetArrayLength = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_uint32))
FuncGetElement = CFUNCTYPE(c_int, c_void_p, c_void_p, c_uint32, POINTER(c_void_p))
FuncSetElement = CFUNCTYPE(c_int, c_void_p, c_void_p, c_uint32, c_void_p)
FuncGetProperty = CFUNCTYPE(c_int, c_void_p, c_void_p, c_void_p, POINTER(c_void_p))
FuncSetProperty = CFUNCTYPE(c_int, c_void_p, c_void_p, c_void_p, c_void_p)
FuncGetNamedProperty = CFUNCTYPE(c_int, c_void_p, c_void_p, c_char_p, POINTER(c_void_p))
FuncSetNamedProperty = CFUNCTYPE(c_int, c_void_p, c_void_p, c_char_p, c_void_p)
FuncGetCbInfo = CFUNCTYPE(
    c_int,
    c_void_p,
    c_void_p,
    POINTER(c_size_t),
    POINTER(c_void_p),
    POINTER(c_void_p),
    POINTER(c_void_p),
)
FuncCreateFunction = CFUNCTYPE(
    c_int, c_void_p, c_char_p, c_size_t, c_void_p, c_void_p, POINTER(c_void_p)
)
FuncCallFunction = CFUNCTYPE(
    c_int, c_void_p, c_void_p, c_void_p, c_size_t, POINTER(c_void_p), POINTER(c_void_p)
)
FuncDefineClass = CFUNCTYPE(
    c_int,
    c_void_p,
    c_char_p,
    c_size_t,
    c_void_p,
    c_void_p,
    c_size_t,
    c_void_p,
    POINTER(c_void_p),
)
FuncCreateReference = CFUNCTYPE(c_int, c_void_p, c_void_p, c_uint32, POINTER(c_void_p))
FuncDeleteReference = CFUNCTYPE(c_int, c_void_p, c_void_p)
FuncGetReferenceValue = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_void_p))
FuncRefReference = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_uint32))
FuncUnrefReference = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_uint32))
FuncThrow = CFUNCTYPE(c_int, c_void_p, c_void_p)
FuncThrowError = CFUNCTYPE(c_int, c_void_p, c_char_p, c_char_p)
FuncCreateError = CFUNCTYPE(c_int, c_void_p, c_void_p, c_void_p, POINTER(c_void_p))
FuncIsExceptionPending = CFUNCTYPE(c_int, c_void_p, POINTER(c_bool))
FuncGetAndClearLastException = CFUNCTYPE(c_int, c_void_p, POINTER(c_void_p))
FuncOpenHandleScope = CFUNCTYPE(c_int, c_void_p, POINTER(c_void_p))
FuncCloseHandleScope = CFUNCTYPE(c_int, c_void_p, c_void_p)
FuncCoerceToString = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_void_p))
FuncGetTypedarrayInfo = CFUNCTYPE(
    c_int,
    c_void_p,
    c_void_p,
    POINTER(c_int),
    POINTER(c_size_t),
    POINTER(c_void_p),
    POINTER(c_void_p),
    POINTER(c_size_t),
)
# Promise functions
FuncCreatePromise = CFUNCTYPE(c_int, c_void_p, POINTER(c_void_p), POINTER(c_void_p))
FuncResolveDeferred = CFUNCTYPE(c_int, c_void_p, c_void_p, c_void_p)
FuncRejectDeferred = CFUNCTYPE(c_int, c_void_p, c_void_p, c_void_p)
FuncIsPromise = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_bool))
# Threadsafe function
FuncCreateTsfn = CFUNCTYPE(
    c_int,
    c_void_p,
    c_void_p,
    c_void_p,
    c_void_p,
    c_size_t,
    c_size_t,
    c_void_p,
    c_void_p,
    c_void_p,
    c_void_p,
    POINTER(c_void_p),
)
FuncCallTsfn = CFUNCTYPE(c_int, c_void_p, c_void_p, c_int)
FuncAcquireTsfn = CFUNCTYPE(c_int, c_void_p)
FuncReleaseTsfn = CFUNCTYPE(c_int, c_void_p, c_int)
# Class/wrap functions
FuncWrap = CFUNCTYPE(
    c_int, c_void_p, c_void_p, c_void_p, c_void_p, c_void_p, POINTER(c_void_p)
)
FuncUnwrap = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_void_p))
FuncDefineClassImpl = CFUNCTYPE(
    c_int,
    c_void_p,
    c_char_p,
    c_size_t,
    c_void_p,
    c_void_p,
    c_size_t,
    c_void_p,
    POINTER(c_void_p),
)
# ArrayBuffer functions
FuncCreateArraybuffer = CFUNCTYPE(
    c_int, c_void_p, c_size_t, POINTER(c_void_p), POINTER(c_void_p)
)
FuncGetArraybufferInfo = CFUNCTYPE(
    c_int, c_void_p, c_void_p, POINTER(c_void_p), POINTER(c_size_t)
)
FuncIsDetachedArraybuffer = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_bool))
FuncDetachArraybuffer = CFUNCTYPE(c_int, c_void_p, c_void_p)
FuncIsArraybuffer = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_bool))
# TypedArray functions
FuncCreateTypedarray = CFUNCTYPE(
    c_int, c_void_p, c_int, c_size_t, c_void_p, c_size_t, POINTER(c_void_p)
)
# DataView functions
FuncCreateDataview = CFUNCTYPE(
    c_int, c_void_p, c_size_t, c_void_p, c_size_t, POINTER(c_void_p)
)
FuncGetDataviewInfo = CFUNCTYPE(
    c_int,
    c_void_p,
    c_void_p,
    POINTER(c_size_t),
    POINTER(c_void_p),
    POINTER(c_void_p),
    POINTER(c_size_t),
)
FuncIsDataview = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_bool))
# Buffer functions
FuncCreateBuffer = CFUNCTYPE(
    c_int, c_void_p, c_size_t, POINTER(c_void_p), POINTER(c_void_p)
)
FuncCreateBufferCopy = CFUNCTYPE(
    c_int, c_void_p, c_size_t, c_void_p, POINTER(c_void_p), POINTER(c_void_p)
)
FuncGetBufferInfo = CFUNCTYPE(
    c_int, c_void_p, c_void_p, POINTER(c_void_p), POINTER(c_size_t)
)
FuncIsBuffer = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_bool))
# External functions
FuncCreateExternal = CFUNCTYPE(
    c_int, c_void_p, c_void_p, c_void_p, c_void_p, POINTER(c_void_p)
)
FuncGetValueExternal = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_void_p))
# Additional error functions
FuncThrowTypeError = CFUNCTYPE(c_int, c_void_p, c_char_p, c_char_p)
FuncThrowRangeError = CFUNCTYPE(c_int, c_void_p, c_char_p, c_char_p)
FuncCreateTypeError = CFUNCTYPE(c_int, c_void_p, c_void_p, c_void_p, POINTER(c_void_p))
FuncCreateRangeError = CFUNCTYPE(c_int, c_void_p, c_void_p, c_void_p, POINTER(c_void_p))
# Instance creation
FuncNewInstance = CFUNCTYPE(
    c_int, c_void_p, c_void_p, c_size_t, POINTER(c_void_p), POINTER(c_void_p)
)
# Fatal exception
FuncFatalException = CFUNCTYPE(c_int, c_void_p, c_void_p)
# Get new target
FuncGetNewTarget = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_void_p))
# Property checking
FuncHasOwnProperty = CFUNCTYPE(c_int, c_void_p, c_void_p, c_void_p, POINTER(c_bool))
# Get all property names
FuncGetAllPropertyNames = CFUNCTYPE(
    c_int, c_void_p, c_void_p, c_int, c_int, c_int, POINTER(c_void_p)
)
# Get property names
FuncGetPropertyNames = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(c_void_p))
# Instance data
FuncSetInstanceData = CFUNCTYPE(c_int, c_void_p, c_void_p, c_void_p, c_void_p)
FuncGetInstanceData = CFUNCTYPE(c_int, c_void_p, POINTER(c_void_p))


# Property descriptor structure (matches C struct)
class NapiPropertyDescriptor(Structure):
    _fields_ = [
        ("utf8name", c_char_p),
        ("name", c_void_p),  # napi_value
        ("method", c_void_p),  # napi_callback
        ("getter", c_void_p),  # napi_callback
        ("setter", c_void_p),  # napi_callback
        ("value", c_void_p),  # napi_value
        ("attributes", c_uint32),
        ("data", c_void_p),
    ]


class NapiPythonFunctions(Structure):
    """Function pointer table matching the C shim."""

    _fields_ = [
        ("get_version", FuncGetVersion),
        ("get_undefined", FuncGetUndefined),
        ("get_null", FuncGetNull),
        ("get_global", FuncGetGlobal),
        ("get_boolean", FuncGetBoolean),
        ("create_int32", FuncCreateInt32),
        ("create_uint32", FuncCreateUint32),
        ("create_int64", FuncCreateInt64),
        ("create_double", FuncCreateDouble),
        ("create_string_utf8", FuncCreateStringUtf8),
        ("get_value_bool", FuncGetValueBool),
        ("get_value_int32", FuncGetValueInt32),
        ("get_value_uint32", FuncGetValueUint32),
        ("get_value_int64", FuncGetValueInt64),
        ("get_value_double", FuncGetValueDouble),
        ("get_value_string_utf8", FuncGetValueStringUtf8),
        ("typeof_", FuncTypeof),
        ("is_array", FuncIsArray),
        ("is_typedarray", FuncIsTypedarray),
        ("is_error", FuncIsError),
        ("create_object", FuncCreateObject),
        ("create_array", FuncCreateArray),
        ("get_array_length", FuncGetArrayLength),
        ("get_element", FuncGetElement),
        ("set_element", FuncSetElement),
        ("get_property", FuncGetProperty),
        ("set_property", FuncSetProperty),
        ("get_named_property", FuncGetNamedProperty),
        ("set_named_property", FuncSetNamedProperty),
        ("get_cb_info", FuncGetCbInfo),
        ("create_function", FuncCreateFunction),
        ("call_function", FuncCallFunction),
        ("define_class", FuncDefineClass),
        ("create_reference", FuncCreateReference),
        ("delete_reference", FuncDeleteReference),
        ("get_reference_value", FuncGetReferenceValue),
        ("reference_ref", FuncRefReference),
        ("reference_unref", FuncUnrefReference),
        ("throw_", FuncThrow),
        ("throw_error", FuncThrowError),
        ("create_error", FuncCreateError),
        ("is_exception_pending", FuncIsExceptionPending),
        ("get_and_clear_last_exception", FuncGetAndClearLastException),
        ("open_handle_scope", FuncOpenHandleScope),
        ("close_handle_scope", FuncCloseHandleScope),
        ("coerce_to_string", FuncCoerceToString),
        ("get_typedarray_info", FuncGetTypedarrayInfo),
        # Promise functions
        ("create_promise", FuncCreatePromise),
        ("resolve_deferred", FuncResolveDeferred),
        ("reject_deferred", FuncRejectDeferred),
        ("is_promise", FuncIsPromise),
        # Threadsafe functions
        ("create_tsfn", FuncCreateTsfn),
        ("call_tsfn", FuncCallTsfn),
        ("acquire_tsfn", FuncAcquireTsfn),
        ("release_tsfn", FuncReleaseTsfn),
        # Class/wrap functions
        ("wrap", FuncWrap),
        ("unwrap", FuncUnwrap),
        ("define_class_impl", FuncDefineClassImpl),
        # ArrayBuffer functions
        ("create_arraybuffer", FuncCreateArraybuffer),
        ("get_arraybuffer_info", FuncGetArraybufferInfo),
        ("is_detached_arraybuffer", FuncIsDetachedArraybuffer),
        ("detach_arraybuffer", FuncDetachArraybuffer),
        ("is_arraybuffer", FuncIsArraybuffer),
        # TypedArray functions
        ("create_typedarray", FuncCreateTypedarray),
        # DataView functions
        ("create_dataview", FuncCreateDataview),
        ("get_dataview_info", FuncGetDataviewInfo),
        ("is_dataview", FuncIsDataview),
        # Buffer functions
        ("create_buffer", FuncCreateBuffer),
        ("create_buffer_copy", FuncCreateBufferCopy),
        ("get_buffer_info", FuncGetBufferInfo),
        ("is_buffer", FuncIsBuffer),
        # External functions
        ("create_external", FuncCreateExternal),
        ("get_value_external", FuncGetValueExternal),
        # Additional error functions
        ("throw_type_error", FuncThrowTypeError),
        ("throw_range_error", FuncThrowRangeError),
        ("create_type_error", FuncCreateTypeError),
        ("create_range_error", FuncCreateRangeError),
        # Instance creation
        ("new_instance", FuncNewInstance),
        # Fatal exception
        ("fatal_exception", FuncFatalException),
        # Get new target
        ("get_new_target", FuncGetNewTarget),
        # Property checking
        ("has_own_property", FuncHasOwnProperty),
        # Get all property names
        ("get_all_property_names", FuncGetAllPropertyNames),
        # Get property names
        ("get_property_names", FuncGetPropertyNames),
        # Instance data
        ("set_instance_data", FuncSetInstanceData),
        ("get_instance_data", FuncGetInstanceData),
    ]


# Global state
_shim_lib: Optional[CDLL] = None
_func_table: Optional[NapiPythonFunctions] = None
_callback_refs: List[Any] = []  # prevent GC of callbacks


def _get_shim_path() -> Path:
    """Get path to the NAPI shim library."""
    return Path(__file__).parent / "_native" / "libnapi_shim.dylib"


def _init_shim() -> CDLL:
    """Initialize the NAPI shim library."""
    global _shim_lib, _func_table

    if _shim_lib is not None:
        return _shim_lib

    shim_path = _get_shim_path()
    if not shim_path.exists():
        raise FileNotFoundError(f"NAPI shim library not found: {shim_path}")

    # Load the shim with RTLD_GLOBAL so its symbols are available to other libs
    _shim_lib = CDLL(str(shim_path), mode=ctypes.RTLD_GLOBAL)

    # Get the function to set our implementations
    set_funcs = _shim_lib.napi_python_set_functions
    set_funcs.argtypes = [POINTER(NapiPythonFunctions)]
    set_funcs.restype = None

    # Create function table with our Python implementations
    _func_table = _create_function_table()

    # Register with the shim
    set_funcs(byref(_func_table))

    print(f"[napi-python] Loaded shim: {shim_path}")
    return _shim_lib


def _create_function_table() -> NapiPythonFunctions:
    """Create the function pointer table."""
    global _callback_refs

    ctx = get_default_context()

    # Helper to get env from handle
    def get_env(env_ptr: int) -> Optional[Env]:
        return ctx.get_env(env_ptr)

    # Wrapper implementations that match C calling convention
    @FuncGetVersion
    def get_version(env, result):
        result[0] = 9
        return napi_status.napi_ok

    @FuncGetUndefined
    def get_undefined(env, result):
        result[0] = Constant.UNDEFINED
        return napi_status.napi_ok

    @FuncGetNull
    def get_null(env, result):
        result[0] = Constant.NULL
        return napi_status.napi_ok

    @FuncGetGlobal
    def get_global(env, result):
        result[0] = Constant.GLOBAL
        return napi_status.napi_ok

    @FuncGetBoolean
    def get_boolean(env, value, result):
        result[0] = Constant.TRUE if value else Constant.FALSE
        return napi_status.napi_ok

    @FuncCreateInt32
    def create_int32(env, value, result):
        handle = ctx.add_value(int(value))
        result[0] = handle
        return napi_status.napi_ok

    @FuncCreateUint32
    def create_uint32(env, value, result):
        handle = ctx.add_value(int(value))
        result[0] = handle
        return napi_status.napi_ok

    @FuncCreateInt64
    def create_int64(env, value, result):
        handle = ctx.add_value(int(value))
        result[0] = handle
        return napi_status.napi_ok

    @FuncCreateDouble
    def create_double(env, value, result):
        handle = ctx.add_value(float(value))
        result[0] = handle
        return napi_status.napi_ok

    @FuncCreateStringUtf8
    def create_string_utf8(env, string, length, result):
        if string:
            if length == 0xFFFFFFFFFFFFFFFF or length < 0:  # NAPI_AUTO_LENGTH
                py_str = string.decode("utf-8")
            else:
                py_str = string[:length].decode("utf-8")
        else:
            py_str = ""
        handle = ctx.add_value(py_str)
        result[0] = handle
        return napi_status.napi_ok

    @FuncGetValueBool
    def get_value_bool(env, value, result):
        py_val = ctx.python_value_from_napi(value)
        result[0] = bool(py_val)
        return napi_status.napi_ok

    @FuncGetValueInt32
    def get_value_int32(env, value, result):
        py_val = ctx.python_value_from_napi(value)
        if py_val is None:
            result[0] = 0
            return napi_status.napi_number_expected
        try:
            result[0] = int(py_val) & 0xFFFFFFFF
        except (TypeError, ValueError):
            result[0] = 0
            return napi_status.napi_number_expected
        return napi_status.napi_ok

    @FuncGetValueUint32
    def get_value_uint32(env, value, result):
        py_val = ctx.python_value_from_napi(value)
        if py_val is None:
            result[0] = 0
            return napi_status.napi_number_expected
        try:
            result[0] = int(py_val) & 0xFFFFFFFF
        except (TypeError, ValueError):
            result[0] = 0
            return napi_status.napi_number_expected
        return napi_status.napi_ok

    @FuncGetValueInt64
    def get_value_int64(env, value, result):
        py_val = ctx.python_value_from_napi(value)
        if py_val is None:
            result[0] = 0
            return napi_status.napi_number_expected
        try:
            result[0] = int(py_val)
        except (TypeError, ValueError):
            result[0] = 0
            return napi_status.napi_number_expected
        return napi_status.napi_ok

    @FuncGetValueDouble
    def get_value_double(env, value, result):
        py_val = ctx.python_value_from_napi(value)
        if py_val is None:
            result[0] = 0.0
            return napi_status.napi_number_expected
        try:
            result[0] = float(py_val)
        except (TypeError, ValueError):
            result[0] = 0.0
            return napi_status.napi_number_expected
        return napi_status.napi_ok

    @FuncGetValueStringUtf8
    def get_value_string_utf8(env, value, buf, bufsize, result):
        py_val = ctx.python_value_from_napi(value)
        if not isinstance(py_val, str):
            return napi_status.napi_string_expected
        encoded = py_val.encode("utf-8")

        if not buf:
            # No buffer - just return the length
            if not result:
                return napi_status.napi_invalid_arg
            result[0] = len(encoded)
        elif bufsize != 0:
            # Copy string to buffer
            copy_len = min(len(encoded), bufsize - 1)
            if copy_len > 0:
                ctypes.memmove(buf, encoded, copy_len)
            # Null terminate
            ctypes.memset(buf + copy_len, 0, 1)
            if result:
                result[0] = copy_len
        elif result:
            result[0] = 0

        return napi_status.napi_ok

    @FuncTypeof
    def typeof_(env, value, result):
        from ._runtime.handle import Undefined

        py_val = ctx.python_value_from_napi(value)
        if py_val is Undefined:
            result[0] = napi_valuetype.napi_undefined
        elif py_val is None:
            result[0] = napi_valuetype.napi_null
        elif isinstance(py_val, bool):
            result[0] = napi_valuetype.napi_boolean
        elif isinstance(py_val, (int, float)):
            result[0] = napi_valuetype.napi_number
        elif isinstance(py_val, str):
            result[0] = napi_valuetype.napi_string
        elif callable(py_val):
            result[0] = napi_valuetype.napi_function
        else:
            result[0] = napi_valuetype.napi_object
        return napi_status.napi_ok

    @FuncIsArray
    def is_array(env, value, result):
        py_val = ctx.python_value_from_napi(value)
        result[0] = isinstance(py_val, list)
        return napi_status.napi_ok

    @FuncIsTypedarray
    def is_typedarray(env, value, result):
        from ._values.arraybuffer import TypedArray, is_typedarray as _is_typedarray

        py_val = ctx.python_value_from_napi(value)
        # Check for our TypedArray class or bytes/bytearray
        result[0] = _is_typedarray(py_val) or isinstance(
            py_val, (bytes, bytearray, memoryview)
        )
        return napi_status.napi_ok

    @FuncIsError
    def is_error(env, value, result):
        py_val = ctx.python_value_from_napi(value)
        result[0] = isinstance(py_val, Exception)
        return napi_status.napi_ok

    @FuncCreateObject
    def create_object(env, result):
        handle = ctx.add_value({})
        result[0] = handle
        return napi_status.napi_ok

    @FuncCreateArray
    def create_array(env, result):
        handle = ctx.add_value([])
        result[0] = handle
        return napi_status.napi_ok

    @FuncGetArrayLength
    def get_array_length(env, value, result):
        py_val = ctx.python_value_from_napi(value)
        result[0] = len(py_val) if isinstance(py_val, list) else 0
        return napi_status.napi_ok

    @FuncGetElement
    def get_element(env, obj, index, result):
        py_obj = ctx.python_value_from_napi(obj)
        if isinstance(py_obj, list) and 0 <= index < len(py_obj):
            result[0] = ctx.add_value(py_obj[index])
        else:
            result[0] = Constant.UNDEFINED
        return napi_status.napi_ok

    @FuncSetElement
    def set_element(env, obj, index, value):
        py_obj = ctx.python_value_from_napi(obj)
        py_val = ctx.python_value_from_napi(value)
        if isinstance(py_obj, list):
            while len(py_obj) <= index:
                py_obj.append(None)
            py_obj[index] = py_val
        return napi_status.napi_ok

    @FuncGetProperty
    def get_property(env, obj, key, result):
        py_obj = ctx.python_value_from_napi(obj)
        py_key = ctx.python_value_from_napi(key)
        if isinstance(py_obj, dict):
            result[0] = ctx.add_value(py_obj.get(py_key))
        else:
            result[0] = Constant.UNDEFINED
        return napi_status.napi_ok

    @FuncSetProperty
    def set_property(env, obj, key, value):
        py_obj = ctx.python_value_from_napi(obj)
        py_key = ctx.python_value_from_napi(key)
        py_val = ctx.python_value_from_napi(value)
        if isinstance(py_obj, dict):
            py_obj[py_key] = py_val
        return napi_status.napi_ok

    @FuncGetNamedProperty
    def get_named_property(env, obj, name, result):
        py_obj = ctx.python_value_from_napi(obj)
        key = name.decode("utf-8") if name else ""
        if isinstance(py_obj, dict):
            val = py_obj.get(key)
            result[0] = ctx.add_value(val)
        else:
            result[0] = Constant.UNDEFINED
        return napi_status.napi_ok

    @FuncSetNamedProperty
    def set_named_property(env, obj, name, value):
        py_obj = ctx.python_value_from_napi(obj)
        key = name.decode("utf-8") if name else ""
        py_val = ctx.python_value_from_napi(value)
        if isinstance(py_obj, dict):
            py_obj[key] = py_val
        return napi_status.napi_ok

    @FuncGetCbInfo
    def get_cb_info(env, cbinfo, argc, argv, this_arg, data):
        cb_info = ctx.get_callback_info(cbinfo)
        if argv and argc:
            argc_val = argc[0]
            args = cb_info.args
            for i in range(min(argc_val, len(args))):
                argv[i] = ctx.add_value(args[i])
            for i in range(len(args), argc_val):
                argv[i] = Constant.UNDEFINED
        if argc:
            argc[0] = len(cb_info.args)
        if this_arg:
            this_arg[0] = (
                ctx.add_value(cb_info.thiz) if cb_info.thiz else Constant.UNDEFINED
            )
        if data:
            data[0] = cb_info.data
        return napi_status.napi_ok

    @FuncCreateFunction
    def create_function(env_id, name, length, cb, data, result):
        """Create a JavaScript function from a native callback."""
        env_obj = get_env(env_id)
        if not env_obj:
            return napi_status.napi_invalid_arg

        # Get function name
        try:
            if name and length > 0 and length < 1000:
                func_name = name[:length].decode("utf-8", errors="replace")
            elif name:
                # Try to decode as null-terminated string
                func_name = name.split(b"\x00")[0].decode("utf-8", errors="replace")
            else:
                func_name = "anonymous"
        except Exception:
            func_name = "anonymous"

        # Create a Python callable that wraps the native callback
        # cb is a C function pointer: napi_value (*)(napi_env, napi_callback_info)
        native_cb = ctypes.cast(cb, CFUNCTYPE(c_void_p, c_void_p, c_void_p))

        def wrapped_function(*args):
            """Python wrapper for native NAPI function."""
            nonlocal env_obj, native_cb, data

            # Open a scope for this call
            scope = ctx.open_scope(env_obj)

            try:
                # Set up callback info
                scope.callback_info.args = list(args)
                scope.callback_info.thiz = None
                scope.callback_info.data = data
                scope.callback_info.fn = wrapped_function

                # Call the native function
                # Pass env ID and scope ID (which serves as callback_info)
                ret = native_cb(env_obj.id, scope.id)

                # Convert result back to Python
                if ret:
                    return ctx.python_value_from_napi(ret)
                return None

            finally:
                ctx.close_scope(env_obj, scope)

        # Set function name
        wrapped_function.__name__ = func_name

        # Store reference to prevent GC
        _callback_refs.append(wrapped_function)
        _callback_refs.append(native_cb)

        # Add to handle store and return
        handle = ctx.add_value(wrapped_function)
        result[0] = handle
        return napi_status.napi_ok

    @FuncCallFunction
    def call_function(env_id, recv, func, argc, argv, result):
        """Call a JavaScript function with receiver (this)."""
        env_obj = get_env(env_id)
        if not env_obj:
            if result:
                result[0] = Constant.UNDEFINED
            return napi_status.napi_invalid_arg

        # Validate recv - emnapi requires it
        if not recv:
            if result:
                result[0] = Constant.UNDEFINED
            return napi_status.napi_invalid_arg

        # Get the function
        py_func = ctx.python_value_from_napi(func)
        if not func:
            if result:
                result[0] = Constant.UNDEFINED
            return napi_status.napi_invalid_arg
        if not callable(py_func):
            if result:
                result[0] = Constant.UNDEFINED
            return napi_status.napi_invalid_arg

        # Get receiver (this value)
        py_recv = ctx.python_value_from_napi(recv)

        # Validate argc/argv
        if argc > 0 and not argv:
            if result:
                result[0] = Constant.UNDEFINED
            return napi_status.napi_invalid_arg

        # Get arguments
        args = []
        for i in range(argc):
            arg_handle = argv[i] if argv else Constant.UNDEFINED
            args.append(ctx.python_value_from_napi(arg_handle))

        # Call the function
        try:
            # Check if this is a wrapped NAPI function that needs callback_info
            if hasattr(py_func, '__name__') and py_recv is not None:
                # For wrapped NAPI functions, we need to set up scope with thiz
                # Check if this function was created by our create_function
                # by checking for our wrapper signature
                scope = ctx.open_scope(env_obj)
                try:
                    scope.callback_info.thiz = py_recv
                    scope.callback_info.args = args
                    ret = py_func(*args)
                finally:
                    ctx.close_scope(env_obj, scope)
            else:
                # Regular Python function call
                ret = py_func(*args)

            if result:
                result[0] = ctx.add_value(ret)
        except Exception as e:
            env_obj.last_exception = e
            if result:
                result[0] = Constant.UNDEFINED
            return napi_status.napi_pending_exception

        return napi_status.napi_ok

    # Storage for wrapped native objects (for napi_wrap/unwrap)
    _wrap_store = {}
    _wrap_counter = [1]

    @FuncDefineClass
    def define_class(
        env_id, name, length, constructor, data, prop_count, props, result
    ):
        """Define a JavaScript class (legacy - forwards to define_class_impl)."""
        # This is called by the C shim via the old function pointer
        # We'll let define_class_impl handle the actual implementation
        return define_class_impl(
            env_id, name, length, constructor, data, prop_count, props, result
        )

    @FuncCreateReference
    def create_reference(env_id, value, initial_refcount, result):
        """Create a reference to a value."""
        env_obj = get_env(env_id)
        if not env_obj:
            return napi_status.napi_invalid_arg

        py_value = ctx.python_value_from_napi(value)

        # Create a proper Reference object
        ref = Reference.create(
            ctx, env_obj, py_value, initial_refcount, ReferenceOwnership.kUserland
        )

        if result:
            result[0] = ref.id
        return napi_status.napi_ok

    @FuncDeleteReference
    def delete_reference(env_id, ref_id):
        """Delete a reference."""
        ref = ctx.get_ref(ref_id)
        if ref:
            ref.dispose()
        return napi_status.napi_ok

    @FuncGetReferenceValue
    def get_reference_value(env_id, ref_id, result):
        """Get the value from a reference."""
        ref = ctx.get_ref(ref_id)
        if ref:
            value = ref.get()
            if value is not None:
                if result:
                    result[0] = ctx.add_value(value)
                return napi_status.napi_ok
        # Reference not found or value was collected
        if result:
            result[0] = Constant.UNDEFINED
        return napi_status.napi_ok

    @FuncRefReference
    def reference_ref(env_id, ref_id, result):
        """Increment reference count."""
        ref = ctx.get_ref(ref_id)
        if not ref:
            return napi_status.napi_invalid_arg

        new_count = ref.ref()
        if result:
            result[0] = new_count
        return napi_status.napi_ok

    @FuncUnrefReference
    def reference_unref(env_id, ref_id, result):
        """Decrement reference count."""
        ref = ctx.get_ref(ref_id)
        if not ref:
            return napi_status.napi_invalid_arg

        new_count = ref.unref()
        if result:
            result[0] = new_count
        return napi_status.napi_ok

    @FuncThrow
    def throw_(env, error):
        return napi_status.napi_ok

    @FuncThrowError
    def throw_error(env, code, msg):
        return napi_status.napi_ok

    @FuncCreateError
    def create_error(env_id, code_handle, msg_handle, result):
        """Create an Error object."""
        env_obj = get_env(env_id)
        if not env_obj:
            if result:
                result[0] = Constant.UNDEFINED
            return napi_status.napi_invalid_arg

        # msg is required
        if not msg_handle:
            if result:
                result[0] = Constant.UNDEFINED
            return napi_status.napi_invalid_arg

        try:
            # Get the message string
            msg_value = ctx.python_value_from_napi(msg_handle)
            if not isinstance(msg_value, str):
                if result:
                    result[0] = Constant.UNDEFINED
                return napi_status.napi_string_expected

            # Create the error
            error = Exception(msg_value)

            # Add code attribute if provided
            if code_handle and code_handle != 0:
                code_value = ctx.python_value_from_napi(code_handle)
                if isinstance(code_value, str):
                    error.code = code_value

            # Store and return the error
            if result:
                result[0] = ctx.add_value(error)
            return napi_status.napi_ok
        except Exception as e:
            print(f"[napi-python] create_error failed: {e}")
            if result:
                result[0] = Constant.UNDEFINED
            return napi_status.napi_generic_failure

    @FuncIsExceptionPending
    def is_exception_pending(env, result):
        env_obj = get_env(env)
        if env_obj and env_obj.last_exception is not None:
            result[0] = True
        else:
            result[0] = False
        return napi_status.napi_ok

    @FuncGetAndClearLastException
    def get_and_clear_last_exception(env, result):
        env_obj = get_env(env)
        if env_obj and env_obj.last_exception is not None:
            exc = env_obj.last_exception
            env_obj.last_exception = None
            result[0] = ctx.add_value(exc)
        else:
            result[0] = Constant.UNDEFINED
        return napi_status.napi_ok

    @FuncOpenHandleScope
    def open_handle_scope(env, result):
        env_obj = get_env(env)
        if env_obj:
            scope = ctx.open_scope(env_obj)
            result[0] = scope.id
        return napi_status.napi_ok

    @FuncCloseHandleScope
    def close_handle_scope(env, scope):
        env_obj = get_env(env)
        if env_obj:
            ctx.close_scope(env_obj)
        return napi_status.napi_ok

    @FuncCoerceToString
    def coerce_to_string(env, value, result):
        py_val = ctx.python_value_from_napi(value)
        result[0] = ctx.add_value(str(py_val))
        return napi_status.napi_ok

    @FuncGetTypedarrayInfo
    def get_typedarray_info(
        env, typedarray, type_out, length, data, arraybuffer, byte_offset
    ):
        from ._values.arraybuffer import (
            TypedArray,
            DataView,
            is_typedarray as _is_typedarray,
        )

        py_val = ctx.python_value_from_napi(typedarray)

        # Handle our TypedArray class
        if _is_typedarray(py_val):
            if type_out:
                type_out[0] = py_val.array_type
            if length:
                length[0] = py_val.length
            if data:
                data[0] = py_val.data_ptr
            if arraybuffer:
                arraybuffer[0] = ctx.add_value(py_val.buffer)
            if byte_offset:
                byte_offset[0] = py_val.byte_offset
            return napi_status.napi_ok

        # Handle DataView
        if isinstance(py_val, DataView):
            if type_out:
                return napi_status.napi_generic_failure  # DataView has no type
            if length:
                length[0] = py_val.byte_length
            if data:
                data[0] = py_val.data_ptr
            if arraybuffer:
                arraybuffer[0] = ctx.add_value(py_val.buffer)
            if byte_offset:
                byte_offset[0] = py_val.byte_offset
            return napi_status.napi_ok

        # Legacy: handle bytes/bytearray as Uint8Array
        if isinstance(py_val, (bytes, bytearray)):
            if type_out:
                type_out[0] = 1  # napi_uint8_array
            if length:
                length[0] = len(py_val)
            if data:
                # Create a ctypes buffer from the bytes
                if isinstance(py_val, bytes):
                    buf = ctypes.create_string_buffer(py_val, len(py_val))
                else:
                    buf = (ctypes.c_uint8 * len(py_val)).from_buffer(py_val)
                data[0] = ctypes.addressof(buf)
                # Keep reference to prevent GC
                _callback_refs.append(buf)
            if arraybuffer:
                arraybuffer[0] = typedarray  # Return same handle
            if byte_offset:
                byte_offset[0] = 0
            return napi_status.napi_ok

        return napi_status.napi_arraybuffer_expected

    # =========================================================================
    # Class / Wrap Functions
    # =========================================================================

    @FuncWrap
    def wrap(env_id, js_object, native_object, finalize_cb, finalize_hint, result):
        """Associate a native pointer with a JavaScript object."""
        env_obj = get_env(env_id)
        if not env_obj:
            if result:
                result[0] = 0
            return napi_status.napi_ok  # Be lenient

        # Handle None/0 handles gracefully
        if js_object is None or js_object == 0:
            if result:
                result[0] = 0
            return napi_status.napi_ok

        try:
            py_obj = ctx.python_value_from_napi(js_object)
        except Exception:
            if result:
                result[0] = 0
            return napi_status.napi_ok

        if py_obj is None:
            if result:
                result[0] = 0
            return napi_status.napi_ok  # Be lenient

        # Store the native pointer on the object
        try:
            py_obj.__napi_native__ = native_object
            py_obj.__napi_weak_ref_id__ = None
            if finalize_cb:
                py_obj.__napi_weak_ref_id__ = _wrap_counter[0]
                _wrap_counter[0] += 1
                _wrap_store[py_obj.__napi_weak_ref_id__] = {
                    "obj": py_obj,
                    "native": native_object,
                    "finalize_cb": finalize_cb,
                    "finalize_hint": finalize_hint,
                }
        except AttributeError:
            # Object doesn't support attribute assignment, store in dict
            obj_id = id(py_obj)
            _wrap_store[obj_id] = native_object

        if result:
            result[0] = 0  # No reference created
        return napi_status.napi_ok

    @FuncUnwrap
    def unwrap(env_id, js_object, result):
        """Get the native pointer from a JavaScript object."""
        env_obj = get_env(env_id)
        if not env_obj:
            return napi_status.napi_invalid_arg

        py_obj = ctx.python_value_from_napi(js_object)
        if py_obj is None:
            return napi_status.napi_invalid_arg

        # Try to get the native pointer
        try:
            native_ptr = getattr(py_obj, "__napi_native__", None)
            if native_ptr is not None:
                if result:
                    result[0] = native_ptr
                return napi_status.napi_ok
        except AttributeError:
            pass

        # Try the dict fallback
        obj_id = id(py_obj)
        native_ptr = _wrap_store.get(obj_id)
        if native_ptr is not None:
            if result:
                result[0] = native_ptr
            return napi_status.napi_ok

        if result:
            result[0] = 0
        return napi_status.napi_invalid_arg

    @FuncDefineClassImpl
    def define_class_impl(
        env_id, name, length, constructor_cb, data, prop_count, props, result
    ):
        """Define a JavaScript class with constructor and methods."""
        env_obj = get_env(env_id)
        if not env_obj:
            return napi_status.napi_invalid_arg

        # Get class name
        try:
            if name and length > 0 and length < 1000:
                class_name = name[:length].decode("utf-8", errors="replace")
            elif name:
                class_name = name.split(b"\x00")[0].decode("utf-8", errors="replace")
            else:
                class_name = "NapiClass"
        except Exception:
            class_name = "NapiClass"

        # Cast constructor callback
        native_ctor = ctypes.cast(
            constructor_cb, CFUNCTYPE(c_void_p, c_void_p, c_void_p)
        )
        _callback_refs.append(native_ctor)

        # Create the wrapper class
        class NapiClassInstance:
            """Instance of a NAPI-defined class."""

            __napi_native__ = None
            __napi_class_name__ = class_name

            def __init__(self, *args):
                """Call the native constructor."""
                # Open a scope for this call
                scope = ctx.open_scope(env_obj)
                try:
                    # Set up callback info
                    scope.callback_info.args = list(args)
                    scope.callback_info.thiz = self
                    scope.callback_info.data = data
                    scope.callback_info.fn = self.__init__
                    scope.callback_info.new_target = type(self)

                    # Call the native constructor
                    ret = native_ctor(env_obj.id, scope.id)

                    # The constructor typically calls napi_wrap to associate native data
                finally:
                    ctx.close_scope(env_obj, scope)

            def __repr__(self):
                return f"<{self.__napi_class_name__} instance>"

        # Set class name
        NapiClassInstance.__name__ = class_name
        NapiClassInstance.__qualname__ = class_name

        # Process properties (methods, getters, setters)
        if prop_count > 0 and props:
            # Calculate property descriptor size
            prop_size = ctypes.sizeof(NapiPropertyDescriptor)

            for i in range(prop_count):
                # Read property descriptor
                prop_ptr = props + (i * prop_size)
                prop_desc = NapiPropertyDescriptor.from_address(prop_ptr)

                # Get property name
                if prop_desc.utf8name:
                    prop_name = prop_desc.utf8name.decode("utf-8", errors="replace")
                elif prop_desc.name:
                    prop_name = str(ctx.python_value_from_napi(prop_desc.name))
                else:
                    continue

                attributes = prop_desc.attributes
                is_static = (attributes & 0x400) != 0  # napi_static = 1 << 10
                prop_data = prop_desc.data

                # Handle method
                if prop_desc.method:
                    method_cb = ctypes.cast(
                        prop_desc.method, CFUNCTYPE(c_void_p, c_void_p, c_void_p)
                    )
                    _callback_refs.append(method_cb)

                    def make_method(cb, pdata):
                        def method(self, *args):
                            scope = ctx.open_scope(env_obj)
                            try:
                                scope.callback_info.args = list(args)
                                scope.callback_info.thiz = self
                                scope.callback_info.data = pdata
                                ret = cb(env_obj.id, scope.id)
                                if ret:
                                    return ctx.python_value_from_napi(ret)
                                return None
                            finally:
                                ctx.close_scope(env_obj, scope)

                        return method

                    method_func = make_method(method_cb, prop_data)
                    method_func.__name__ = prop_name

                    if is_static:
                        setattr(NapiClassInstance, prop_name, staticmethod(method_func))
                    else:
                        setattr(NapiClassInstance, prop_name, method_func)

                # Handle getter/setter
                elif prop_desc.getter or prop_desc.setter:
                    fget = None
                    fset = None

                    if prop_desc.getter:
                        getter_cb = ctypes.cast(
                            prop_desc.getter, CFUNCTYPE(c_void_p, c_void_p, c_void_p)
                        )
                        _callback_refs.append(getter_cb)

                        def make_getter(cb, pdata):
                            def getter(self):
                                scope = ctx.open_scope(env_obj)
                                try:
                                    scope.callback_info.args = []
                                    scope.callback_info.thiz = self
                                    scope.callback_info.data = pdata
                                    ret = cb(env_obj.id, scope.id)
                                    if ret:
                                        return ctx.python_value_from_napi(ret)
                                    return None
                                finally:
                                    ctx.close_scope(env_obj, scope)

                            return getter

                        fget = make_getter(getter_cb, prop_data)

                    if prop_desc.setter:
                        setter_cb = ctypes.cast(
                            prop_desc.setter, CFUNCTYPE(c_void_p, c_void_p, c_void_p)
                        )
                        _callback_refs.append(setter_cb)

                        def make_setter(cb, pdata):
                            def setter(self, value):
                                scope = ctx.open_scope(env_obj)
                                try:
                                    scope.callback_info.args = [value]
                                    scope.callback_info.thiz = self
                                    scope.callback_info.data = pdata
                                    cb(env_obj.id, scope.id)
                                finally:
                                    ctx.close_scope(env_obj, scope)

                            return setter

                        fset = make_setter(setter_cb, prop_data)

                    setattr(NapiClassInstance, prop_name, property(fget, fset))

                # Handle value
                elif prop_desc.value:
                    value = ctx.python_value_from_napi(prop_desc.value)
                    setattr(NapiClassInstance, prop_name, value)

        # Keep reference to prevent GC
        _callback_refs.append(NapiClassInstance)

        # Return the class as a handle
        if result:
            result[0] = ctx.add_value(NapiClassInstance)

        return napi_status.napi_ok

    # =========================================================================
    # Promise Functions
    # =========================================================================

    @FuncCreatePromise
    def create_promise(env_id, deferred_out, promise_out):
        """Create a promise and deferred pair."""
        import asyncio

        env_obj = get_env(env_id)
        if not env_obj:
            return napi_status.napi_invalid_arg

        # Create an asyncio Future
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # No event loop, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        future = loop.create_future()

        # Store the deferred (future + loop) and get an ID
        deferred_id = ctx.store_deferred({"future": future, "loop": loop})

        # Store the future as a value and get a handle
        promise_handle = ctx.add_value(future)

        if deferred_out:
            deferred_out[0] = deferred_id
        if promise_out:
            promise_out[0] = promise_handle

        return napi_status.napi_ok

    @FuncResolveDeferred
    def resolve_deferred(env_id, deferred_id, resolution):
        """Resolve a deferred promise."""
        env_obj = get_env(env_id)
        if not env_obj:
            return napi_status.napi_invalid_arg

        deferred = ctx.get_deferred(deferred_id)
        if not deferred:
            return napi_status.napi_invalid_arg

        future = deferred["future"]
        loop = deferred["loop"]

        # Get the Python value for resolution
        py_value = ctx.python_value_from_napi(resolution)

        # Resolve the future (thread-safe)
        if not future.done():
            loop.call_soon_threadsafe(future.set_result, py_value)

        # Clean up
        ctx.delete_deferred(deferred_id)

        return napi_status.napi_ok

    @FuncRejectDeferred
    def reject_deferred(env_id, deferred_id, rejection):
        """Reject a deferred promise."""
        env_obj = get_env(env_id)
        if not env_obj:
            return napi_status.napi_invalid_arg

        deferred = ctx.get_deferred(deferred_id)
        if not deferred:
            return napi_status.napi_invalid_arg

        future = deferred["future"]
        loop = deferred["loop"]

        # Get the Python value for rejection
        py_value = ctx.python_value_from_napi(rejection)

        # Convert to exception if needed
        if isinstance(py_value, Exception):
            exc = py_value
        else:
            exc = Exception(str(py_value) if py_value else "Promise rejected")

        # Reject the future (thread-safe)
        if not future.done():
            loop.call_soon_threadsafe(future.set_exception, exc)

        # Clean up
        ctx.delete_deferred(deferred_id)

        return napi_status.napi_ok

    @FuncIsPromise
    def is_promise(env_id, value, result):
        """Check if a value is a promise (asyncio.Future)."""
        import asyncio

        if not result:
            return napi_status.napi_invalid_arg

        py_value = ctx.python_value_from_napi(value)
        result[0] = isinstance(py_value, asyncio.Future)
        return napi_status.napi_ok

    # =========================================================================
    # Threadsafe Function Support
    # =========================================================================

    # Storage for threadsafe functions
    _tsfn_store = {}
    _tsfn_counter = [1]  # Use list to allow modification in nested function

    @FuncCreateTsfn
    def create_tsfn(
        env_id,
        func,
        async_resource,
        async_resource_name,
        max_queue_size,
        initial_thread_count,
        thread_finalize_data,
        thread_finalize_cb,
        context,
        call_js_cb,
        result,
    ):
        """Create a threadsafe function."""
        import asyncio
        import threading
        import queue

        env_obj = get_env(env_id)
        if not env_obj:
            return napi_status.napi_invalid_arg

        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Create the threadsafe function data
        tsfn_id = _tsfn_counter[0]
        _tsfn_counter[0] += 1

        # Cast call_js_cb to a callable
        if call_js_cb:
            CallJsCb = CFUNCTYPE(None, c_void_p, c_void_p, c_void_p, c_void_p)
            js_cb = ctypes.cast(call_js_cb, CallJsCb)
        else:
            js_cb = None

        # Store the function as a persistent reference to prevent it from
        # being overwritten when scopes are closed
        func_ref = None
        func_value = None
        if func is not None and func != 0:
            try:
                func_value = ctx.python_value_from_napi(func)
                if func_value is not None:
                    # Create a reference to preserve the function
                    func_ref = _wrap_counter[0]
                    _wrap_counter[0] += 1
                    _wrap_store[func_ref] = {"value": func_value, "refcount": 1}
                    pass  # Stored func as persistent ref
            except Exception:
                pass  # Failed to store func

        tsfn_data = {
            "id": tsfn_id,
            "env_id": env_id,
            "func": func,
            "func_ref": func_ref,  # Persistent reference to the function
            "func_value": func_value,  # Direct reference to prevent GC
            "context": context,
            "call_js_cb": js_cb,
            "loop": loop,
            "queue": queue.Queue(maxsize=max_queue_size if max_queue_size > 0 else 0),
            "max_queue_size": max_queue_size,
            "thread_count": initial_thread_count,
            "is_closing": False,  # Proper closing state
            "closed": False,
            "finalize_data": thread_finalize_data,
            "finalize_cb": thread_finalize_cb,
        }

        # Debug: print(f"[napi-python] create_tsfn: id={tsfn_id}, func={func}, func_ref={func_ref}")
        _tsfn_store[tsfn_id] = tsfn_data
        _callback_refs.append(tsfn_data)
        if js_cb:
            _callback_refs.append(js_cb)

        if result:
            result[0] = tsfn_id

        return napi_status.napi_ok

    @FuncCallTsfn
    def call_tsfn(tsfn_id, data, is_blocking):
        """Call a threadsafe function."""
        import asyncio
        import threading

        tsfn_data = _tsfn_store.get(tsfn_id)
        if not tsfn_data:
            return napi_status.napi_invalid_arg

        # Check closing state
        if tsfn_data.get("is_closing", False) or tsfn_data["closed"]:
            if tsfn_data["thread_count"] == 0:
                return napi_status.napi_invalid_arg
            else:
                tsfn_data["thread_count"] -= 1
                return napi_status.napi_closing

        env_id = tsfn_data["env_id"]
        func = tsfn_data["func"]
        context = tsfn_data["context"]
        call_js_cb = tsfn_data["call_js_cb"]
        loop = tsfn_data["loop"]

        def dispatch():
            """Execute the callback on the main thread."""
            env_obj = get_env(env_id)
            if not env_obj:
                return

            # Open a scope for this callback
            scope = ctx.open_scope(env_obj)
            try:
                if call_js_cb:
                    # Get the function from our persistent reference
                    func_value = tsfn_data.get("func_value")
                    func_ref = tsfn_data.get("func_ref")

                    if func_value is not None and func_ref is not None:
                        # Store the callback in the handle store at a high index
                        # that won't get erased by scope management
                        persistent_handle = 0x10000000 + func_ref
                        ctx._handle_store._values.extend([None] * max(0, persistent_handle + 1 - len(ctx._handle_store._values)))
                        ctx._handle_store._values[persistent_handle] = func_value
                        js_callback = persistent_handle
                    elif func_value is not None:
                        js_callback = ctx.add_value(func_value)
                    else:
                        js_callback = 0

                    # Track if native callback triggers any NAPI value creation
                    initial_value_count = len(ctx._handle_store._values)

                    # Call the native JS callback: (env, js_callback, context, data)
                    try:
                        call_js_cb(env_id, js_callback, context, data)
                    except Exception as exc:
                        import traceback
                        print(f"[napi-python] call_js_cb exception in TSFN dispatch: {exc}")
                        traceback.print_exc()
                        # Native callback may fail, continue with workaround

                    # Check if native callback created any new values
                    new_value_count = len(ctx._handle_store._values)
                    native_created_value = new_value_count > initial_value_count

                    # If native callback didn't call back into NAPI (common when not in Node.js),
                    # call the Python callback directly with data pointer as an External
                    if not native_created_value and func_value is not None and callable(func_value):
                        # Create an External value wrapping the native data pointer
                        # This allows advanced users to access the raw data if needed
                        try:
                            external = ctx.create_external(data)
                            func_value(external)
                        except Exception:
                            pass  # Callback exceptions are silently ignored
            except Exception:
                pass  # TSFN dispatch errors are silently ignored
            finally:
                ctx.close_scope(env_obj, scope)

        # Check if we're on the main thread
        main_thread_id = getattr(ctx, "_main_thread_id", None)
        current_thread_id = threading.current_thread().ident

        if main_thread_id is None:
            # First call - assume this is the main thread
            ctx._main_thread_id = current_thread_id
            main_thread_id = current_thread_id

        if is_blocking == 1:
            # Blocking mode - always dispatch immediately
            dispatch()
        elif current_thread_id == main_thread_id:
            # We're on the main thread - dispatch immediately
            dispatch()
        else:
            # We're on a background thread with non-blocking mode
            # For webcodecs and similar libs, we still need to dispatch
            # immediately because the asyncio event loop won't process
            # queued callbacks until awaited
            #
            # TODO: Consider using a proper queue and async processing
            # For now, dispatch directly (native code handles thread safety)
            dispatch()

        return napi_status.napi_ok

    @FuncAcquireTsfn
    def acquire_tsfn(tsfn_id):
        """Acquire a threadsafe function (increment thread count)."""
        tsfn_data = _tsfn_store.get(tsfn_id)
        if not tsfn_data:
            return napi_status.napi_invalid_arg

        # Check if closing
        if tsfn_data.get("is_closing", False):
            return napi_status.napi_closing

        tsfn_data["thread_count"] += 1
        return napi_status.napi_ok

    @FuncReleaseTsfn
    def release_tsfn(tsfn_id, mode):
        """Release a threadsafe function."""
        tsfn_data = _tsfn_store.get(tsfn_id)
        if not tsfn_data:
            return napi_status.napi_ok

        # Check thread count
        if tsfn_data["thread_count"] == 0:
            return napi_status.napi_invalid_arg

        tsfn_data["thread_count"] -= 1

        # napi_tsfn_abort = 1
        if tsfn_data["thread_count"] == 0 or mode == 1:
            is_closing = tsfn_data.get("is_closing", False)
            if not is_closing:
                # Set closing state
                is_closing_value = 1 if mode == 1 else 0
                tsfn_data["is_closing"] = bool(is_closing_value)

                # Mark as closed
                tsfn_data["closed"] = True

                # Call finalize callback if provided
                finalize_cb = tsfn_data.get("finalize_cb")
                finalize_data = tsfn_data.get("finalize_data")
                context = tsfn_data.get("context")

                if finalize_cb:
                    try:
                        FinalizeCb = CFUNCTYPE(None, c_void_p, c_void_p, c_void_p)
                        finalize_func = ctypes.cast(finalize_cb, FinalizeCb)
                        env_id = tsfn_data["env_id"]
                        finalize_func(env_id, finalize_data, context)
                    except Exception as e:
                        print(f"[napi-python] TSFN finalize error: {e}")

                # Remove from store
                _tsfn_store.pop(tsfn_id, None)

        return napi_status.napi_ok

    # =============================================================================
    # ArrayBuffer Functions
    # =============================================================================

    from ._values.arraybuffer import (
        ArrayBuffer,
        TypedArray,
        DataView,
        is_arraybuffer as _is_arraybuffer,
        is_typedarray as _is_typedarray,
        is_dataview as _is_dataview,
    )
    from ._napi.types import napi_typedarray_type

    @FuncCreateArraybuffer
    def create_arraybuffer(env, byte_length, data, result):
        try:
            arraybuffer = ArrayBuffer(byte_length)
            if data:
                data[0] = arraybuffer.data_ptr
            handle = ctx.add_value(arraybuffer)
            result[0] = handle
            return napi_status.napi_ok
        except Exception:
            return napi_status.napi_generic_failure

    @FuncGetArraybufferInfo
    def get_arraybuffer_info(env, arraybuffer_handle, data, byte_length):
        try:
            py_val = ctx.python_value_from_napi(arraybuffer_handle)
            if not _is_arraybuffer(py_val):
                return napi_status.napi_invalid_arg
            if data:
                data[0] = py_val.data_ptr
            if byte_length:
                byte_length[0] = py_val.byte_length
            return napi_status.napi_ok
        except Exception:
            return napi_status.napi_generic_failure

    @FuncIsDetachedArraybuffer
    def is_detached_arraybuffer(env, arraybuffer_handle, result):
        try:
            py_val = ctx.python_value_from_napi(arraybuffer_handle)
            if _is_arraybuffer(py_val):
                result[0] = py_val.detached
            else:
                result[0] = False
            return napi_status.napi_ok
        except Exception:
            return napi_status.napi_generic_failure

    @FuncDetachArraybuffer
    def detach_arraybuffer(env, arraybuffer_handle):
        try:
            py_val = ctx.python_value_from_napi(arraybuffer_handle)
            if not _is_arraybuffer(py_val):
                return napi_status.napi_arraybuffer_expected
            py_val.detach()
            return napi_status.napi_ok
        except Exception:
            return napi_status.napi_generic_failure

    @FuncIsArraybuffer
    def is_arraybuffer(env, value, result):
        try:
            py_val = ctx.python_value_from_napi(value)
            result[0] = _is_arraybuffer(py_val)
            return napi_status.napi_ok
        except Exception:
            return napi_status.napi_generic_failure

    # =============================================================================
    # TypedArray Functions
    # =============================================================================

    @FuncCreateTypedarray
    def create_typedarray(
        env, array_type, length, arraybuffer_handle, byte_offset, result
    ):
        try:
            buffer = ctx.python_value_from_napi(arraybuffer_handle)
            if not _is_arraybuffer(buffer):
                return napi_status.napi_invalid_arg
            typedarray = TypedArray(array_type, buffer, byte_offset, length)
            handle = ctx.add_value(typedarray)
            result[0] = handle
            return napi_status.napi_ok
        except Exception:
            return napi_status.napi_generic_failure

    # =============================================================================
    # DataView Functions
    # =============================================================================

    @FuncCreateDataview
    def create_dataview(env, byte_length, arraybuffer_handle, byte_offset, result):
        try:
            buffer = ctx.python_value_from_napi(arraybuffer_handle)
            if not _is_arraybuffer(buffer):
                return napi_status.napi_invalid_arg
            dataview = DataView(buffer, byte_offset, byte_length)
            handle = ctx.add_value(dataview)
            result[0] = handle
            return napi_status.napi_ok
        except Exception:
            return napi_status.napi_generic_failure

    @FuncGetDataviewInfo
    def get_dataview_info(
        env, dataview_handle, byte_length, data, arraybuffer, byte_offset
    ):
        try:
            py_val = ctx.python_value_from_napi(dataview_handle)
            if not _is_dataview(py_val):
                return napi_status.napi_invalid_arg
            if byte_length:
                byte_length[0] = py_val.byte_length
            if data:
                data[0] = py_val.data_ptr
            if arraybuffer:
                arraybuffer[0] = ctx.add_value(py_val.buffer)
            if byte_offset:
                byte_offset[0] = py_val.byte_offset
            return napi_status.napi_ok
        except Exception:
            return napi_status.napi_generic_failure

    @FuncIsDataview
    def is_dataview(env, value, result):
        try:
            py_val = ctx.python_value_from_napi(value)
            result[0] = _is_dataview(py_val)
            return napi_status.napi_ok
        except Exception:
            return napi_status.napi_generic_failure

    # =============================================================================
    # Buffer Functions
    # =============================================================================

    @FuncCreateBuffer
    def create_buffer(env, size, data, result):
        try:
            arraybuffer = ArrayBuffer(size)
            buffer = TypedArray(
                napi_typedarray_type.napi_uint8_array, arraybuffer, 0, size
            )
            if data:
                data[0] = arraybuffer.data_ptr
            handle = ctx.add_value(buffer)
            result[0] = handle
            return napi_status.napi_ok
        except Exception:
            return napi_status.napi_generic_failure

    @FuncCreateBufferCopy
    def create_buffer_copy(env, length, source_data, result_data, result):
        from ctypes import memmove

        try:
            arraybuffer = ArrayBuffer(length)
            if source_data and length > 0:
                memmove(arraybuffer.data_ptr, source_data, length)
            buffer = TypedArray(
                napi_typedarray_type.napi_uint8_array, arraybuffer, 0, length
            )
            if result_data:
                result_data[0] = arraybuffer.data_ptr
            handle = ctx.add_value(buffer)
            result[0] = handle
            return napi_status.napi_ok
        except Exception:
            return napi_status.napi_generic_failure

    @FuncGetBufferInfo
    def get_buffer_info(env, buffer_handle, data, length):
        from ctypes import c_uint8, addressof

        try:
            py_val = ctx.python_value_from_napi(buffer_handle)
            if _is_typedarray(py_val):
                if data:
                    data[0] = py_val.data_ptr
                if length:
                    length[0] = py_val.length
                return napi_status.napi_ok
            if _is_dataview(py_val):
                if data:
                    data[0] = py_val.data_ptr
                if length:
                    length[0] = py_val.byte_length
                return napi_status.napi_ok
            # Handle Python bytes/bytearray
            if isinstance(py_val, (bytes, bytearray)):
                # Need to convert to a stable buffer
                # Store it as an ArrayBuffer for this call
                buf = ArrayBuffer.from_data(py_val)
                # Store reference to prevent GC
                ctx._temp_buffers = getattr(ctx, "_temp_buffers", [])
                ctx._temp_buffers.append(buf)
                if data:
                    data[0] = buf.data_ptr
                if length:
                    length[0] = len(py_val)
                return napi_status.napi_ok
            return napi_status.napi_invalid_arg
        except Exception:
            return napi_status.napi_generic_failure

    @FuncIsBuffer
    def is_buffer(env, value, result):
        try:
            py_val = ctx.python_value_from_napi(value)
            result[0] = isinstance(py_val, (bytes, bytearray, TypedArray))
            return napi_status.napi_ok
        except Exception:
            return napi_status.napi_generic_failure

    # =============================================================================
    # External Functions
    # =============================================================================

    @FuncCreateExternal
    def create_external(env, data_ptr, finalize_cb, finalize_hint, result):
        try:
            external = ctx.create_external(data_ptr)
            handle = ctx.add_value(external)
            result[0] = handle
            return napi_status.napi_ok
        except Exception:
            return napi_status.napi_generic_failure

    @FuncGetValueExternal
    def get_value_external(env, value, result):
        try:
            py_val = ctx.python_value_from_napi(value)
            if ctx.is_external(py_val):
                result[0] = ctx.get_external_value(py_val)
                return napi_status.napi_ok
            return napi_status.napi_invalid_arg
        except Exception:
            return napi_status.napi_generic_failure

    # =============================================================================
    # Additional Error Functions
    # =============================================================================

    @FuncThrowTypeError
    def throw_type_error(env, code, msg):
        env_obj = get_env(env)
        if env_obj:
            msg_str = msg.decode("utf-8") if msg else ""
            env_obj.last_exception = TypeError(msg_str)
        return napi_status.napi_ok

    @FuncThrowRangeError
    def throw_range_error(env, code, msg):
        env_obj = get_env(env)
        if env_obj:
            msg_str = msg.decode("utf-8") if msg else ""
            env_obj.last_exception = ValueError(msg_str)
        return napi_status.napi_ok

    @FuncCreateTypeError
    def create_type_error(env, code, msg_handle, result):
        try:
            msg = ctx.python_value_from_napi(msg_handle)
            if not isinstance(msg, str):
                return napi_status.napi_string_expected
            error = TypeError(msg)
            handle = ctx.add_value(error)
            result[0] = handle
            return napi_status.napi_ok
        except Exception:
            return napi_status.napi_generic_failure

    @FuncCreateRangeError
    def create_range_error(env, code, msg_handle, result):
        try:
            msg = ctx.python_value_from_napi(msg_handle)
            if not isinstance(msg, str):
                return napi_status.napi_string_expected
            error = ValueError(msg)
            handle = ctx.add_value(error)
            result[0] = handle
            return napi_status.napi_ok
        except Exception:
            return napi_status.napi_generic_failure

    # =============================================================================
    # Instance Creation
    # =============================================================================

    @FuncNewInstance
    def new_instance(env_id, constructor_handle, argc, argv, result):
        """Create a new instance of a class."""
        env_obj = get_env(env_id)
        if not env_obj:
            return napi_status.napi_invalid_arg

        try:
            # Get the constructor class
            constructor = ctx.python_value_from_napi(constructor_handle)

            if constructor is None:
                if result:
                    result[0] = Constant.UNDEFINED
                return napi_status.napi_invalid_arg

            # Get arguments
            args = []
            for i in range(argc):
                if argv:
                    args.append(ctx.python_value_from_napi(argv[i]))
                else:
                    args.append(None)

            # Create the instance by calling the constructor
            if callable(constructor):
                instance = constructor(*args)
            else:
                if result:
                    result[0] = Constant.UNDEFINED
                return napi_status.napi_function_expected

            # Store the instance and return handle
            if result:
                result[0] = ctx.add_value(instance)
            return napi_status.napi_ok

        except Exception as e:
            if result:
                result[0] = Constant.UNDEFINED
            return napi_status.napi_generic_failure

    @FuncFatalException
    def fatal_exception(env_id, err):
        """Handle a fatal exception - just log it for now."""
        # TODO: Proper fatal exception handling
        return napi_status.napi_ok

    @FuncGetNewTarget
    def get_new_target(env_id, cbinfo, result):
        """Get the new.target value from callback info."""
        env_obj = get_env(env_id)
        if not env_obj:
            return napi_status.napi_invalid_arg
        if not cbinfo:
            return napi_status.napi_invalid_arg
        if not result:
            return napi_status.napi_invalid_arg

        try:
            cb_info = ctx.get_callback_info(cbinfo)
            thiz = cb_info.thiz
            fn = cb_info.fn

            # Logic from emnapi: check if this is a constructor call
            # thiz == null || thiz.constructor == null ? 0
            #   : thiz instanceof fn ? thiz.constructor : 0
            if thiz is None:
                result[0] = Constant.UNDEFINED
            elif not hasattr(thiz, '__class__'):
                result[0] = Constant.UNDEFINED
            else:
                # Check if thiz is an instance of the function/class
                # In Python, fn might be the class itself or a method
                thiz_type = type(thiz)

                # If fn is callable and thiz is an instance of something fn created
                if fn is not None and isinstance(thiz, type(thiz)):
                    # Return the constructor (type of thiz)
                    result[0] = ctx.add_value(thiz_type)
                else:
                    result[0] = Constant.UNDEFINED

            return napi_status.napi_ok
        except Exception:
            if result:
                result[0] = Constant.UNDEFINED
            return napi_status.napi_ok

    @FuncHasOwnProperty
    def has_own_property(env_id, object_handle, key_handle, result):
        """Check if object has own property."""
        try:
            py_obj = ctx.python_value_from_napi(object_handle)
            py_key = ctx.python_value_from_napi(key_handle)
            if isinstance(py_obj, dict):
                if result:
                    result[0] = py_key in py_obj
            else:
                if result:
                    result[0] = hasattr(py_obj, str(py_key))
            return napi_status.napi_ok
        except Exception:
            if result:
                result[0] = False
            return napi_status.napi_ok

    @FuncGetAllPropertyNames
    def get_all_property_names(
        env_id, object_handle, key_mode, key_filter, key_conversion, result
    ):
        """Get all property names of an object."""
        try:
            py_obj = ctx.python_value_from_napi(object_handle)
            if isinstance(py_obj, dict):
                names = list(py_obj.keys())
            else:
                names = dir(py_obj)
            if result:
                result[0] = ctx.add_value(names)
            return napi_status.napi_ok
        except Exception:
            if result:
                result[0] = ctx.add_value([])
            return napi_status.napi_ok

    @FuncGetPropertyNames
    def get_property_names(env_id, object_handle, result):
        """Get property names of an object."""
        try:
            py_obj = ctx.python_value_from_napi(object_handle)
            if isinstance(py_obj, dict):
                names = list(py_obj.keys())
            else:
                names = [n for n in dir(py_obj) if not n.startswith("_")]
            if result:
                result[0] = ctx.add_value(names)
            return napi_status.napi_ok
        except Exception:
            if result:
                result[0] = ctx.add_value([])
            return napi_status.napi_ok

    # =============================================================================
    # Instance Data
    # =============================================================================

    @FuncSetInstanceData
    def set_instance_data(env_id, data, finalize_cb, finalize_hint):
        """Set instance data for environment."""
        env_obj = get_env(env_id)
        if not env_obj:
            return napi_status.napi_invalid_arg
        env_obj.set_instance_data(data, finalize_cb, finalize_hint)
        return napi_status.napi_ok

    @FuncGetInstanceData
    def get_instance_data(env_id, result):
        """Get instance data for environment."""
        env_obj = get_env(env_id)
        if not env_obj:
            if result:
                result[0] = 0
            return napi_status.napi_invalid_arg
        data = env_obj.get_instance_data()
        if result:
            result[0] = data if data else 0
        return napi_status.napi_ok

    # Keep references to prevent GC
    _callback_refs.extend(
        [
            get_version,
            get_undefined,
            get_null,
            get_global,
            get_boolean,
            create_int32,
            create_uint32,
            create_int64,
            create_double,
            create_string_utf8,
            get_value_bool,
            get_value_int32,
            get_value_uint32,
            get_value_int64,
            get_value_double,
            get_value_string_utf8,
            typeof_,
            is_array,
            is_typedarray,
            is_error,
            create_object,
            create_array,
            get_array_length,
            get_element,
            set_element,
            get_property,
            set_property,
            get_named_property,
            set_named_property,
            get_cb_info,
            create_function,
            call_function,
            define_class,
            create_reference,
            delete_reference,
            get_reference_value,
            reference_ref,
            reference_unref,
            throw_,
            throw_error,
            create_error,
            is_exception_pending,
            get_and_clear_last_exception,
            open_handle_scope,
            close_handle_scope,
            coerce_to_string,
            get_typedarray_info,
            create_promise,
            resolve_deferred,
            reject_deferred,
            is_promise,
            create_tsfn,
            call_tsfn,
            acquire_tsfn,
            release_tsfn,
            wrap,
            unwrap,
            define_class_impl,
            create_arraybuffer,
            get_arraybuffer_info,
            is_detached_arraybuffer,
            detach_arraybuffer,
            is_arraybuffer,
            create_typedarray,
            create_dataview,
            get_dataview_info,
            is_dataview,
            create_buffer,
            create_buffer_copy,
            get_buffer_info,
            is_buffer,
            create_external,
            get_value_external,
            throw_type_error,
            throw_range_error,
            create_type_error,
            create_range_error,
            new_instance,
            fatal_exception,
            get_new_target,
            has_own_property,
            get_all_property_names,
            get_property_names,
            set_instance_data,
            get_instance_data,
        ]
    )

    return NapiPythonFunctions(
        get_version=get_version,
        get_undefined=get_undefined,
        get_null=get_null,
        get_global=get_global,
        get_boolean=get_boolean,
        create_int32=create_int32,
        create_uint32=create_uint32,
        create_int64=create_int64,
        create_double=create_double,
        create_string_utf8=create_string_utf8,
        get_value_bool=get_value_bool,
        get_value_int32=get_value_int32,
        get_value_uint32=get_value_uint32,
        get_value_int64=get_value_int64,
        get_value_double=get_value_double,
        get_value_string_utf8=get_value_string_utf8,
        typeof_=typeof_,
        is_array=is_array,
        is_typedarray=is_typedarray,
        is_error=is_error,
        create_object=create_object,
        create_array=create_array,
        get_array_length=get_array_length,
        get_element=get_element,
        set_element=set_element,
        get_property=get_property,
        set_property=set_property,
        get_named_property=get_named_property,
        set_named_property=set_named_property,
        get_cb_info=get_cb_info,
        create_function=create_function,
        call_function=call_function,
        define_class=define_class,
        create_reference=create_reference,
        delete_reference=delete_reference,
        get_reference_value=get_reference_value,
        reference_ref=reference_ref,
        reference_unref=reference_unref,
        throw_=throw_,
        throw_error=throw_error,
        create_error=create_error,
        is_exception_pending=is_exception_pending,
        get_and_clear_last_exception=get_and_clear_last_exception,
        open_handle_scope=open_handle_scope,
        close_handle_scope=close_handle_scope,
        coerce_to_string=coerce_to_string,
        get_typedarray_info=get_typedarray_info,
        create_promise=create_promise,
        resolve_deferred=resolve_deferred,
        reject_deferred=reject_deferred,
        is_promise=is_promise,
        create_tsfn=create_tsfn,
        call_tsfn=call_tsfn,
        acquire_tsfn=acquire_tsfn,
        release_tsfn=release_tsfn,
        wrap=wrap,
        unwrap=unwrap,
        define_class_impl=define_class_impl,
        create_arraybuffer=create_arraybuffer,
        get_arraybuffer_info=get_arraybuffer_info,
        is_detached_arraybuffer=is_detached_arraybuffer,
        detach_arraybuffer=detach_arraybuffer,
        is_arraybuffer=is_arraybuffer,
        create_typedarray=create_typedarray,
        create_dataview=create_dataview,
        get_dataview_info=get_dataview_info,
        is_dataview=is_dataview,
        create_buffer=create_buffer,
        create_buffer_copy=create_buffer_copy,
        get_buffer_info=get_buffer_info,
        is_buffer=is_buffer,
        create_external=create_external,
        get_value_external=get_value_external,
        throw_type_error=throw_type_error,
        throw_range_error=throw_range_error,
        create_type_error=create_type_error,
        create_range_error=create_range_error,
        new_instance=new_instance,
        fatal_exception=fatal_exception,
        get_new_target=get_new_target,
        has_own_property=has_own_property,
        get_all_property_names=get_all_property_names,
        get_property_names=get_property_names,
        set_instance_data=set_instance_data,
        get_instance_data=get_instance_data,
    )


class LibcLoadedFunction:
    """Wrapper for a function pointer from dlsym to provide CDLL function-like interface."""

    def __init__(self, ptr: int):
        self._ptr = ptr
        self._argtypes = None
        self._restype = None
        self._func = None

    @property
    def argtypes(self):
        return self._argtypes

    @argtypes.setter
    def argtypes(self, value):
        self._argtypes = value
        self._func = None  # Reset cached function

    @property
    def restype(self):
        return self._restype

    @restype.setter
    def restype(self, value):
        self._restype = value
        self._func = None  # Reset cached function

    def __call__(self, *args):
        if self._func is None:
            # Create CFUNCTYPE from argtypes/restype
            if self._argtypes is None:
                func_type = CFUNCTYPE(self._restype or c_void_p)
            else:
                func_type = CFUNCTYPE(self._restype or c_void_p, *self._argtypes)
            self._func = func_type(self._ptr)
        return self._func(*args)


class LibcLoadedLibrary:
    """Wrapper for libraries loaded via libc.dlopen to provide CDLL-like interface."""

    def __init__(self, handle: int, path: str):
        self._handle = handle
        self._path = path
        self._libc = CDLL("libc.dylib")
        self._libc.dlsym.argtypes = [c_void_p, c_char_p]
        self._libc.dlsym.restype = c_void_p
        self._symbols = {}

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        if name in self._symbols:
            return self._symbols[name]
        # Look up symbol
        sym = self._libc.dlsym(self._handle, name.encode())
        if not sym:
            raise AttributeError(f"Symbol not found: {name}")
        func = LibcLoadedFunction(sym)
        self._symbols[name] = func
        return func


def _load_with_libc_dlopen(path: str):
    """
    Load a library using libc.dlopen directly.

    This bypasses Python's CDLL which can have issues with "flat namespace"
    symbol resolution on macOS.
    """
    libc = CDLL("libc.dylib")
    libc.dlopen.argtypes = [c_char_p, c_int]
    libc.dlopen.restype = c_void_p
    libc.dlerror.restype = c_char_p

    RTLD_LAZY = 0x1
    handle = libc.dlopen(path.encode(), RTLD_LAZY)

    if not handle:
        err = libc.dlerror()
        raise OSError(f"dlopen failed: {err.decode() if err else 'unknown error'}")

    return LibcLoadedLibrary(handle, path)


def load_addon(path: str) -> ModuleExports:
    """
    Load a Node-API native addon.
    """
    path = Path(path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"Addon not found: {path}")

    # Initialize the shim with our Python implementations
    shim = _init_shim()

    # Get context and create environment
    ctx = get_default_context()
    env = ctx.create_env(str(path), NODE_API_DEFAULT_MODULE_API_VERSION)

    # Load the addon - NAPI symbols will be resolved from our shim (loaded with RTLD_GLOBAL)
    try:
        lib = CDLL(str(path))
    except OSError as e:
        # On macOS, Python's CDLL can fail with "flat namespace" errors even when
        # raw dlopen works. Try using libc.dlopen directly as a fallback.
        if "flat namespace" in str(e):
            try:
                lib = _load_with_libc_dlopen(str(path))
            except Exception as e2:
                raise NapiError(
                    napi_status.napi_generic_failure, f"Failed to load addon: {e2}"
                )
        else:
            raise NapiError(
                napi_status.napi_generic_failure, f"Failed to load addon: {e}"
            )

    # Find and call the init function
    try:
        init_fn = lib.napi_register_module_v1
    except AttributeError:
        raise NapiError(
            napi_status.napi_generic_failure,
            "Module does not export napi_register_module_v1",
        )

    init_fn.argtypes = [c_void_p, c_void_p]
    init_fn.restype = c_void_p

    # Create exports object
    exports: Dict[str, Any] = {}

    # Open scope for initialization
    scope = ctx.open_scope(env)

    try:
        exports_handle = ctx.add_value(exports)

        print(f"[napi-python] Calling init function...")
        result = init_fn(env.id, exports_handle)
        print(f"[napi-python] Init returned: {result}")

        # Get updated exports
        if result:
            exports = ctx.python_value_from_napi(result) or exports

    finally:
        ctx.close_scope(env, scope)

    return ModuleExports(exports, ctx, env)
