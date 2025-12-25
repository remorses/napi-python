#!/usr/bin/env python3
"""
Load and use the canvas npm package native addon with napi-python.

This demonstrates:
1. Loading the node-canvas native addon
2. Creating a Canvas object
3. Drawing shapes, text, and paths using CanvasRenderingContext2d
4. Exporting canvas content as PNG
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
    width, height = 400, 200
    canvas = canvas_bindings.Canvas(width, height)
    print(f"\nCreated canvas: {int(canvas.width)}x{int(canvas.height)}")
    print(f"Canvas type: {canvas.type}")
    print(f"Canvas stride: {int(canvas.stride)} bytes")

    # Create 2D rendering context
    ctx = canvas_bindings.CanvasRenderingContext2d(canvas)
    print("\nDrawing on canvas...")

    # Draw background
    ctx.fillStyle = "#1a1a2e"
    ctx.fillRect(0, 0, width, height)

    # Draw colored rectangles
    ctx.fillStyle = "#ff6b6b"  # Red
    ctx.fillRect(20, 20, 80, 80)

    ctx.fillStyle = "#4ecdc4"  # Teal
    ctx.fillRect(120, 20, 80, 80)

    ctx.fillStyle = "#ffe66d"  # Yellow
    ctx.fillRect(220, 20, 80, 80)

    # Draw text
    ctx.fillStyle = "#ffffff"
    ctx.font = "24px sans-serif"
    ctx.fillText("Hello from Python!", 20, 140)

    ctx.fillStyle = "#888888"
    ctx.font = "14px monospace"
    ctx.fillText("napi-python + node-canvas", 20, 170)

    # Draw a circle using arc
    ctx.beginPath()
    ctx.arc(340, 60, 40, 0, 6.28318)  # 2*PI
    ctx.fillStyle = "#a855f7"  # Purple
    ctx.fill()

    print("  - Background filled")
    print("  - 3 colored rectangles drawn")
    print("  - Text rendered with 2 fonts")
    print("  - Circle drawn using arc path")

    # Export to PNG buffer
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


if __name__ == "__main__":
    main()
