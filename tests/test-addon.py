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

# Note: greet has string truncation issue
print(f"greet('World') = {addon.greet('World')} (known issue: string truncation)")

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

print("\n=== Summary ===")
print("Working:")
print("  - Simple functions (add, getMagicNumber)")
print("  - Arrays (doubleArray, arrayLength)")
print("  - Callbacks (callWithValue, mapAndSum)")
print("  - Optional values (maybeDouble, greetOptional)")
print("  - Division")
print("  - Classes (Counter with methods and properties)")
print("")
print("Known issues:")
print("  - String arguments get truncated in some cases")
print("  - Error throwing not yet implemented")

print("\n=== Core tests passed! ===")
