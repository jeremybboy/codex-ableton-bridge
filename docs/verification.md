---
title: Verification
---

# Verification

[Documentation](index.md) · [Quick start](quickstart.md) · [Architecture](architecture.md)

## Offline checks

The Python suite builds evidence using a generated PCM tone, silence, temporary request files and a stand-in for Live. It covers the MCP handshake and schema errors, request expiry and readback, private directory checks, rejected stale edit targets and overlap, and measured changes after a synthetic level increase. GitHub Actions installs the wheel and runs these checks on macOS and Ubuntu, and builds the public documentation.

## Earlier Live observation

One local run of the original prototype on Live 12.4 Intro observed stock EQ insertion and parameter readback, prepared WAVs placed at the requested matching beat, Drift inserted through Live's UI with parameters adjusted through the bridge, and MIDI imported through Live's menu. The prototype also analyzed a real unnormalized Main WAV. The recorded export read −7.38 dBFS sample peak, −7.2 dBTP true peak and −23 LUFS integrated loudness. Live's existing held Main peak read −7.38 dBFS. This is one local observation. The numerical readings establish measured signal levels for that export. Listening is a separate acceptance step.

## Packaged Live acceptance

The packaged Control Surface still needs a live pass. In a fresh disposable Set, install the MCP package and script from the same revision and complete these steps.

1. List tracks and confirm the active Set. Append EQ Three to a test audio track, inspect the readback, change one enabled parameter, and verify the displayed value in Live.
2. Insert the generated PCM fixture at the same beat on two empty test tracks. Confirm start, end and Warp Off. Attempt the same placement again on an occupied track and verify that the existing clip remains in place.
3. Add Drift in Live. Preview and adjust an exposed parameter with the bridge. Import a synthetic MIDI clip through Live's menu if checking the combined instrument workflow.
4. Export Main before and after a known level change using matched render settings and range. Compare the meter results and listen to the level-matched renders independently.
5. Check Live's Undo for each tested mutation before documenting its behavior. Record Live edition, build and OS along with each result.

Report any divergence or ambiguous write with the exact step and synthetic reproduction. Use a disposable Set for retries.
