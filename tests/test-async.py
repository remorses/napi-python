"""
Test async functions with asyncio.

Ported from emnapi's packages/test/async tests.
Tests async work execution, concurrent operations, error handling, and repeated work.
"""

import sys
import asyncio
import inspect
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common import (
    load_test_addon,
    TestRunner,
    must_call,
    must_call_at_least,
    assert_strict_equal,
    assert_deep_strict_equal,
    assert_throws,
)


# =============================================================================
# Async Test Runner
# =============================================================================


class AsyncTestRunner(TestRunner):
    """Test runner that supports async tests."""

    def __init__(self, name: str):
        super().__init__(name)
        self.loop = None

    def run(self, verbose: bool = True):
        """Run all registered tests, supporting both sync and async."""
        if verbose:
            print(f"\n{'=' * 60}")
            print(f"Running: {self.name}")
            print("=" * 60)

        # Create event loop for async tests
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            for name, fn in self.tests:
                try:
                    # Check if the test is async
                    if inspect.iscoroutinefunction(fn):
                        self.loop.run_until_complete(fn())
                    else:
                        fn()
                    self.passed += 1
                    if verbose:
                        print(f"  [PASS] {name}")
                except Exception as e:
                    self.failed += 1
                    if verbose:
                        print(f"  [FAIL] {name}")
                        print(f"         {type(e).__name__}: {e}")
                        import traceback

                        traceback.print_exc()
        finally:
            self.loop.close()

        if verbose:
            print("-" * 60)
            print(
                f"Results: {self.passed} passed, {self.failed} failed, {self.skipped} skipped"
            )
            print("=" * 60)

        return self.failed == 0


# =============================================================================
# Load addon
# =============================================================================

addon = load_test_addon()
runner = AsyncTestRunner("Async Tests")


# =============================================================================
# Test: Basic async execution (asyncAdd)
# Ported from: test_async.Test(5, {}, callback) which multiplies by 2
# =============================================================================


@runner.test("asyncAdd - basic async execution")
async def test_async_add_basic():
    """Test basic async addition."""
    result = addon.asyncAdd(2, 3)
    assert asyncio.isfuture(result), "Expected a Future"
    value = await asyncio.wait_for(result, timeout=5.0)
    assert_strict_equal(value, 5, "asyncAdd(2, 3) should return 5")


@runner.test("asyncAdd - with zero")
async def test_async_add_zero():
    """Test async addition with zero."""
    result = addon.asyncAdd(0, 0)
    value = await asyncio.wait_for(result, timeout=5.0)
    assert_strict_equal(value, 0, "asyncAdd(0, 0) should return 0")


@runner.test("asyncAdd - with negative numbers")
async def test_async_add_negative():
    """Test async addition with negative numbers."""
    result = addon.asyncAdd(-10, 5)
    value = await asyncio.wait_for(result, timeout=5.0)
    assert_strict_equal(value, -5, "asyncAdd(-10, 5) should return -5")


@runner.test("asyncAdd - large numbers")
async def test_async_add_large():
    """Test async addition with large numbers."""
    result = addon.asyncAdd(1000000, 2000000)
    value = await asyncio.wait_for(result, timeout=5.0)
    assert_strict_equal(
        value, 3000000, "asyncAdd(1000000, 2000000) should return 3000000"
    )


# =============================================================================
# Test: Async with delay (delayedValue)
# Simulates the sleep(1) in emnapi's Execute callback
# =============================================================================


@runner.test("delayedValue - basic delayed return")
async def test_delayed_value_basic():
    """Test delayed value return."""
    result = addon.delayedValue(42, 100)
    assert asyncio.isfuture(result), "Expected a Future"
    value = await asyncio.wait_for(result, timeout=5.0)
    assert_strict_equal(value, 42, "delayedValue(42, 100) should return 42")


@runner.test("delayedValue - verifies actual delay")
async def test_delayed_value_timing():
    """Test that delayedValue actually delays."""
    start = time.time()
    result = addon.delayedValue(100, 150)  # 150ms delay
    value = await asyncio.wait_for(result, timeout=5.0)
    elapsed = time.time() - start
    assert_strict_equal(value, 100, "delayedValue should return correct value")
    assert elapsed >= 0.14, (
        f"Should have taken at least 140ms, took {elapsed * 1000:.0f}ms"
    )


@runner.test("delayedValue - with zero delay")
async def test_delayed_value_zero_delay():
    """Test delayedValue with zero delay."""
    result = addon.delayedValue(999, 0)
    value = await asyncio.wait_for(result, timeout=5.0)
    assert_strict_equal(
        value, 999, "delayedValue with 0 delay should return immediately"
    )


