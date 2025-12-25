"""Test loading @napi-rs/webcodecs addon."""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from napi_python import load_addon

# Find the webcodecs .node file
addon_path = (
    Path(__file__).parent.parent
    / "node_modules"
    / "@napi-rs"
    / "webcodecs-darwin-arm64"
    / "webcodecs.darwin-arm64.node"
)

print(f"Loading webcodecs from: {addon_path}")
print(f"Exists: {addon_path.exists()}")

if not addon_path.exists():
    print("Webcodecs addon not found. Run: npm install @napi-rs/webcodecs")
    sys.exit(1)

try:
    webcodecs = load_addon(str(addon_path))
    print(f"\nWebcodecs loaded successfully!")
    print(f"Exports: {len(dir(webcodecs))} items")

    # Try to access some exports
    print("\n=== Checking key exports ===")
    key_exports = [
        "VideoEncoder",
        "VideoDecoder",
        "AudioEncoder",
        "AudioDecoder",
        "ImageDecoder",
        "Mp4Demuxer",
        "Mp4Muxer",
        "VideoFrame",
    ]
    for name in key_exports:
        try:
            val = getattr(webcodecs, name)
            print(f"  {name}: {type(val).__name__}")
        except Exception as e:
            print(f"  {name}: ERROR - {e}")

    # Check hardware accelerators
    print("\n=== Hardware Accelerators ===")
    try:
        accelerators = webcodecs.getHardwareAccelerators()
        print(f"  Available: {accelerators}")
    except Exception as e:
        print(f"  Error: {e}")

    # Try to get preferred hardware accelerator
    try:
        preferred = webcodecs.getPreferredHardwareAccelerator()
        print(f"  Preferred: {preferred}")
    except Exception as e:
        print(f"  Error getting preferred: {e}")

    print("\n=== Webcodecs addon loaded and working! ===")

except Exception as e:
    print(f"\nError loading addon: {e}")
    import traceback

    traceback.print_exc()
