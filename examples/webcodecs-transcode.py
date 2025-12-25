# original repo https://github.com/Brooooooklyn/webcodecs-node
"""
Webcodecs demuxing example using @napi-rs/webcodecs.

This example demonstrates what currently works with napi-python:
- Loading MP4 files
- Getting track info, duration, decoder configs
- Demuxing video and audio packets via TSFN callbacks

Current limitations:
- Demuxed chunks are External pointers (not full EncodedVideoChunk objects)
- VideoEncoder/AudioEncoder don't work yet (configure doesn't apply)
- Muxing to new files isn't possible without proper chunk objects

The TSFN (ThreadSafe Function) callbacks work, but the native code doesn't
call back into NAPI to create proper JavaScript objects. This is because
the addon detects it's not running in a real Node.js/V8 environment.
"""

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

print(f"\nInput: {input_file}")

if not input_file.exists():
    print("Input file not found!")
    sys.exit(1)


async def demux_example():
    """Demonstrate MP4 demuxing capabilities."""
    
    # Counters for received chunks
    video_chunks = []
    audio_chunks = []
    errors = []

    def on_video_chunk(chunk):
        video_chunks.append(chunk)

    def on_audio_chunk(chunk):
        audio_chunks.append(chunk)

    def on_error(e):
        errors.append(str(e))

    print("\n=== Creating Mp4Demuxer ===")
    demuxer = webcodecs.Mp4Demuxer({
        "videoOutput": on_video_chunk,
        "audioOutput": on_audio_chunk,
        "error": on_error,
    })
    print(f"Demuxer created, state: {demuxer.state}")

    print("\n=== Loading video file ===")
    await demuxer.load(str(input_file))
    print(f"State after load: {demuxer.state}")

    print("\n=== File Information ===")
    duration_us = demuxer.duration
    duration_s = duration_us / 1_000_000 if duration_us else 0
    print(f"Duration: {duration_us} µs ({duration_s:.2f}s)")
    
    tracks = demuxer.tracks
    print(f"Tracks: {len(tracks)}")
    for i, track in enumerate(tracks):
        track_type = track.get('trackType', 'unknown')
        if 'codedWidth' in track:
            print(f"  Track {i}: {track_type} - {track['codedWidth']}x{track['codedHeight']}")
        elif 'sampleRate' in track:
            print(f"  Track {i}: {track_type} - {track['sampleRate']}Hz, {track['numberOfChannels']}ch")

    print("\n=== Decoder Configurations ===")
    video_config = demuxer.videoDecoderConfig
    if video_config:
        print(f"Video: {video_config}")
    
    audio_config = demuxer.audioDecoderConfig
    if audio_config:
        print(f"Audio: {audio_config}")

    print("\n=== Demuxing all packets ===")
    print("Starting demux...")
    demuxer.demux()
    
    # Wait for demuxing to complete
    while demuxer.state == "demuxing":
        await asyncio.sleep(0.1)
    
    print(f"Final state: {demuxer.state}")

    print("\n=== Results ===")
    print(f"Video chunks received: {len(video_chunks)}")
    print(f"Audio chunks received: {len(audio_chunks)}")
    print(f"Total chunks: {len(video_chunks) + len(audio_chunks)}")
    
    if errors:
        print(f"Errors: {len(errors)}")
        for e in errors[:3]:  # Show first 3
            print(f"  - {e}")
    
    # Show chunk info (they are External pointers, not full chunk objects)
    if video_chunks:
        print(f"\nNote: Chunks are {type(video_chunks[0]).__name__} objects (native pointers)")
        print("Full EncodedVideoChunk/EncodedAudioChunk objects require")
        print("native NAPI callback support which isn't available outside Node.js")

    demuxer.close()
    print("\nDemuxer closed.")


if __name__ == "__main__":
    asyncio.run(demux_example())