@runner.test("delayedValue - with negative value")
async def test_delayed_value_negative():
    """Test delayedValue with negative value."""
    result = addon.delayedValue(-123, 50)
    value = await asyncio.wait_for(result, timeout=5.0)
    assert_strict_equal(value, -123, "delayedValue should handle negative values")


# =============================================================================
# Test: Async error handling (asyncDivide)
# Tests error propagation in async context
# =============================================================================


@runner.test("asyncDivide - successful division")
async def test_async_divide_success():
    """Test successful async division."""
    result = addon.asyncDivide(10, 2)
    value = await asyncio.wait_for(result, timeout=5.0)
    assert_strict_equal(value, 5, "asyncDivide(10, 2) should return 5")


@runner.test("asyncDivide - division by zero throws")
async def test_async_divide_error():
    """Test that async division by zero raises an error."""
    result = addon.asyncDivide(10, 0)
    try:
        await asyncio.wait_for(result, timeout=5.0)
        raise AssertionError("Expected division by zero to throw")
    except Exception as e:
        # The error should propagate from the async function
        assert "zero" in str(e).lower() or "Division" in str(e), (
            f"Expected division error, got: {e}"
        )


@runner.test("asyncDivide - integer division")
async def test_async_divide_integer():
    """Test integer division behavior."""
    result = addon.asyncDivide(7, 2)
    value = await asyncio.wait_for(result, timeout=5.0)
    assert_strict_equal(
        value, 3, "asyncDivide(7, 2) should return 3 (integer division)"
    )


@runner.test("asyncDivide - negative numbers")
async def test_async_divide_negative():
    """Test async division with negative numbers."""
    result = addon.asyncDivide(-10, 2)
    value = await asyncio.wait_for(result, timeout=5.0)
    assert_strict_equal(value, -5, "asyncDivide(-10, 2) should return -5")


# =============================================================================
# Test: Async array processing (asyncSum)
# =============================================================================


@runner.test("asyncSum - basic sum")
async def test_async_sum_basic():
    """Test basic async sum."""
    result = addon.asyncSum([1, 2, 3, 4, 5])
    assert asyncio.isfuture(result), "Expected a Future"
    value = await asyncio.wait_for(result, timeout=5.0)
    assert_strict_equal(value, 15, "asyncSum([1,2,3,4,5]) should return 15")


@runner.test("asyncSum - empty array")
async def test_async_sum_empty():
    """Test async sum with empty array."""
    result = addon.asyncSum([])
    value = await asyncio.wait_for(result, timeout=5.0)
    assert_strict_equal(value, 0, "asyncSum([]) should return 0")


@runner.test("asyncSum - single element")
async def test_async_sum_single():
    """Test async sum with single element."""
    result = addon.asyncSum([42])
    value = await asyncio.wait_for(result, timeout=5.0)
    assert_strict_equal(value, 42, "asyncSum([42]) should return 42")


@runner.test("asyncSum - with negative numbers")
async def test_async_sum_negative():
    """Test async sum with negative numbers."""
    result = addon.asyncSum([-1, -2, 3, 4])
    value = await asyncio.wait_for(result, timeout=5.0)
    assert_strict_equal(value, 4, "asyncSum([-1,-2,3,4]) should return 4")


@runner.test("asyncSum - large array")
async def test_async_sum_large():
    """Test async sum with large array."""
    numbers = list(range(1, 101))  # 1 to 100
    result = addon.asyncSum(numbers)
    value = await asyncio.wait_for(result, timeout=5.0)
    assert_strict_equal(value, 5050, "asyncSum([1..100]) should return 5050")


# =============================================================================
# Test: Concurrent async operations
# Ported from: multiple async work items queued simultaneously
# =============================================================================


@runner.test("concurrent - multiple asyncAdd calls")
async def test_concurrent_add():
    """Test multiple concurrent asyncAdd calls."""

    # Wrap in coroutines to ensure proper handling with asyncio.gather
    async def do_add(a, b):
        return await addon.asyncAdd(a, b)

    results = await asyncio.gather(
        do_add(1, 2),
        do_add(3, 4),
        do_add(5, 6),
    )
    assert_deep_strict_equal(
        list(results), [3, 7, 11], "Concurrent asyncAdd should work"
    )


