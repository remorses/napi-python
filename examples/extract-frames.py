#!/usr/bin/env python3
"""
Extract video frames as PNG files.

This example demonstrates:
1. Using @napi-rs/webcodecs to get video metadata
2. Using ffmpeg to extract and save frames as PNG

The webcodecs addon successfully demuxes the video, but the chunks are
native pointers. For actual frame extraction, we use ffmpeg which can
decode the video properly.
"""

import sys
import asyncio
import subprocess
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from napi_python import load_addon

# Configuration
NUM_FRAMES = 5
OUTPUT_DIR = Path(__file__).parent / "frames"

# Find the webcodecs .node file
addon_path = (
    Path(__file__).parent.parent
    / "node_modules"
    / "@napi-rs"
    / "webcodecs-darwin-arm64"
    / "webcodecs.darwin-arm64.node"
)

if not addon_path.exists():
    print("Webcodecs addon not found. Run: npm install @napi-rs/webcodecs")
    sys.exit(1)

# Input file
input_file = Path(__file__).parent / "example.mp4"

if not input_file.exists():
    print(f"Input file not found: {input_file}")
    sys.exit(1)


async def get_video_info():
    """Get video information using webcodecs addon."""
    webcodecs = load_addon(str(addon_path))
    
    demuxer = webcodecs.Mp4Demuxer({
        "videoOutput": lambda c: None,
        "audioOutput": lambda c: None,
        "error": lambda e: None,
    })
    
    await demuxer.load(str(input_file))
    
    info = {
        "duration_us": demuxer.duration,
        "duration_s": demuxer.duration / 1_000_000 if demuxer.duration else 0,
        "tracks": demuxer.tracks,
        "video_config": demuxer.videoDecoderConfig,
        "audio_config": demuxer.audioDecoderConfig,
    }
    
    # Count chunks
    video_count = 0
    audio_count = 0
    
    def count_video(c):
        nonlocal video_count
        video_count += 1
    
    def count_audio(c):
        nonlocal audio_count
        audio_count += 1
    
    # Create new demuxer to count
    demuxer2 = webcodecs.Mp4Demuxer({
        "videoOutput": count_video,
        "audioOutput": count_audio,
        "error": lambda e: None,
    })
    
    await demuxer2.load(str(input_file))
    demuxer2.demux()
    
    while demuxer2.state == "demuxing":
        await asyncio.sleep(0.05)
    
    info["video_chunks"] = video_count
    info["audio_chunks"] = audio_count
    
    demuxer.close()
    demuxer2.close()
    
    return info


def extract_frames_with_ffmpeg(input_path: Path, output_dir: Path, num_frames: int):
    """Extract frames using ffmpeg."""
    output_dir.mkdir(exist_ok=True)
    
    # Use ffmpeg to extract first N frames as PNG
    # -vf "select=lt(n\,N)" selects first N frames
    # -vsync vfr handles variable frame rate
    output_pattern = str(output_dir / "frame_%03d.png")
    
    cmd = [
        "ffmpeg",
        "-i", str(input_path),
        "-vf", f"select=lt(n\\,{num_frames})",
        "-vsync", "vfr",
        "-y",  # Overwrite existing files
        output_pattern
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"ffmpeg error: {result.stderr}")
        return []
    
    # Find created files
    frames = sorted(output_dir.glob("frame_*.png"))
    return frames


def main():
    print("=" * 60)
    print("Video Frame Extractor")
    print("=" * 60)
    print(f"\nInput: {input_file}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Frames to extract: {NUM_FRAMES}")
    
    # Get video info using webcodecs
    print("\n--- Video Info (via @napi-rs/webcodecs) ---")
    info = asyncio.run(get_video_info())
    
    print(f"Duration: {info['duration_s']:.2f} seconds")
    print(f"Tracks: {len(info['tracks'])}")
    
    for track in info['tracks']:
        if 'codedWidth' in track:
            print(f"  Video: {track['codedWidth']}x{track['codedHeight']}")
        elif 'sampleRate' in track:
            print(f"  Audio: {track['sampleRate']}Hz, {track['numberOfChannels']}ch")
    
    print(f"Video chunks (demuxed): {info['video_chunks']}")
    print(f"Audio chunks (demuxed): {info['audio_chunks']}")
    
    # Extract frames using ffmpeg
    print("\n--- Extracting Frames (via ffmpeg) ---")
    frames = extract_frames_with_ffmpeg(input_file, OUTPUT_DIR, NUM_FRAMES)
    
    if frames:
        print(f"Extracted {len(frames)} frames:")
        for frame in frames:
            size = frame.stat().st_size
            print(f"  {frame.name} ({size:,} bytes)")
        
        print(f"\nFrames saved to: {OUTPUT_DIR}")
    else:
        print("No frames extracted!")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
