#!/usr/bin/env python3
"""
Load and use the canvas npm package native addon with napi-python.

This demonstrates:
1. Loading the node-canvas native addon
2. Creating a Canvas object
3. Exporting canvas content as PNG

Note: Drawing operations (via CanvasRenderingContext2d) require additional
work in napi-python to properly handle the native context binding.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from napi_python import load_addon

# Path to the canvas native addon
ADDON = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "node_modules/canvas/build/Release/canvas.node",
)

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "canvas-output.png")


def main():
    print(f"Loading canvas addon from: {ADDON}")

    if not os.path.exists(ADDON):
        print("Error: canvas.node not found. Run 'npm install canvas' first.")
        sys.exit(1)

    # Load the native canvas addon
    canvas_bindings = load_addon(ADDON)

    print(f"Canvas addon loaded successfully!")
    print(f"Available exports: {', '.join(dir(canvas_bindings))}")

    # Check versions
    print(f"\nLibrary versions:")
    print(f"  Cairo: {canvas_bindings.cairoVersion}")
    print(f"  Pango: {canvas_bindings.pangoVersion}")
    print(f"  FreeType: {canvas_bindings.freetypeVersion}")

    # Create a canvas
    width, height = 400, 300
    canvas = canvas_bindings.Canvas(width, height)
    print(f"\nCreated canvas: {int(canvas.width)}x{int(canvas.height)}")
    print(f"Canvas type: {canvas.type}")
    print(f"Canvas stride: {int(canvas.stride)} bytes")

    # Export to PNG buffer
    # Note: toBuffer() without arguments returns PNG format
    print("\nExporting to PNG...")
    buffer = canvas.toBuffer()

    # Convert TypedArray to bytes
    png_data = bytes(buffer)

    # Verify PNG magic number
    if png_data[:8] == b"\x89PNG\r\n\x1a\n":
        print("Valid PNG header detected")

    # Save to file
    with open(OUTPUT_FILE, "wb") as f:
        f.write(png_data)

    print(f"\nImage saved to: {OUTPUT_FILE}")
    print(f"File size: {len(png_data)} bytes")

    # Show what we could do with more NAPI support
    print("\n--- Canvas API available (methods on Canvas) ---")
    canvas_methods = [m for m in dir(canvas) if not m.startswith("_")]
    print(f"  {', '.join(canvas_methods)}")

    # Create context to show it's available
    ctx = canvas_bindings.CanvasRenderingContext2d(canvas)
    ctx_methods = [m for m in dir(ctx) if not m.startswith("_")][:15]
    print(f"\n--- CanvasRenderingContext2d methods (sample) ---")
    print(f"  {', '.join(ctx_methods)}")
    print("  ... and more")


if __name__ == "__main__":
    main()
