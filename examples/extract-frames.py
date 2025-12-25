#!/usr/bin/env python3
"""Demux MP4 video using napi-python with @napi-rs/webcodecs."""

import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from napi_python import load_addon

INPUT_VIDEO = os.path.join(os.path.dirname(__file__), "example.mp4")
ADDON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "node_modules/@napi-rs/webcodecs-darwin-arm64/webcodecs.darwin-arm64.node"
)


async def main():
    webcodecs = load_addon(ADDON_PATH)

    video_chunks = []
    audio_chunks = []

    demuxer = webcodecs.Mp4Demuxer({
        "videoOutput": lambda c: video_chunks.append(c),
        "audioOutput": lambda c: audio_chunks.append(c),
        "error": lambda e: print(f"Error: {e}"),
    })

    await demuxer.load(INPUT_VIDEO)

    duration = demuxer.duration / 1_000_000
    tracks = demuxer.tracks
    video_track = next((t for t in tracks if "codedWidth" in t), None)

    demuxer.demux()
    while demuxer.state == "demuxing":
        await asyncio.sleep(0.05)

    demuxer.close()

    print(f"Video: {INPUT_VIDEO}")
    print(f"Duration: {duration:.2f}s")
    if video_track:
        print(f"Resolution: {video_track['codedWidth']}x{video_track['codedHeight']}")
    print(f"Demuxed: {len(video_chunks)} video, {len(audio_chunks)} audio chunks")


if __name__ == "__main__":
    asyncio.run(main())
