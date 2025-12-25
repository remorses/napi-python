# original repo https://github.com/Brooooooklyn/webcodecs-node
"""Video transcoding example using @napi-rs/webcodecs."""

import sys
import asyncio
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

if not addon_path.exists():
    print("Webcodecs addon not found. Run: npm install @napi-rs/webcodecs")
    sys.exit(1)

webcodecs = load_addon(str(addon_path))
print(f"Webcodecs loaded: {len(dir(webcodecs))} exports")

# Input file
input_file = Path(__file__).parent / "example.mp4"
output_file = Path(__file__).parent / "output.mp4"

print(f"\nInput: {input_file}")
print(f"Output: {output_file}")

if not input_file.exists():
    print("Input file not found!")
    sys.exit(1)


async def transcode():
    # Collect video chunks and frames
    video_chunks = []
    audio_chunks = []
    frames = []
    encoded_chunks = []
    errors = []

    def on_video_chunk(chunk):
        video_chunks.append(chunk)

    def on_audio_chunk(chunk):
        audio_chunks.append(chunk)

    def on_error(e):
        errors.append(str(e))
        print(f"  [error] {e}")

    print("\n=== Creating Mp4Demuxer ===")
    demuxer = webcodecs.Mp4Demuxer(
        {
            "videoOutput": on_video_chunk,
            "audioOutput": on_audio_chunk,
            "error": on_error,
        }
    )
    print(f"Demuxer created: {demuxer}")

    print("\n=== Loading video file ===")
    result = demuxer.load(str(input_file))
    print(f"Load result type: {type(result)}")

    if asyncio.isfuture(result) or asyncio.iscoroutine(result):
        print("Awaiting load...")
        result = await result
        print(f"Load completed: {result}")

    print(f"State after load: {demuxer.state}")

    print("\n=== Getting decoder config ===")
    config = demuxer.videoDecoderConfig
    print(f"Video decoder config: {config}")

    audio_config = demuxer.audioDecoderConfig
    print(f"Audio decoder config: {audio_config}")

    # Get track info
    print("\n=== Track info ===")
    tracks = demuxer.tracks
    print(f"Tracks: {tracks}")

    duration = demuxer.duration
    print(f"Duration: {duration} microseconds ({duration / 1000000:.2f}s)")

    print("\n=== Demuxing all packets ===")
    # Call demux() to extract all packets
    # demux() spawns a thread and returns immediately
    # Callbacks are invoked asynchronously
    print("Calling demux()...")
    demuxer.demux()

    # Wait for demuxing to complete
    print("Waiting for demux to complete...")
    while demuxer.state == "demuxing":
        await asyncio.sleep(0.1)

    print(f"Final state: {demuxer.state}")
    print(f"Video chunks received: {len(video_chunks)}")
    print(f"Audio chunks received: {len(audio_chunks)}")
    if errors:
        print(f"Errors encountered: {len(errors)}")

    # Note: The chunks are External objects containing native pointers
    # In a full implementation, you would need to decode these using VideoDecoder/AudioDecoder
    # For now, we just count them to verify the demuxing works

    if video_chunks:
        print(f"\nFirst video chunk: {video_chunks[0]}")
        print(f"Last video chunk: {video_chunks[-1]}")

    if audio_chunks:
        print(f"\nFirst audio chunk: {audio_chunks[0]}")
        print(f"Last audio chunk: {audio_chunks[-1]}")

    print("\n=== Summary ===")
    print(f"Video chunks: {len(video_chunks)}")
    print(f"Audio chunks: {len(audio_chunks)}")
    print(f"Frames decoded: {len(frames)}")
    print(f"Encoded chunks: {len(encoded_chunks)}")


if __name__ == "__main__":
    asyncio.run(transcode())
