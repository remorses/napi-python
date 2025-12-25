"""
ArrayBuffer and TypedArray implementations.

These provide the underlying data structures for binary data in NAPI.
"""

from ctypes import (
    c_uint8,
    c_int8,
    c_uint16,
    c_int16,
    c_uint32,
    c_int32,
    c_float,
    c_double,
    c_int64,
    c_uint64,
    addressof,
    sizeof,
    memmove,
    POINTER,
    cast,
    c_char,
)
from typing import Optional, Union, Type, Any
import struct

from .._napi.types import napi_typedarray_type


class ArrayBuffer:
    """
    Python implementation of JavaScript ArrayBuffer.

    Uses a ctypes array for the underlying storage, which provides:
    - Stable memory address (won't be moved by GC)
    - Direct pointer access for native code
    """

    def __init__(self, byte_length: int):
        """Create an ArrayBuffer of the specified size."""
        self._byte_length = byte_length
        # Use ctypes array for stable memory location
        self._buffer = (c_uint8 * byte_length)()
        self._detached = False

    @classmethod
    def from_data(cls, data: bytes) -> "ArrayBuffer":
        """Create an ArrayBuffer from existing bytes."""
        buf = cls(len(data))
        memmove(buf._buffer, data, len(data))
        return buf

    @property
    def byte_length(self) -> int:
        """Get the size in bytes."""
        if self._detached:
            return 0
        return self._byte_length

    @property
    def data_ptr(self) -> int:
        """Get the raw pointer to the data."""
        if self._detached or self._byte_length == 0:
            return 0
        return addressof(self._buffer)

    @property
    def detached(self) -> bool:
        """Check if the buffer has been detached."""
        return self._detached

    def detach(self) -> None:
        """Detach the ArrayBuffer (make it unusable)."""
        self._detached = True
        self._buffer = (c_uint8 * 0)()

    def to_bytes(self) -> bytes:
        """Convert to Python bytes."""
        if self._detached:
            return b""
        return bytes(self._buffer)

    def __len__(self) -> int:
        return self.byte_length

    def __repr__(self) -> str:
        return f"ArrayBuffer({self._byte_length})"


# TypedArray element info: (ctypes_type, element_size)
TYPED_ARRAY_INFO = {
    napi_typedarray_type.napi_int8_array: (c_int8, 1),
    napi_typedarray_type.napi_uint8_array: (c_uint8, 1),
    napi_typedarray_type.napi_uint8_clamped_array: (c_uint8, 1),
    napi_typedarray_type.napi_int16_array: (c_int16, 2),
    napi_typedarray_type.napi_uint16_array: (c_uint16, 2),
    napi_typedarray_type.napi_int32_array: (c_int32, 4),
    napi_typedarray_type.napi_uint32_array: (c_uint32, 4),
    napi_typedarray_type.napi_float32_array: (c_float, 4),
    napi_typedarray_type.napi_float64_array: (c_double, 8),
    napi_typedarray_type.napi_bigint64_array: (c_int64, 8),
    napi_typedarray_type.napi_biguint64_array: (c_uint64, 8),
}

# Map type enum to name for error messages
TYPED_ARRAY_NAMES = {
    napi_typedarray_type.napi_int8_array: "Int8Array",
    napi_typedarray_type.napi_uint8_array: "Uint8Array",
    napi_typedarray_type.napi_uint8_clamped_array: "Uint8ClampedArray",
    napi_typedarray_type.napi_int16_array: "Int16Array",
    napi_typedarray_type.napi_uint16_array: "Uint16Array",
    napi_typedarray_type.napi_int32_array: "Int32Array",
    napi_typedarray_type.napi_uint32_array: "Uint32Array",
    napi_typedarray_type.napi_float32_array: "Float32Array",
    napi_typedarray_type.napi_float64_array: "Float64Array",
    napi_typedarray_type.napi_bigint64_array: "BigInt64Array",
    napi_typedarray_type.napi_biguint64_array: "BigUint64Array",
}


