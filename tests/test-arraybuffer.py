"""Test ArrayBuffer and TypedArray functionality."""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from napi_python._values.arraybuffer import (
    ArrayBuffer,
    TypedArray,
    DataView,
    RangeError,
    TYPED_ARRAY_INFO,
    is_arraybuffer,
    is_typedarray,
    is_dataview,
)
from napi_python._napi.types import napi_typedarray_type

print("=== ArrayBuffer Tests ===")

# Test ArrayBuffer creation
print("\n--- ArrayBuffer Creation ---")
buf = ArrayBuffer(16)
print(f"ArrayBuffer(16): byte_length={buf.byte_length}, data_ptr={hex(buf.data_ptr)}")
assert buf.byte_length == 16, f"Expected 16, got {buf.byte_length}"
assert buf.data_ptr != 0, "Expected non-zero pointer"
assert not buf.detached, "Buffer should not be detached"

# Test ArrayBuffer from data
print("\n--- ArrayBuffer.from_data ---")
data = b"Hello, World!"
buf2 = ArrayBuffer.from_data(data)
print(f"ArrayBuffer.from_data({data!r}): byte_length={buf2.byte_length}")
assert buf2.byte_length == len(data), f"Expected {len(data)}, got {buf2.byte_length}"
assert buf2.to_bytes() == data, f"Expected {data!r}, got {buf2.to_bytes()!r}"

# Test ArrayBuffer detach
print("\n--- ArrayBuffer Detach ---")
buf3 = ArrayBuffer(8)
assert not buf3.detached
buf3.detach()
assert buf3.detached, "Buffer should be detached"
assert buf3.byte_length == 0, "Detached buffer should have 0 length"
print(f"After detach: detached={buf3.detached}, byte_length={buf3.byte_length}")

# Test type checking
print("\n--- Type Checking ---")
assert is_arraybuffer(buf), "Should be arraybuffer"
assert not is_typedarray(buf), "ArrayBuffer is not a typedarray"
assert not is_dataview(buf), "ArrayBuffer is not a dataview"
print("Type checks passed")

print("\n=== TypedArray Tests ===")

# Test Uint8Array
print("\n--- Uint8Array ---")
buf = ArrayBuffer(8)
u8 = TypedArray(napi_typedarray_type.napi_uint8_array, buf)
print(
    f"Uint8Array: length={u8.length}, byte_length={u8.byte_length}, offset={u8.byte_offset}"
)
assert u8.length == 8, f"Expected 8, got {u8.length}"
assert u8.byte_length == 8, f"Expected 8, got {u8.byte_length}"
assert u8.byte_offset == 0, f"Expected 0, got {u8.byte_offset}"
assert u8.array_type == napi_typedarray_type.napi_uint8_array

# Test writing and reading
u8[0] = 42
u8[7] = 255
print(f"u8[0]={u8[0]}, u8[7]={u8[7]}")
assert u8[0] == 42, f"Expected 42, got {u8[0]}"
assert u8[7] == 255, f"Expected 255, got {u8[7]}"

# Test Int32Array
print("\n--- Int32Array ---")
buf = ArrayBuffer(16)
i32 = TypedArray(napi_typedarray_type.napi_int32_array, buf)
print(f"Int32Array: length={i32.length}, byte_length={i32.byte_length}")
assert i32.length == 4, f"Expected 4, got {i32.length}"  # 16 bytes / 4 bytes per int32
assert i32.byte_length == 16, f"Expected 16, got {i32.byte_length}"

i32[0] = -1
i32[1] = 2147483647  # INT32_MAX
i32[2] = -2147483648  # INT32_MIN
print(f"i32[0]={i32[0]}, i32[1]={i32[1]}, i32[2]={i32[2]}")
assert i32[0] == -1, f"Expected -1, got {i32[0]}"
assert i32[1] == 2147483647, f"Expected 2147483647, got {i32[1]}"
assert i32[2] == -2147483648, f"Expected -2147483648, got {i32[2]}"

# Test Float64Array
print("\n--- Float64Array ---")
buf = ArrayBuffer(24)
f64 = TypedArray(napi_typedarray_type.napi_float64_array, buf)
print(f"Float64Array: length={f64.length}, byte_length={f64.byte_length}")
assert f64.length == 3, (
    f"Expected 3, got {f64.length}"
)  # 24 bytes / 8 bytes per float64

f64[0] = 3.14159
f64[1] = -273.15
f64[2] = 1e100
print(f"f64[0]={f64[0]}, f64[1]={f64[1]}, f64[2]={f64[2]}")
assert abs(f64[0] - 3.14159) < 0.00001, f"Expected ~3.14159, got {f64[0]}"
assert abs(f64[1] - (-273.15)) < 0.01, f"Expected ~-273.15, got {f64[1]}"

