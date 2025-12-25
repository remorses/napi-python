#!/usr/bin/env python3
"""Use node-canvas native addon directly from Python via napi-python."""

from napi_python import load_addon

# Load the native canvas addon (npm install canvas)
canvas = load_addon("node_modules/canvas/build/Release/canvas.node")

# Create canvas and 2D context - same API as browser/Node.js
c = canvas.Canvas(400, 200)
ctx = canvas.CanvasRenderingContext2d(c)

# Draw background
ctx.fillStyle = "#1a1a2e"
ctx.fillRect(0, 0, 400, 200)

# Draw colored shapes
for i, color in enumerate(["#ff6b6b", "#4ecdc4", "#ffe66d"]):
    ctx.fillStyle = color
    ctx.fillRect(20 + i * 100, 20, 80, 80)

# Draw circle
ctx.beginPath()
ctx.arc(340, 60, 40, 0, 6.283)
ctx.fillStyle = "#a855f7"
ctx.fill()

# Draw text
ctx.fillStyle = "#ffffff"
ctx.font = "24px sans-serif"
ctx.fillText("Hello from Python!", 20, 140)

ctx.fillStyle = "#666666"
ctx.font = "14px monospace"
ctx.fillText("napi-python + node-canvas", 20, 170)

# Export to PNG
with open("examples/canvas-output.png", "wb") as f:
    f.write(bytes(c.toBuffer()))

print("saved canvas-output.png")
