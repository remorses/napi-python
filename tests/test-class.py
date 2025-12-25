"""Test NAPI class support."""

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

print("\n=== Testing Counter class ===")

# Test class exists and is callable
print(f"Counter type: {type(addon.Counter)}")
assert callable(addon.Counter), "Counter should be callable"

# Create with default value
c1 = addon.Counter()
print(f"Counter() created: {c1}")
assert c1.value == 0, f"Default value should be 0, got {c1.value}"

# Create with initial value
c2 = addon.Counter(10)
print(f"Counter(10) created: {c2}")
assert c2.value == 10, f"Initial value should be 10, got {c2.value}"

# Test increment
c2.increment()
print(f"After increment(): {c2.value}")
assert c2.value == 11, f"After increment should be 11, got {c2.value}"

# Test decrement
c2.decrement()
print(f"After decrement(): {c2.value}")
assert c2.value == 10, f"After decrement should be 10, got {c2.value}"

# Test add
c2.add(5)
print(f"After add(5): {c2.value}")
assert c2.value == 15, f"After add(5) should be 15, got {c2.value}"

# Test reset
c2.reset()
print(f"After reset(): {c2.value}")
assert c2.value == 0, f"After reset should be 0, got {c2.value}"

# Test setter
c2.value = 42
print(f"After c2.value = 42: {c2.value}")
assert c2.value == 42, f"After setting value should be 42, got {c2.value}"

# Test multiple instances are independent
c3 = addon.Counter(100)
print(f"\nTesting independence of instances:")
print(f"c2.value = {c2.value}, c3.value = {c3.value}")
c3.increment()
print(f"After c3.increment(): c2.value = {c2.value}, c3.value = {c3.value}")
assert c2.value == 42, "c2 should be unchanged"
assert c3.value == 101, "c3 should be 101"

print("\n=== All class tests passed! ===")