# Test TypedArray with offset
print("\n--- TypedArray with Offset ---")
buf = ArrayBuffer(16)
# Create a view starting at byte 4
u8_offset = TypedArray(
    napi_typedarray_type.napi_uint8_array, buf, byte_offset=4, length=8
)
print(
    f"Uint8Array(offset=4, length=8): length={u8_offset.length}, offset={u8_offset.byte_offset}"
)
assert u8_offset.length == 8
assert u8_offset.byte_offset == 4
assert u8_offset.buffer is buf

# Test alignment error
print("\n--- Alignment Check ---")
try:
    # Int32Array requires 4-byte alignment
    bad_view = TypedArray(napi_typedarray_type.napi_int32_array, buf, byte_offset=3)
    print("ERROR: Should have raised RangeError for misaligned offset")
    assert False
except RangeError as e:
    print(f"Correctly raised RangeError: {e}")

# Test bounds error
print("\n--- Bounds Check ---")
try:
    # Try to create view that extends past buffer
    bad_view = TypedArray(
        napi_typedarray_type.napi_uint8_array, buf, byte_offset=0, length=100
    )
    print("ERROR: Should have raised RangeError for out of bounds")
    assert False
except RangeError as e:
    print(f"Correctly raised RangeError: {e}")

# Test type checking
print("\n--- TypedArray Type Checking ---")
assert is_typedarray(u8), "Should be typedarray"
assert not is_arraybuffer(u8), "TypedArray is not an arraybuffer"
assert not is_dataview(u8), "TypedArray is not a dataview"
print("Type checks passed")

print("\n=== DataView Tests ===")

# Test DataView creation
print("\n--- DataView Creation ---")
buf = ArrayBuffer(16)
dv = DataView(buf)
print(f"DataView: byte_length={dv.byte_length}, offset={dv.byte_offset}")
assert dv.byte_length == 16
assert dv.byte_offset == 0
assert dv.buffer is buf

# Test DataView with offset
dv_offset = DataView(buf, byte_offset=4, byte_length=8)
print(
    f"DataView(offset=4, length=8): byte_length={dv_offset.byte_length}, offset={dv_offset.byte_offset}"
)
assert dv_offset.byte_length == 8
assert dv_offset.byte_offset == 4

# Test bounds error
print("\n--- DataView Bounds Check ---")
try:
    bad_dv = DataView(buf, byte_offset=10, byte_length=10)  # 10 + 10 = 20 > 16
    print("ERROR: Should have raised RangeError")
    assert False
except RangeError as e:
    print(f"Correctly raised RangeError: {e}")

# Test type checking
print("\n--- DataView Type Checking ---")
assert is_dataview(dv), "Should be dataview"
assert not is_arraybuffer(dv), "DataView is not an arraybuffer"
assert not is_typedarray(dv), "DataView is not a typedarray"
print("Type checks passed")

print("\n=== All TypedArray Types Test ===")

for type_enum, (ctype, element_size) in TYPED_ARRAY_INFO.items():
    buf = ArrayBuffer(element_size * 4)  # Create buffer for 4 elements
    ta = TypedArray(type_enum, buf)
    print(f"{type_enum.name}: length={ta.length}, element_size={element_size}")
    assert ta.length == 4, f"Expected 4 elements, got {ta.length}"
    assert ta.byte_length == element_size * 4

print("\n=== Memory Pointer Tests ===")

# Test that data_ptr points to the same memory as buffer
buf = ArrayBuffer(8)
u8 = TypedArray(napi_typedarray_type.napi_uint8_array, buf)

# Write via TypedArray
u8[0] = 0xDE
u8[1] = 0xAD
u8[2] = 0xBE
u8[3] = 0xEF

# Read back raw bytes
raw = buf.to_bytes()
print(f"Written via TypedArray, read via buffer: {raw[:4].hex()}")
assert raw[0] == 0xDE
assert raw[1] == 0xAD
assert raw[2] == 0xBE
assert raw[3] == 0xEF

# Test pointer matches
print(f"Buffer data_ptr: {hex(buf.data_ptr)}")
print(f"TypedArray data_ptr: {hex(u8.data_ptr)}")
assert buf.data_ptr == u8.data_ptr, "Pointers should match for offset=0"