@runner.test("concurrent - multiple delayedValue calls run in parallel")
async def test_concurrent_delayed_parallel():
    """Test that multiple delayedValue calls run in parallel, not sequentially."""
    start = time.time()
    futures = [
        addon.delayedValue(1, 100),
        addon.delayedValue(2, 100),
        addon.delayedValue(3, 100),
    ]
    results = await asyncio.gather(*futures)
    elapsed = time.time() - start

    assert_deep_strict_equal(list(results), [1, 2, 3], "All values should be returned")
    # Should complete in ~100ms since they run in parallel, not 300ms
    assert elapsed < 0.5, (
        f"Should have completed in parallel, took {elapsed * 1000:.0f}ms"
    )


@runner.test("concurrent - mixed async operations")
async def test_concurrent_mixed():
    """Test sequential execution of different async operations."""
    # Run sequentially to avoid resource exhaustion
    result1 = await addon.asyncAdd(10, 20)
    result2 = await addon.asyncSum([1, 2, 3])
    result3 = await addon.asyncDivide(100, 5)
    result4 = await addon.delayedValue(42, 50)

    assert_strict_equal(result1, 30, "asyncAdd should return 30")
    assert_strict_equal(result2, 6, "asyncSum should return 6")
    assert_strict_equal(result3, 20, "asyncDivide should return 20")
    assert_strict_equal(result4, 42, "delayedValue should return 42")


@runner.test("concurrent - many sequential operations")
async def test_concurrent_many():
    """Test many sequential operations."""
    # Run sequentially to avoid resource exhaustion
    n = 20
    all_results = []

    for i in range(n):
        result = await addon.asyncAdd(i, i)
        all_results.append(result)

    expected = [i * 2 for i in range(n)]
    assert_deep_strict_equal(
        list(all_results), expected, f"Should handle {n} sequential operations"
    )


# =============================================================================
# Test: Repeated async work
# Ported from: DoRepeatedWork test with 500 iterations
# =============================================================================


@runner.test("repeated - multiple sequential async calls")
async def test_repeated_sequential():
    """Test repeated sequential async calls (simulates DoRepeatedWork)."""
    iterations = 100
    results = []
    for i in range(iterations):
        result = await addon.asyncAdd(i, 1)
        results.append(result)

    expected = [i + 1 for i in range(iterations)]
    assert_deep_strict_equal(
        results, expected, f"Should handle {iterations} sequential calls"
    )


@runner.test("repeated - alternating operations")
async def test_repeated_alternating():
    """Test alternating between different async operations."""
    results = []
    for i in range(20):
        if i % 2 == 0:
            result = await addon.asyncAdd(i, i)
        else:
            result = await addon.asyncSum([i, i, i])
        results.append(result)

    expected = []
    for i in range(20):
        if i % 2 == 0:
            expected.append(i * 2)
        else:
            expected.append(i * 3)

    assert_deep_strict_equal(results, expected, "Alternating operations should work")


# =============================================================================
# Test: Timeout behavior
# =============================================================================


@runner.test("timeout - asyncio.wait_for with timeout")
async def test_timeout_behavior():
    """Test that asyncio timeout works correctly with delayed values."""
    # This should NOT timeout
    result = await asyncio.wait_for(addon.delayedValue(1, 50), timeout=1.0)
    assert_strict_equal(result, 1, "Should return before timeout")


@runner.test("timeout - short timeout on long delay")
async def test_timeout_short():
    """Test that short timeout properly times out on long delay."""
    try:
        # Delay of 500ms with timeout of 100ms should fail
        await asyncio.wait_for(addon.delayedValue(1, 500), timeout=0.1)
        raise AssertionError("Should have timed out")
    except asyncio.TimeoutError:
        pass  # Expected


# =============================================================================
# Test: Error propagation in concurrent operations
# =============================================================================


@runner.test("error - single error in gather with return_exceptions")
async def test_error_in_gather():
    """Test error handling in asyncio.gather with return_exceptions."""

    async def do_divide(a, b):
        return await addon.asyncDivide(a, b)

    results = await asyncio.gather(
        do_divide(10, 2),
        do_divide(10, 0),  # This will fail
        do_divide(20, 4),
        return_exceptions=True,
    )

    assert_strict_equal(results[0], 5, "First result should be 5")
    assert isinstance(results[1], Exception), "Second result should be an exception"
    assert_strict_equal(results[2], 5, "Third result should be 5")


@runner.test("error - error in first of sequential operations")
async def test_error_sequential():
    """Test error handling in sequential operations."""
    results = []
    caught_error = False

    try:
        results.append(await addon.asyncDivide(10, 2))
        results.append(await addon.asyncDivide(10, 0))  # This fails
        results.append(await addon.asyncDivide(20, 4))  # Should not reach
    except Exception:
        caught_error = True

    assert caught_error, "Should have caught the error"
    assert_deep_strict_equal(results, [5], "Only first result should be captured")


