---
title: Quick start
---

# Quick start

[Documentation](index.md) · [Architecture](architecture.md) · [Verification](verification.md)

For Live control, use macOS, Ableton Live 12.4 Intro, Python 3.10 or later and Codex with local MCP support. Put FFmpeg on the server's PATH to use the audio tools. The first-time steps assume you are inside a checkout of the implementation.

## Try the meter without Live

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
demo_dir="$(mktemp -d)"
python3 examples/synthetic_wav.py "$demo_dir/tone.wav"
.venv/bin/codex-ableton-bridge measure_main_render "{\"file\":\"$demo_dir/tone.wav\"}"
```

The six-second stereo sine wave has a sample peak near −12 dBFS. To run the excerpt analyzer, use `analyze_render` with the same JSON and optional `start` and `seconds` fields.

## Connect Live

1. Copy the `src/CodexAbletonBridge` folder into `Remote Scripts` under Live's current User Library. Create `Remote Scripts` if needed. [Ableton's installation instructions](https://help.ableton.com/hc/en-us/articles/209072009-Installing-third-party-remote-scripts)
2. Save your work and relaunch Live. In Settings, open **Tempo & MIDI** and select **CodexAbletonBridge** in one Control Surface slot. Set its MIDI input and output to **None**. Keep one instance of this Control Surface active at a time.
3. With the virtual environment already installed from the preceding section, register the server. Run the registration command from a terminal where `command -v ffmpeg` returns the executable path.

   ```sh
   codex mcp add codex-ableton-bridge \
     --env "PATH=$(dirname "$(command -v ffmpeg)"):$PATH" \
     -- "$PWD/.venv/bin/codex-ableton-bridge"
   ```

4. Start a fresh Codex chat. Open a disposable Set, confirm it is the active Set, then run `.venv/bin/codex-ableton-bridge tracks` for readback. Inspect tracks again in Codex before the first edit.

## Make a controlled edit

> In my disposable Set, list the tracks and inspect the top-level devices on the track named Test Audio. Append EQ Three there and show the resulting device and its parameter values.

For audio-informed edits, export the intended track from the same bars you will evaluate and provide the local path. Confirm the active Set before writing and inspect the target in Live whenever a write times out. To insert a prepared WAV, use a regular, empty Arrangement audio track in a stopped Set at constant tempo. Positions are zero-based quarter-note beats.

Add instruments such as Drift through Live's UI and use the bridge to inspect and adjust their exposed parameters. Import MIDI through Live. The bridge reports Live's parameter readback and clip position after a successful request.

## Measure the mix

In Arrangement View, select the comparison range. In Live's export dialog, choose **Main**, **WAV**, the Set's sample rate, **32-bit**, **No Dither** and **Normalize Off**. Repeat with the same range and settings for a comparison. Give Codex the local WAV paths and request `measure_main_render`. For before and after listening, level-match the two renders. [Ableton's export guide](https://www.ableton.com/en/live-manual/12/managing-files-and-sets/#exporting-audio-and-video)

To disconnect, select **None** in the Control Surface slot and run `codex mcp remove codex-ableton-bridge`.
