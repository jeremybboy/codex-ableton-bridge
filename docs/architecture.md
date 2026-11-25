---
title: Architecture
---

# Architecture

[Documentation](index.md) · [Quick start](quickstart.md) · [Verification](verification.md)

Codex launches the Python package as a newline-delimited JSON-RPC server on stdin and stdout. It exposes the MCP handshake, ping, tool listing and tool calls. Live loads the separately installed `CodexAbletonBridge` script and performs edits through its Control Surface callback. Both components use the same protocol source.

For Live operations, the server writes an expiring JSON request into a per-user directory under `/tmp`. The directory must be owned by that user and inaccessible to group and other users. Live claims a request by removing it before dispatch, then writes the reply atomically. Install the Live script and the MCP package from the same revision.

Live writes target the active Set and check track and device names against their slots. The user must confirm the Set and keep a single bridge Control Surface active. Same-user local processes and the Control Surface installation share the trust boundary. An expired request is discarded before dispatch. A timed-out request that Live already claimed may still have changed the Set, so inspect Live before retrying. Saving and Undo remain in Live.

| Tools | Operation |
| --- | --- |
| `tracks`, `arrangement`, `chain` | Inspect regular tracks, returns, Main and the available clip or device data. |
| `add` | Append EQ Three, Auto Filter, Reverb, Delay, Compressor or Utility where Live can insert it. |
| `parameters`, `preview`, `set` | Inspect top-level device parameters and preview or write supported raw settings. The writer rejects active automation, disabled parameters and fractional quantized settings. |
| `insert_wav` | Insert a prepared PCM WAV into Arrangement View and request Warp Off. Use a stopped, constant-tempo Set and verify both clip boundaries in Live. |
| `analyze_render` | Measure a short local excerpt and return peak, RMS and approximate band levels. |
| `measure_main_render` | Scan an exported file with FFmpeg's EBU R128 filter for integrated loudness, loudness range and peak metrics. |

Audio tools read supported local WAV, AIFF and FLAC files using FFmpeg. Audio passes directly from the local file to FFmpeg. Responses return measurement values through the configured MCP client. FFmpeg determines the reported precision. Loudness range needs a representative duration and can be unstable on short files. Absolute source paths can appear in local arrangement readback, and the client's own data handling applies to tool responses. [FFmpeg's EBU R128 filter](https://ffmpeg.org/ffmpeg-filters.html#ebur128)
