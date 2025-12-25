"""Test the complex test addon."""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from napi_python import load_addon

addon_path = (
    Path(__file__).parent.parent / "test-addon" / "test-addon.darwin-arm64.node"
)

print(f"Loading addon from: {addon_path}")
addon = load_addon(str(addon_path))

print(f"Addon exports: {dir(addon)}")

# Test simple functions
print("\n=== Simple Functions ===")
result = addon.add(2, 3)
print(f"add(2, 3) = {result}")
assert result == 5, f"Expected 5, got {result}"

result = addon.getMagicNumber()
print(f"getMagicNumber() = {result}")
assert result == 42, f"Expected 42, got {result}"

result = addon.greet("World")
print(f"greet('World') = {result}")
assert result == "Hello, World!", f"Expected 'Hello, World!', got {result}"

result = addon.greet("Python")
print(f"greet('Python') = {result}")
assert result == "Hello, Python!", f"Expected 'Hello, Python!', got {result}"

# Test unicode strings
result = addon.greet("日本語")
print(f"greet('日本語') = {result}")
assert result == "Hello, 日本語!", f"Expected 'Hello, 日本語!', got {result}"

# Test arrays
print("\n=== Arrays ===")
result = addon.doubleArray([1, 2, 3])
print(f"doubleArray([1,2,3]) = {result}")
assert result == [2, 4, 6], f"Expected [2, 4, 6], got {result}"

result = addon.arrayLength([1, 2, 3, 4, 5])
print(f"arrayLength([1,2,3,4,5]) = {result}")
assert result == 5, f"Expected 5, got {result}"

# Test callbacks - these work!
print("\n=== Callbacks ===")
result = addon.callWithValue(lambda x: x * 2, 5)
print(f"callWithValue(lambda x: x * 2, 5) = {result}")
assert result == 10, f"Expected 10, got {result}"

result = addon.mapAndSum([1, 2, 3], lambda x: x * 2)
print(f"mapAndSum([1,2,3], lambda x: x * 2) = {result}")
assert result == 12, f"Expected 12, got {result}"

# Test optional
print("\n=== Optional ===")
result = addon.maybeDouble(5)
print(f"maybeDouble(5) = {result}")
assert result == 10, f"Expected 10, got {result}"

result = addon.maybeDouble(-5)
print(f"maybeDouble(-5) = {result}")
assert result is None, f"Expected None, got {result}"

result = addon.greetOptional(None)
print(f"greetOptional(None) = {result}")
assert result == "Hello, stranger!", f"Expected 'Hello, stranger!', got {result}"

# Test division (error handling not fully working yet)
print("\n=== Math ===")
result = addon.divide(10, 2)
print(f"divide(10, 2) = {result}")
assert result == 5, f"Expected 5, got {result}"

# Test class
print("\n=== Class ===")
counter = addon.Counter(10)
print(f"Counter(10).value = {counter.value}")
assert counter.value == 10, f"Expected 10, got {counter.value}"

counter.increment()
print(f"After increment(): {counter.value}")
assert counter.value == 11, f"Expected 11, got {counter.value}"

counter.add(5)
print(f"After add(5): {counter.value}")
assert counter.value == 16, f"Expected 16, got {counter.value}"

counter.reset()
print(f"After reset(): {counter.value}")
assert counter.value == 0, f"Expected 0, got {counter.value}"

# Test Buffer/TypedArray functions
print("\n=== Buffers ===")

# Test buffer_length - if function exists
if hasattr(addon, "bufferLength"):
    # Create a bytes object to pass as buffer
    test_bytes = bytes([1, 2, 3, 4, 5])
    result = addon.bufferLength(test_bytes)
    print(f"bufferLength(bytes[5]) = {result}")
    assert result == 5, f"Expected 5, got {result}"

    # Test create_buffer
    result = addon.createBuffer(10, 42)
    print(
        f"createBuffer(10, 42) = {type(result).__name__}, len={len(result) if hasattr(result, '__len__') else 'N/A'}"
    )

    # Test buffer_sum
    test_bytes = bytes([1, 2, 3, 4, 5])
    result = addon.bufferSum(test_bytes)
    print(f"bufferSum([1,2,3,4,5]) = {result}")
    assert result == 15, f"Expected 15, got {result}"

    # Test buffer_get_byte
    test_bytes = bytes([10, 20, 30, 40, 50])
    result = addon.bufferGetByte(test_bytes, 2)
    print(f"bufferGetByte([10,20,30,40,50], 2) = {result}")
    assert result == 30, f"Expected 30, got {result}"

    print("Buffer tests passed!")
else:
    print("Buffer functions not available (rebuild test-addon to add them)")

# Test TypedArray functions
print("\n=== TypedArrays ===")

if hasattr(addon, "createUint8Array"):
    # Test create_uint8_array
    result = addon.createUint8Array(5)
    print(f"createUint8Array(5) = {type(result).__name__}")

    # Test uint8_array_length
    test_bytes = bytes([1, 2, 3, 4, 5])
    result = addon.uint8ArrayLength(test_bytes)
    print(f"uint8ArrayLength(bytes[5]) = {result}")
    assert result == 5, f"Expected 5, got {result}"

    # Test uint8_array_sum
    test_bytes = bytes([1, 2, 3, 4, 5])
    result = addon.uint8ArraySum(test_bytes)
    print(f"uint8ArraySum([1,2,3,4,5]) = {result}")
    assert result == 15, f"Expected 15, got {result}"

    # Test double_uint8_array
    test_bytes = bytes([1, 2, 3, 4, 5])
    result = addon.doubleUint8Array(test_bytes)
    print(f"doubleUint8Array([1,2,3,4,5]) = {type(result).__name__}")

    print("TypedArray tests passed!")
else:
    print("TypedArray functions not available (rebuild test-addon to add them)")

print("\n=== Summary ===")
print("Working:")
print("  - Simple functions (add, getMagicNumber)")
print("  - String functions (greet with ASCII and Unicode)")
print("  - Arrays (doubleArray, arrayLength)")
print("  - Callbacks (callWithValue, mapAndSum)")
print("  - Optional values (maybeDouble, greetOptional)")
print("  - Division")
print("  - Classes (Counter with methods and properties)")
print("  - Buffers (if available)")
print("  - TypedArrays (if available)")
print("")
print("Known issues:")
print("  - Error throwing not yet implemented")

print("\n=== Core tests passed! ===")
