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
        func_name = name.decode("utf-8") if name else "anonymous"

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

    @FuncDefineClass
    def define_class(env, name, length, constructor, data, prop_count, props, result):
        # TODO: Implement
        result[0] = Constant.UNDEFINED
        return napi_status.napi_ok

    @FuncCreateReference
    def create_reference(env, value, initial_refcount, result):
        # TODO: Implement
        result[0] = 0
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
