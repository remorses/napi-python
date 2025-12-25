# WebCodecs Example Plan

Use `@napi-rs/webcodecs` addon to demonstrate Python loading a real-world napi-rs package.

## Package Capabilities

```
@napi-rs/webcodecs
├── Video: H.264, H.265, VP8, VP9, AV1 (encode/decode)
├── Audio: AAC, Opus, MP3, FLAC (encode/decode)
├── Containers: Mp4Demuxer, Mp4Muxer, WebMDemuxer, WebMMuxer
└── Images: JPEG, PNG, WebP, GIF, AVIF, JPEG XL decode
```

## Target Example: MP4 Transcode

Full pipeline demonstrating demux → decode → encode → mux:

```
┌─────────────┐     ┌────────────┐     ┌──────────────┐     ┌─────────────┐
│ input.mp4   │ ──▶ │ Mp4Demuxer │ ──▶ │ VideoDecoder │ ──▶ │ VideoFrame  │
└─────────────┘     └────────────┘     └──────────────┘     └─────────────┘
                                                                   │
                                                                   ▼
┌─────────────┐     ┌────────────┐     ┌──────────────┐     ┌─────────────┐
│ output.mp4  │ ◀── │ Mp4Muxer   │ ◀── │ VideoEncoder │ ◀── │ (process)   │
└─────────────┘     └────────────┘     └──────────────┘     └─────────────┘
```

## Python API Usage

```python
from napi_python import load_addon

webcodecs = load_addon("webcodecs.darwin-arm64.node")

# Demux
demuxer = webcodecs.Mp4Demuxer({
    "videoOutput": lambda chunk: decoder.decode(chunk),
    "error": lambda e: print(f"Error: {e}")
})
await demuxer.load("./input.mp4")

# Decode
decoder = webcodecs.VideoDecoder({
    "output": lambda frame: encode_frame(frame),
    "error": lambda e: print(f"Error: {e}")
})
decoder.configure(demuxer.videoDecoderConfig)

# Encode 
encoder = webcodecs.VideoEncoder({
    "output": lambda chunk, meta: muxer.addVideoChunk(chunk, meta),
    "error": lambda e: print(f"Error: {e}")
})
encoder.configure({
    "codec": "avc1.42001E",
    "width": 1920,
    "height": 1080,
    "bitrate": 5_000_000
})

# Mux
muxer = webcodecs.Mp4Muxer({"fastStart": True})
muxer.addVideoTrack({"codec": "avc1.42001E", "width": 1920, "height": 1080})

# Run pipeline
demuxer.demux()
await encoder.flush()

# Output
data = muxer.finalize()
with open("output.mp4", "wb") as f:
    f.write(bytes(data))
```

## Required NAPI Features - Implementation Status

### Priority 1 - TypedArrays/Buffers ✅ IMPLEMENTED

Video data flows through `Uint8Array` and `ArrayBuffer`:

| Function | Status | Notes |
|----------|--------|-------|
| `napi_create_arraybuffer` | ✅ Done | Creates ArrayBuffer with raw pointer |
| `napi_get_arraybuffer_info` | ✅ Done | Returns data pointer and length |
| `napi_create_typedarray` | ✅ Done | All types (Int8-BigUint64) |
| `napi_get_typedarray_info` | ✅ Done | Type, length, data, buffer, offset |
| `napi_is_typedarray` | ✅ Done | Type check |
| `napi_is_arraybuffer` | ✅ Done | Type check |
| `napi_is_dataview` | ✅ Done | Type check |
| `napi_create_dataview` | ✅ Done | Low-level buffer access |
| `napi_get_dataview_info` | ✅ Done | DataView info extraction |
| `napi_detach_arraybuffer` | ✅ Done | Detach buffer |
| `napi_is_detached_arraybuffer` | ✅ Done | Check detached state |

### Priority 2 - Buffer (Node.js) ✅ IMPLEMENTED

| Function | Status | Notes |
|----------|--------|-------|
| `napi_create_buffer` | ✅ Done | Creates Uint8Array-backed buffer |
| `napi_create_buffer_copy` | ✅ Done | Copy data to new buffer |
| `napi_get_buffer_info` | ✅ Done | Get buffer data/length |
| `napi_is_buffer` | ✅ Done | Type check |

### Priority 3 - Error Handling ✅ IMPLEMENTED

| Function | Status | Notes |
|----------|--------|-------|
| `napi_throw` | ✅ Done | Throw exception value |
| `napi_throw_error` | ✅ Done | Throw Error with message |
| `napi_throw_type_error` | ✅ Done | Throw TypeError |
| `napi_throw_range_error` | ✅ Done | Throw ValueError |
| `napi_is_exception_pending` | ✅ Done | Check pending exception |
| `napi_get_and_clear_last_exception` | ✅ Done | Get and clear exception |
| `napi_create_error` | ✅ Done | Create Error object |
| `napi_create_type_error` | ✅ Done | Create TypeError |
| `napi_create_range_error` | ✅ Done | Create ValueError |

### Priority 4 - External Values ✅ IMPLEMENTED

| Function | Status | Notes |
|----------|--------|-------|
| `napi_create_external` | ✅ Done | Opaque pointer wrapper |
| `napi_get_value_external` | ✅ Done | Get pointer from external |

## New Files Created

- `napi_python/_values/arraybuffer.py` - ArrayBuffer, TypedArray, DataView classes

## Test Strategy

1. Start with `ImageDecoder` - simplest API
2. Move to `VideoEncoder` with generated frames
3. Full transcode pipeline

## Next Steps

1. **Install webcodecs package**: `npm install @napi-rs/webcodecs`
2. **Create image decode example**: `examples/webcodecs-image.py`
3. **Test with real addon**: Load and call ImageDecoder
4. **Debug any missing functions**: Add as needed

## Files to Create

- `examples/webcodecs-transcode.py` - Main example
- `examples/webcodecs-image.py` - Simpler image decode example