# Test offset pointer
u8_offset = TypedArray(napi_typedarray_type.napi_uint8_array, buf, byte_offset=4)
expected_ptr = buf.data_ptr + 4
print(
    f"TypedArray(offset=4) data_ptr: {hex(u8_offset.data_ptr)}, expected: {hex(expected_ptr)}"
)
assert u8_offset.data_ptr == expected_ptr, "Offset pointer should be buffer + offset"

print("\n=== Shared Memory Tests ===")

# Test that multiple TypedArrays share the same underlying buffer
buf = ArrayBuffer(16)
u8 = TypedArray(napi_typedarray_type.napi_uint8_array, buf)
i32 = TypedArray(napi_typedarray_type.napi_int32_array, buf)

# Write via u8
u8[0] = 0x01
u8[1] = 0x02
u8[2] = 0x03
u8[3] = 0x04

# Read via i32 (little-endian: 0x04030201)
expected_i32 = 0x04030201
print(f"u8[0:4] = [0x01, 0x02, 0x03, 0x04], i32[0] = {hex(i32[0])}")
assert i32[0] == expected_i32, f"Expected {hex(expected_i32)}, got {hex(i32[0])}"

# Write via i32
i32[1] = 0xDEADBEEF
# Read back via u8 (bytes 4-7)
print(
    f"i32[1] = 0xDEADBEEF, u8[4:8] = [{hex(u8[4])}, {hex(u8[5])}, {hex(u8[6])}, {hex(u8[7])}]"
)
assert u8[4] == 0xEF, f"Expected 0xEF, got {hex(u8[4])}"
assert u8[5] == 0xBE, f"Expected 0xBE, got {hex(u8[5])}"
assert u8[6] == 0xAD, f"Expected 0xAD, got {hex(u8[6])}"
assert u8[7] == 0xDE, f"Expected 0xDE, got {hex(u8[7])}"
print("Shared memory tests passed")

print("\n=== Zero-Length Buffer Tests ===")

# Test zero-length ArrayBuffer
buf_zero = ArrayBuffer(0)
assert buf_zero.byte_length == 0, "Zero-length buffer should have length 0"
assert buf_zero.data_ptr == 0, "Zero-length buffer should have null pointer"
assert buf_zero.to_bytes() == b"", "Zero-length buffer should return empty bytes"
print("Zero-length ArrayBuffer: OK")

# Test zero-length TypedArray
buf = ArrayBuffer(8)
u8_zero = TypedArray(
    napi_typedarray_type.napi_uint8_array, buf, byte_offset=0, length=0
)
assert u8_zero.length == 0, "Zero-length TypedArray should have length 0"
assert u8_zero.byte_length == 0, "Zero-length TypedArray should have byte_length 0"
print("Zero-length TypedArray: OK")

# Test zero-length DataView
dv_zero = DataView(buf, byte_offset=0, byte_length=0)
assert dv_zero.byte_length == 0, "Zero-length DataView should have length 0"
print("Zero-length DataView: OK")

print("\n=== Detached Buffer Behavior Tests ===")

buf = ArrayBuffer(8)
u8 = TypedArray(napi_typedarray_type.napi_uint8_array, buf)

# Before detach
assert buf.data_ptr != 0, "Buffer should have valid pointer before detach"
assert u8.data_ptr != 0, "TypedArray should have valid pointer before detach"

# Detach
buf.detach()

# After detach
assert buf.detached, "Buffer should be detached"
assert buf.byte_length == 0, "Detached buffer should have 0 length"
assert buf.data_ptr == 0, "Detached buffer should have null pointer"
assert u8.data_ptr == 0, "TypedArray of detached buffer should have null pointer"
print("Detached buffer behavior: OK")

print("\n=== Float32Array Tests ===")

buf = ArrayBuffer(16)
f32 = TypedArray(napi_typedarray_type.napi_float32_array, buf)
assert f32.length == 4, f"Expected 4 elements, got {f32.length}"

f32[0] = 1.5
f32[1] = -2.25
f32[2] = 3.14159
f32[3] = 0.0

assert abs(f32[0] - 1.5) < 0.0001, f"Expected 1.5, got {f32[0]}"
assert abs(f32[1] - (-2.25)) < 0.0001, f"Expected -2.25, got {f32[1]}"
assert abs(f32[2] - 3.14159) < 0.001, f"Expected ~3.14159, got {f32[2]}"
assert f32[3] == 0.0, f"Expected 0.0, got {f32[3]}"
print("Float32Array read/write: OK")

print("\n=== Uint16Array Tests ===")

buf = ArrayBuffer(8)
u16 = TypedArray(napi_typedarray_type.napi_uint16_array, buf)
assert u16.length == 4, f"Expected 4 elements, got {u16.length}"

u16[0] = 0
u16[1] = 1000
u16[2] = 65535  # max uint16
u16[3] = 32768

