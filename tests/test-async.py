"""Test async functions with asyncio."""

import sys
import asyncio
import time
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


async def test_async():
    print("\n=== Async Functions ===")

    # Test async add
    print("Testing asyncAdd(2, 3)...")
    result = addon.asyncAdd(2, 3)
    assert asyncio.isfuture(result), "Expected a Future"
    value = await asyncio.wait_for(result, timeout=5.0)
    print(f"asyncAdd(2, 3) = {value}")
    assert value == 5, f"Expected 5, got {value}"

    # Test async sum
    print("Testing asyncSum([1, 2, 3, 4, 5])...")
    result = addon.asyncSum([1, 2, 3, 4, 5])
    assert asyncio.isfuture(result), "Expected a Future"
    value = await asyncio.wait_for(result, timeout=5.0)
    print(f"asyncSum([1,2,3,4,5]) = {value}")
    assert value == 15, f"Expected 15, got {value}"

    # Test delayed value
    print("Testing delayedValue(42, 100)...")
    start = time.time()
    result = addon.delayedValue(42, 100)
    assert asyncio.isfuture(result), "Expected a Future"
    value = await asyncio.wait_for(result, timeout=5.0)
    elapsed = time.time() - start
    print(f"delayedValue(42, 100) = {value} (took {elapsed * 1000:.0f}ms)")
    assert value == 42, f"Expected 42, got {value}"
    assert elapsed >= 0.09, (
        f"Should have taken at least 90ms, took {elapsed * 1000:.0f}ms"
    )

    # Test multiple concurrent async calls
    print("\nTesting concurrent async calls...")
    start = time.time()
    futures = [
        addon.delayedValue(1, 100),
        addon.delayedValue(2, 100),
        addon.delayedValue(3, 100),
    ]
    results = await asyncio.gather(*futures)
    elapsed = time.time() - start
    print(f"Concurrent results: {results} (took {elapsed * 1000:.0f}ms)")
    assert results == [1, 2, 3], f"Expected [1,2,3], got {results}"
    # Should complete in ~100ms since they run in parallel, not 300ms
    assert elapsed < 0.5, (
        f"Should have completed in parallel, took {elapsed * 1000:.0f}ms"
    )

    print("\n=== All async tests passed! ===")


# Create and run the event loop
print("Running async tests...")
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
try:
    loop.run_until_complete(test_async())
finally:
    loop.close()
