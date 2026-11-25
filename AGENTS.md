# Repository instructions

This repository packages a macOS-first bridge between a local Codex MCP server and Ableton Live. FFmpeg measures exported audio locally.

- Keep a dedicated branch for every change. Inspect status and diffs, stage explicit paths, run the relevant checks, and open one PR. The human owner handles the merge. Agents must never merge, force-push, or commit or push directly to the default branch after bootstrap.
- Keep Ableton Sets, audio, MIDI exports, device presets, credentials, workstation paths, and screenshots with private data out of Git.
- Verify the active Set, track, and device before Live writes. Inspect the target in Live before retrying an operation with an uncertain result.
- Keep the two-process protocol in `src/CodexAbletonBridge/protocol.py`. The Live script must load without third-party Python dependencies. The package and installed script must use compatible message formats.
- Use `python -m pip install .` and `python -m unittest discover -s tests -v` with FFmpeg on PATH. Tests use synthetic data and a stand-in for Live. Never run acceptance against a user's working Set.
- Record automated and Live observations independently. Describe render measurements and listening as distinct evidence. Start with the [documentation index](docs/index.md).
