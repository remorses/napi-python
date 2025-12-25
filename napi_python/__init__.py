"""
napi-python: Load Node-API native addons in Python.

Usage:
    from napi_python import load_addon

    addon = load_addon("path/to/addon.node")
    result = addon.some_function(arg1, arg2)
"""

from ._runtime import Context, create_context, get_default_context, Env
from ._napi import napi_status, napi_valuetype

__version__ = "0.1.0"

__all__ = [
    "load_addon",
    "Context",
    "create_context",
    "get_default_context",
    "Env",
    "napi_status",
    "napi_valuetype",
]


def load_addon(path: str):
    """
    Load a Node-API native addon.

    Args:
        path: Path to the .node file

    Returns:
        A module-like object with the addon's exports
    """
    from ._loader import load_addon as _load

    return _load(path)