assert u16[0] == 0
assert u16[1] == 1000
assert u16[2] == 65535
assert u16[3] == 32768
print("Uint16Array read/write: OK")

print("\n=== Int16Array Tests ===")

buf = ArrayBuffer(8)
i16 = TypedArray(napi_typedarray_type.napi_int16_array, buf)
assert i16.length == 4

i16[0] = 0
i16[1] = -1
i16[2] = 32767  # max int16
i16[3] = -32768  # min int16

assert i16[0] == 0
assert i16[1] == -1
assert i16[2] == 32767
assert i16[3] == -32768
print("Int16Array read/write: OK")

print("\n=== BigInt64Array Tests ===")

buf = ArrayBuffer(16)
bi64 = TypedArray(napi_typedarray_type.napi_bigint64_array, buf)
assert bi64.length == 2

bi64[0] = 9223372036854775807  # max int64
bi64[1] = -9223372036854775808  # min int64

assert bi64[0] == 9223372036854775807
assert bi64[1] == -9223372036854775808
print("BigInt64Array read/write: OK")

print("\n=== BigUint64Array Tests ===")

buf = ArrayBuffer(16)
bu64 = TypedArray(napi_typedarray_type.napi_biguint64_array, buf)
assert bu64.length == 2

bu64[0] = 0
bu64[1] = 18446744073709551615  # max uint64

assert bu64[0] == 0
assert bu64[1] == 18446744073709551615
print("BigUint64Array read/write: OK")

print("\n=== Uint8ClampedArray Tests ===")

buf = ArrayBuffer(4)
u8c = TypedArray(napi_typedarray_type.napi_uint8_clamped_array, buf)
assert u8c.length == 4

# Note: Python ctypes doesn't clamp automatically, so we just test normal range
u8c[0] = 0
u8c[1] = 128
u8c[2] = 255
u8c[3] = 100

assert u8c[0] == 0
assert u8c[1] == 128
assert u8c[2] == 255
assert u8c[3] == 100
print("Uint8ClampedArray read/write: OK")

print("\n=== DataView Pointer Tests ===")

buf = ArrayBuffer(16)
dv = DataView(buf, byte_offset=4, byte_length=8)

# DataView pointer should be buffer + offset
expected_ptr = buf.data_ptr + 4
assert dv.data_ptr == expected_ptr, (
    f"Expected {hex(expected_ptr)}, got {hex(dv.data_ptr)}"
)
print(f"DataView(offset=4) data_ptr: {hex(dv.data_ptr)}, expected: {hex(expected_ptr)}")
print("DataView pointer: OK")

print("\n=== Index Bounds Tests ===")

buf = ArrayBuffer(4)
u8 = TypedArray(napi_typedarray_type.napi_uint8_array, buf)

# Test negative index
try:
    _ = u8[-1]
    assert False, "Should have raised IndexError for negative index"
except IndexError:
    print("Negative index raises IndexError: OK")

# Test out of bounds read
try:
    _ = u8[4]
    assert False, "Should have raised IndexError for out of bounds read"
except IndexError:
    print("Out of bounds read raises IndexError: OK")

# Test out of bounds write
try:
    u8[4] = 0
    assert False, "Should have raised IndexError for out of bounds write"
except IndexError:
    print("Out of bounds write raises IndexError: OK")

print("\n=== len() Tests ===")

buf = ArrayBuffer(16)
assert len(buf) == 16, f"Expected len(buf) == 16, got {len(buf)}"

u8 = TypedArray(napi_typedarray_type.napi_uint8_array, buf)
assert len(u8) == 16, f"Expected len(u8) == 16, got {len(u8)}"

i32 = TypedArray(napi_typedarray_type.napi_int32_array, buf)
assert len(i32) == 4, f"Expected len(i32) == 4, got {len(i32)}"

f64 = TypedArray(napi_typedarray_type.napi_float64_array, buf)
assert len(f64) == 2, f"Expected len(f64) == 2, got {len(f64)}"

print("len() tests: OK")

print("\n=== repr() Tests ===")

buf = ArrayBuffer(16)
assert "ArrayBuffer(16)" in repr(buf), f"Unexpected repr: {repr(buf)}"

u8 = TypedArray(napi_typedarray_type.napi_uint8_array, buf)
assert "Uint8Array" in repr(u8), f"Unexpected repr: {repr(u8)}"

dv = DataView(buf)
assert "DataView" in repr(dv), f"Unexpected repr: {repr(dv)}"

print("repr() tests: OK")

print("\n=== All ArrayBuffer/TypedArray tests passed! ===")
