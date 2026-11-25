# Contributing

Open a pull request against `main` from a focused branch. Include the affected entry point, the checks you ran and any verification still needed in Live. The maintainer reviews and merges changes.

Install the checkout in a virtual environment with `python -m pip install .`, then run `python -m unittest discover -s tests -v` with FFmpeg on PATH. Generate test media at runtime, for example with `examples/synthetic_wav.py`. Use a fresh disposable Set for any Live test and keep Sets, media, presets, credentials and workstation details out of issues and pull requests.

Read the [code of conduct](CODE_OF_CONDUCT.md) and [architecture](docs/architecture.md) before contributing.