class TypedArray:
    """
    Python implementation of JavaScript TypedArray.

    Provides a typed view into an ArrayBuffer.
    """

    def __init__(
        self,
        array_type: int,
        buffer: ArrayBuffer,
        byte_offset: int = 0,
        length: Optional[int] = None,
    ):
        """
        Create a TypedArray view.

        Args:
            array_type: napi_typedarray_type value
            buffer: The underlying ArrayBuffer
            byte_offset: Byte offset into the buffer
            length: Number of elements (not bytes)
        """
        if array_type not in TYPED_ARRAY_INFO:
            raise ValueError(f"Invalid TypedArray type: {array_type}")

        self._type = array_type
        self._buffer = buffer
        self._byte_offset = byte_offset

        ctype, element_size = TYPED_ARRAY_INFO[array_type]
        self._element_size = element_size
        self._ctype = ctype

        # Validate alignment
        if element_size > 1 and byte_offset % element_size != 0:
            name = TYPED_ARRAY_NAMES.get(array_type, "TypedArray")
            raise RangeError(
                f"start offset of {name} should be a multiple of {element_size}"
            )

        # Calculate length
        if length is None:
            remaining = buffer.byte_length - byte_offset
            length = remaining // element_size

        self._length = length

        # Validate bounds
        if (length * element_size + byte_offset) > buffer.byte_length:
            raise RangeError("Invalid typed array length")

    @property
    def array_type(self) -> int:
        """Get the TypedArray type."""
        return self._type

    @property
    def buffer(self) -> ArrayBuffer:
        """Get the underlying ArrayBuffer."""
        return self._buffer

    @property
    def byte_offset(self) -> int:
        """Get the byte offset into the buffer."""
        return self._byte_offset

    @property
    def byte_length(self) -> int:
        """Get the length in bytes."""
        return self._length * self._element_size

    @property
    def length(self) -> int:
        """Get the number of elements."""
        return self._length

    @property
    def data_ptr(self) -> int:
        """Get the raw pointer to the data."""
        if self._buffer.detached or self._buffer.byte_length == 0:
            return 0
        return self._buffer.data_ptr + self._byte_offset

    def __len__(self) -> int:
        return self._length

    def __getitem__(self, index: int) -> Union[int, float]:
        if index < 0 or index >= self._length:
            raise IndexError("TypedArray index out of range")

        ptr = self.data_ptr + index * self._element_size
        ctype_ptr = cast(ptr, POINTER(self._ctype))
        return ctype_ptr[0]

    def __setitem__(self, index: int, value: Union[int, float]) -> None:
        if index < 0 or index >= self._length:
            raise IndexError("TypedArray index out of range")

        ptr = self.data_ptr + index * self._element_size
        ctype_ptr = cast(ptr, POINTER(self._ctype))
        ctype_ptr[0] = value

    def __repr__(self) -> str:
        name = TYPED_ARRAY_NAMES.get(self._type, "TypedArray")
        return f"{name}(length={self._length})"


class RangeError(Exception):
    """JavaScript-style RangeError."""

    def __init__(self, message: str, code: Optional[str] = None):
        super().__init__(message)
        self.code = code


class DataView:
    """
    Python implementation of JavaScript DataView.

    Provides a low-level interface for reading and writing
    arbitrary data types from an ArrayBuffer.
    """

    def __init__(
        self,
        buffer: ArrayBuffer,
        byte_offset: int = 0,
        byte_length: Optional[int] = None,
    ):
        """Create a DataView."""
        self._buffer = buffer
        self._byte_offset = byte_offset

        if byte_length is None:
            byte_length = buffer.byte_length - byte_offset

        if (byte_offset + byte_length) > buffer.byte_length:
            raise RangeError(
                "byte_offset + byte_length should be less than or equal to "
                "the size in bytes of the array passed in",
                "ERR_NAPI_INVALID_DATAVIEW_ARGS",
            )

        self._byte_length = byte_length

    @property
    def buffer(self) -> ArrayBuffer:
        return self._buffer

    @property
    def byte_offset(self) -> int:
        return self._byte_offset

    @property
    def byte_length(self) -> int:
        return self._byte_length

    @property
    def data_ptr(self) -> int:
        """Get the raw pointer to the data."""
        if self._buffer.detached or self._buffer.byte_length == 0:
            return 0
        return self._buffer.data_ptr + self._byte_offset

    def __repr__(self) -> str:
        return f"DataView(byteLength={self._byte_length})"


# Constructor map for type checking
TYPED_ARRAY_CONSTRUCTORS = (TypedArray, DataView)


def is_arraybuffer(value: Any) -> bool:
    """Check if value is an ArrayBuffer."""
    return isinstance(value, ArrayBuffer)


def is_typedarray(value: Any) -> bool:
    """Check if value is a TypedArray (not DataView)."""
    return isinstance(value, TypedArray)


def is_dataview(value: Any) -> bool:
    """Check if value is a DataView."""
    return isinstance(value, DataView)


def is_buffer(value: Any) -> bool:
    """Check if value is a Buffer (TypedArray or bytes)."""
    return isinstance(value, (TypedArray, bytes, bytearray, memoryview))
