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

from ._runtime import Context, Env, get_default_context
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
    c_int, c_void_p, c_void_p, c_char_p, c_size_t, POINTER(c_size_t)
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
        ("release_tsfn", FuncReleaseTsfn),
        # Class/wrap functions
        ("wrap", FuncWrap),
        ("unwrap", FuncUnwrap),
        ("define_class_impl", FuncDefineClassImpl),
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
        result[0] = int(py_val) & 0xFFFFFFFF
        return napi_status.napi_ok

    @FuncGetValueUint32
    def get_value_uint32(env, value, result):
        py_val = ctx.python_value_from_napi(value)
        result[0] = int(py_val) & 0xFFFFFFFF
        return napi_status.napi_ok

    @FuncGetValueInt64
    def get_value_int64(env, value, result):
        py_val = ctx.python_value_from_napi(value)
        result[0] = int(py_val)
        return napi_status.napi_ok

    @FuncGetValueDouble
    def get_value_double(env, value, result):
        py_val = ctx.python_value_from_napi(value)
        result[0] = float(py_val)
        return napi_status.napi_ok

    @FuncGetValueStringUtf8
    def get_value_string_utf8(env, value, buf, bufsize, result):
        py_val = ctx.python_value_from_napi(value)
        if not isinstance(py_val, str):
            return napi_status.napi_string_expected
        encoded = py_val.encode("utf-8")
        if result:
            result[0] = len(encoded)
        if buf and bufsize > 0:
            copy_len = min(len(encoded), bufsize - 1)
            ctypes.memmove(buf, encoded, copy_len)
            buf[copy_len] = 0
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
        py_val = ctx.python_value_from_napi(value)
        # Treat bytes and bytearray as TypedArray (Uint8Array equivalent)
        result[0] = isinstance(py_val, (bytes, bytearray, memoryview))
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
            result[0] = ctx.add_value(py_obj.get(key))
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
        """Call a JavaScript function."""
        env_obj = get_env(env_id)
        if not env_obj:
            if result:
                result[0] = Constant.UNDEFINED
            return napi_status.napi_invalid_arg

        # Get the function
        py_func = ctx.python_value_from_napi(func)
        if not callable(py_func):
            if result:
                result[0] = Constant.UNDEFINED
            return napi_status.napi_function_expected

        # Get receiver
        py_recv = ctx.python_value_from_napi(recv) if recv else None

        # Get arguments
        args = []
        for i in range(argc):
            arg_handle = argv[i] if argv else Constant.UNDEFINED
            args.append(ctx.python_value_from_napi(arg_handle))

        # Call the function
        try:
            ret = py_func(*args)
            if result:
                result[0] = ctx.add_value(ret)
        except Exception as e:
            env_obj.last_exception = e
            if result:
                result[0] = Constant.UNDEFINED
            return napi_status.napi_pending_exception

        return napi_status.napi_ok

    # Storage for wrapped native objects
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
    def create_reference(env, value, initial_refcount, result):
        # Store the value to prevent GC
        ref_id = _wrap_counter[0]
        _wrap_counter[0] += 1
        py_value = ctx.python_value_from_napi(value)
        _wrap_store[ref_id] = {"value": py_value, "refcount": initial_refcount}
        if result:
            result[0] = ref_id
        return napi_status.napi_ok

    @FuncDeleteReference
    def delete_reference(env, ref):
        return napi_status.napi_ok

    @FuncGetReferenceValue
    def get_reference_value(env, ref, result):
        result[0] = Constant.UNDEFINED
        return napi_status.napi_ok

    @FuncThrow
    def throw_(env, error):
        return napi_status.napi_ok

    @FuncThrowError
    def throw_error(env, code, msg):
        return napi_status.napi_ok

    @FuncCreateError
    def create_error(env, code, msg, result):
        result[0] = Constant.UNDEFINED
        return napi_status.napi_ok

    @FuncIsExceptionPending
    def is_exception_pending(env, result):
        result[0] = False
        return napi_status.napi_ok

    @FuncGetAndClearLastException
    def get_and_clear_last_exception(env, result):
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
        py_val = ctx.python_value_from_napi(typedarray)

        if isinstance(py_val, (bytes, bytearray)):
            # Treat as Uint8Array
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
            return napi_status.napi_invalid_arg

        py_obj = ctx.python_value_from_napi(js_object)
        if py_obj is None:
            return napi_status.napi_invalid_arg

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

        tsfn_data = {
            "id": tsfn_id,
            "env_id": env_id,
            "func": func,
            "context": context,
            "call_js_cb": js_cb,
            "loop": loop,
            "queue": queue.Queue(maxsize=max_queue_size if max_queue_size > 0 else 0),
            "thread_count": initial_thread_count,
            "closed": False,
            "finalize_data": thread_finalize_data,
            "finalize_cb": thread_finalize_cb,
        }

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

        tsfn_data = _tsfn_store.get(tsfn_id)
        if not tsfn_data or tsfn_data["closed"]:
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
                    # Call the JS callback: (env, js_callback, context, data)
                    call_js_cb(env_id, func, context, data)
            except Exception as e:
                print(f"[napi-python] TSFN callback error: {e}")
            finally:
                ctx.close_scope(env_obj, scope)

        # Dispatch to the event loop
        try:
            loop.call_soon_threadsafe(dispatch)
        except RuntimeError:
            # Loop might be closed, try to run synchronously
            dispatch()

        return napi_status.napi_ok

    @FuncReleaseTsfn
    def release_tsfn(tsfn_id, mode):
        """Release a threadsafe function."""
        tsfn_data = _tsfn_store.get(tsfn_id)
        if not tsfn_data:
            return napi_status.napi_ok

        tsfn_data["thread_count"] -= 1

        if tsfn_data["thread_count"] <= 0 or mode == 1:  # napi_tsfn_abort
            tsfn_data["closed"] = True
            # Could call finalize callback here
            _tsfn_store.pop(tsfn_id, None)

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
            release_tsfn,
            wrap,
            unwrap,
            define_class_impl,
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
        release_tsfn=release_tsfn,
        wrap=wrap,
        unwrap=unwrap,
        define_class_impl=define_class_impl,
    )


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
        raise NapiError(napi_status.napi_generic_failure, f"Failed to load addon: {e}")

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