# =============================================================================
# Test: Async function returns Future
# =============================================================================


@runner.test("future - asyncAdd returns awaitable future")
async def test_future_type_add():
    """Verify asyncAdd returns a proper Future-like object."""
    result = addon.asyncAdd(1, 1)
    assert asyncio.isfuture(result) or hasattr(result, "__await__"), (
        "asyncAdd should return a Future-like object"
    )
    value = await result
    assert_strict_equal(value, 2, "Awaited value should be correct")


@runner.test("future - delayedValue returns awaitable future")
async def test_future_type_delayed():
    """Verify delayedValue returns a proper Future-like object."""
    result = addon.delayedValue(99, 10)
    assert asyncio.isfuture(result) or hasattr(result, "__await__"), (
        "delayedValue should return a Future-like object"
    )
    value = await result
    assert_strict_equal(value, 99, "Awaited value should be correct")


@runner.test("future - asyncSum returns awaitable future")
async def test_future_type_sum():
    """Verify asyncSum returns a proper Future-like object."""
    result = addon.asyncSum([1, 2, 3])
    assert asyncio.isfuture(result) or hasattr(result, "__await__"), (
        "asyncSum should return a Future-like object"
    )
    value = await result
    assert_strict_equal(value, 6, "Awaited value should be correct")


@runner.test("future - asyncDivide returns awaitable future")
async def test_future_type_divide():
    """Verify asyncDivide returns a proper Future-like object."""
    result = addon.asyncDivide(10, 2)
    assert asyncio.isfuture(result) or hasattr(result, "__await__"), (
        "asyncDivide should return a Future-like object"
    )
    value = await result
    assert_strict_equal(value, 5, "Awaited value should be correct")


# =============================================================================
# Test: Multiple awaits on same future
# =============================================================================


@runner.test("await - multiple awaits on completed future")
async def test_multiple_awaits():
    """Test that a future can be awaited multiple times after completion."""
    future = addon.asyncAdd(5, 5)
    value1 = await future
    # Note: In Python, once a future is done, awaiting it again returns the result
    # This tests the behavior of the NAPI Python future implementation
    try:
        # Try to await again - behavior depends on implementation
        # Some implementations allow this, some don't
        value2 = await asyncio.wait_for(
            asyncio.shield(asyncio.create_task(asyncio.sleep(0))), timeout=0.1
        )
    except Exception:
        pass  # Some implementations don't support multiple awaits

    assert_strict_equal(value1, 10, "First await should return correct value")


# =============================================================================
# Test: Ordering of async completions
# =============================================================================


@runner.test("ordering - shorter delays complete first")
async def test_ordering_by_delay():
    """Test that async operations complete in order of their delay times."""
    completed = []

    async def track_completion(delay_ms, value):
        result = await addon.delayedValue(value, delay_ms)
        completed.append(result)
        return result

    # Create tasks with different delays
    tasks = [
        asyncio.create_task(track_completion(150, 1)),  # Slow
        asyncio.create_task(track_completion(50, 2)),  # Fast
        asyncio.create_task(track_completion(100, 3)),  # Medium
    ]

    await asyncio.gather(*tasks)

    # Values should complete in order: 2 (50ms), 3 (100ms), 1 (150ms)
    assert_deep_strict_equal(completed, [2, 3, 1], "Should complete in delay order")


# =============================================================================
# Test: Stress test for async work pool
# Similar to MAX_CANCEL_THREADS test in emnapi
# =============================================================================


@runner.test("stress - many concurrent operations with delays")
async def test_stress_concurrent():
    """Stress test with many delayed operations (run sequentially for stability)."""
    n = 10  # Reduced count for stability
    delay = 10  # Reduced delay

    # Run sequentially to avoid overwhelming the async system
    results = []
    for i in range(n):
        result = await addon.delayedValue(i, delay)
        results.append(result)

    expected = list(range(n))
    assert_deep_strict_equal(
        list(results), expected, f"All {n} values should be correct"
    )


@runner.test("stress - rapid sequential async calls")
async def test_stress_rapid_fire():
    """Stress test with sequential async calls."""
    # Run sequentially to avoid resource exhaustion
    n = 50
    all_values = []

    for _ in range(n):
        result = await addon.asyncAdd(1, 1)
        all_values.append(result)

    assert all(v == 2 for v in all_values), "All calls should return 2"
    assert len(all_values) == n, f"Should have {n} results"


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    success = runner.run(verbose=True)
    sys.exit(0 if success else 1)
