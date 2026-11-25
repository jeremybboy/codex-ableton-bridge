# Codex Ableton Bridge

Control selected Ableton Live edits from Codex and measure exported audio locally with FFmpeg.

[Quick start](docs/quickstart.md) · [Documentation](https://jeremybboy.github.io/codex-ableton-bridge/) · [Verification](docs/verification.md)

![Codex sends edit commands to Live through a local bridge. A Main WAV goes through a local analyzer for peak and loudness measurements.](docs/assets/repository-overview.svg)

A Python Control Surface applies supported edits to the active Set. When a mix decision calls for audio evidence, export the relevant track or Main output from Live and give Codex the local file path.

## What you can do

- Inspect tracks, Arrangement clips and top-level devices. Append selected stock effects and preview or set readable, enabled parameters.
- Place a prepared PCM WAV at a specified beat on a regular Arrangement audio track.
- Measure peak, RMS and approximate frequency bands on an excerpt. Scan a whole Main render for sample peak, true peak, headroom, integrated loudness and loudness range.

The Live workflow targets macOS and Ableton Live 12.4 Intro. [Verification](docs/verification.md) identifies the operations observed in the prototype and the tests for this package. The [offline example](docs/quickstart.md#try-the-meter-without-live) uses a generated WAV and needs no Live installation.

[Architecture](docs/architecture.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [MIT license](LICENSE)
