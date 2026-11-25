# Repository instructions

This is a macOS-first bridge between a local Codex MCP server and Ableton Live 12.4. Audio measurements come from exported WAVs on the user's own machine.

- Keep a dedicated branch for every change. Inspect status and diffs, stage explicit paths, run the relevant checks, and open one PR. The human owner handles the merge. Agents must never merge, force-push, or commit or push directly to the default branch after bootstrap.
- Keep Ableton Sets, audio, MIDI exports, device presets, credentials, workstation paths, and screenshots with private data out of Git.
- Verify the target Set, track, and device before Live writes. Inspect the actual Set before retrying an operation with an uncertain result.
- State separately what was checked with an automated fixture and what was observed in Live. Keep render measurements and listening judgments distinct.
- Use the [documentation index](docs/index.md) to find the supported workflows and evidence.
