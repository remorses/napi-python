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

    def on_video_chunk(chunk):
        print(f"  [videoOutput] Got chunk: {chunk}")
        video_chunks.append(chunk)

    def on_audio_chunk(chunk):
        print(f"  [audioOutput] Got chunk: {chunk}")
        audio_chunks.append(chunk)

    def on_error(e):
        print(f"  [error] Demuxer error: {e}")

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

    print(f"Video chunks received: {len(video_chunks)}")
    print(f"Audio chunks received: {len(audio_chunks)}")

    print("\n=== Getting decoder config ===")
    config = demuxer.videoDecoderConfig
    print(f"Video decoder config: {config}")

    audio_config = demuxer.audioDecoderConfig
    print(f"Audio decoder config: {audio_config}")

    # Get track info
    print("\n=== Track info ===")
    try:
        tracks = demuxer.tracks
        print(f"Tracks: {tracks}")
    except Exception as e:
        print(f"Error getting tracks: {e}")

    try:
        duration = demuxer.duration
        print(f"Duration: {duration} microseconds")
    except Exception as e:
        print(f"Error getting duration: {e}")

    print("\n=== Demuxing packets ===")
    # Call demux() to extract packets and call callbacks
    # demux() can take an optional count argument
    print("Calling demux()...")
    demux_result = demuxer.demux()
    print(f"Demux result: {demux_result}")
    print(f"Video chunks after demux: {len(video_chunks)}")
    print(f"Audio chunks after demux: {len(audio_chunks)}")

    # Try demuxing in batches
    if not video_chunks:
        print("\nTrying demux(100)...")
        demux_result = demuxer.demux(100)
        print(f"Demux(100) result: {demux_result}")
        print(f"Video chunks: {len(video_chunks)}")
        print(f"Audio chunks: {len(audio_chunks)}")

    # Try calling demux until we get some chunks
    attempts = 0
    while not video_chunks and attempts < 5:
        attempts += 1
        print(f"\nDemux attempt {attempts}...")
        demux_result = demuxer.demux()
        print(
            f"Result: {demux_result}, video: {len(video_chunks)}, audio: {len(audio_chunks)}"
        )

    if config:
        print("\n=== Creating VideoDecoder ===")
        decoder = webcodecs.VideoDecoder(
            {
                "output": lambda frame: frames.append(frame),
                "error": lambda e: print(f"Decoder error: {e}"),
            }
        )
        print(f"Decoder created: {decoder}")

        print("Configuring decoder...")
        decoder.configure(config)

        print(f"Decoding {len(video_chunks)} chunks...")
        for i, chunk in enumerate(video_chunks[:10]):  # First 10 for testing
            decoder.decode(chunk)
            if i % 10 == 0:
                print(f"  Decoded chunk {i}")

        print("Flushing decoder...")
        flush_result = decoder.flush()
        if asyncio.isfuture(flush_result) or asyncio.iscoroutine(flush_result):
            flush_result = await flush_result

        print(f"Frames decoded: {len(frames)}")

    if frames:
        print("\n=== Creating VideoEncoder ===")
        encoder = webcodecs.VideoEncoder(
            {
                "output": lambda chunk, metadata: encoded_chunks.append(
                    (chunk, metadata)
                ),
                "error": lambda e: print(f"Encoder error: {e}"),
            }
        )
        print(f"Encoder created: {encoder}")

        # Configure encoder (H.264, same resolution as input)
        encoder.configure(
            {
                "codec": "avc1.42001f",
                "width": 1280,
                "height": 720,
                "bitrate": 1_000_000,
                "framerate": 30,
            }
        )

        print(f"Encoding {len(frames)} frames...")
        for i, frame in enumerate(frames[:10]):  # First 10 for testing
            encoder.encode(frame)
            if i % 10 == 0:
                print(f"  Encoded frame {i}")

        print("Flushing encoder...")
        flush_result = encoder.flush()
        if asyncio.isfuture(flush_result) or asyncio.iscoroutine(flush_result):
            flush_result = await flush_result

        print(f"Encoded chunks: {len(encoded_chunks)}")

    print("\n=== Summary ===")
    print(f"Video chunks: {len(video_chunks)}")
    print(f"Audio chunks: {len(audio_chunks)}")
    print(f"Frames: {len(frames)}")
    print(f"Encoded chunks: {len(encoded_chunks)}")


if __name__ == "__main__":
    asyncio.run(transcode())
