"""Measure local audio renders using FFmpeg."""
import math
import re
import shutil
import subprocess
from pathlib import Path

AUDIO_FORMATS = {".wav": "wav", ".aif": "aiff", ".aiff": "aiff", ".flac": "flac"}
BANDS = (
    ("20-60 Hz", 20, 60),
    ("60-150 Hz", 60, 150),
    ("150-350 Hz", 150, 350),
    ("350-900 Hz", 350, 900),
    ("900-2500 Hz", 900, 2500),
    ("2500-6500 Hz", 2500, 6500),
    ("6500-16000 Hz", 6500, 16000),
)


def db_field(stderr, key):
    match = re.search(r"\b" + key + r":\s+(-?\d+(?:\.\d+)?|-?inf)\b", stderr)
    if not match:
        return None
    value = float(match[1])
    return round(value, 2) if math.isfinite(value) else None


def audio_path(file):
    path = Path(file).expanduser().resolve(strict=True)
    if not path.is_file() or path.suffix.lower() not in AUDIO_FORMATS:
        raise ValueError("Use a local WAV, AIFF or FLAC rendered from the target track.")
    return path


def ffmpeg_input(path, *options):
    executable = shutil.which("ffmpeg")
    if not executable:
        raise RuntimeError("Install FFmpeg and make it available on the server's PATH.")
    return [
        executable, "-nostdin", "-hide_banner", *options, "-protocol_whitelist", "file",
        "-f", AUDIO_FORMATS[path.suffix.lower()], "-i", str(path),
    ]


def measure_main_render(file):
    """Scan an entire render using FFmpeg's EBU R128 and oversampled peak meters."""
    path = audio_path(file)
    command = [
        *ffmpeg_input(path),
        "-map", "0:a:0", "-af", "ebur128=peak=sample+true:framelog=verbose", "-f", "null", "-",
    ]
    try:
        process = subprocess.run(command, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("The Main render did not finish measuring within two minutes.") from exc
    summary = re.split(r"\bSummary:\s*\n", process.stderr, maxsplit=1)[-1]
    sample = re.search(r"Sample peak:\s+Peak:\s+(-?\d+(?:\.\d+)?|-?inf)", summary)
    true = re.search(r"True peak:\s+Peak:\s+(-?\d+(?:\.\d+)?|-?inf)", summary)
    if process.returncode or sample is None or true is None:
        raise RuntimeError("FFmpeg could not measure the local Main render.")
    peak_dbfs, true_peak_dbtp = float(sample[1]), float(true[1])
    if not math.isfinite(peak_dbfs) or not math.isfinite(true_peak_dbtp):
        raise ValueError("The render has no measurable audio. Check its track and render range.")
    integrated = db_field(summary, "I")
    if integrated is None or integrated <= -70:
        raise ValueError("Integrated loudness is below the meter's gate.")
    return {
        "render": path.name,
        "sample_peak_dbfs": peak_dbfs,
        "true_peak_dbtp": true_peak_dbtp,
        "true_peak_headroom_db": round(-true_peak_dbtp, 1),
        "integrated_loudness_lufs": integrated,
        "loudness_range_lu": db_field(summary, "LRA"),
        "method": "Whole-file EBU R128 measurement. Use a Main render with Normalize off for gain staging.",
    }


def analyze(file, start=0, seconds=20):
    path = audio_path(file)
    if not math.isfinite(start) or start < 0 or not math.isfinite(seconds) or not 2 <= seconds <= 60:
        raise ValueError("Choose a nonnegative start and a length of 2 to 60 seconds.")
    branches = ["[b0]astats=metadata=0[out0]"]
    for i, (_, low, high) in enumerate(BANDS, 1):
        branches.append("[b%d]highpass=f=%d,lowpass=f=%d,astats=metadata=0[out%d]" % (i, low, high, i))
    fan_out = "[0:a:0]asplit=%d%s" % (len(branches), "".join("[b%d]" % i for i in range(len(branches))))
    graph = ";".join([fan_out] + branches)
    command = ffmpeg_input(path, "-ss", str(start), "-t", str(seconds))
    command.extend(["-filter_complex", graph])
    for i in range(len(branches)):
        command.extend(["-map", "[out%d]" % i])
    process = subprocess.run(command + ["-f", "null", "-"], capture_output=True, text=True, timeout=30)
    if process.returncode:
        raise RuntimeError("ffmpeg could not decode the requested audio excerpt.")

    stats = {}
    for component, summary in re.findall(
        r"\[(Parsed_astats_\d+) @ [^\]]+\] Overall\s*\n((?:\[\1 @ [^\]]+\][^\n]*\n?)+)",
        process.stderr,
    ):
        stats[int(component.rsplit("_", 1)[1])] = summary
    summaries = [stats[key] for key in sorted(stats)]
    if len(summaries) != len(branches):
        raise RuntimeError("Could not read all audio measurements from ffmpeg.")

    overall = summaries[0]
    samples = db_field(overall, "Number of samples")
    if not samples:
        raise ValueError("The rendered excerpt contains no audio samples at that offset.")
    rms = db_field(overall, "RMS level dB")
    peak = db_field(overall, "Peak level dB")
    return {
        "render": path.name,
        "start_seconds": start,
        "requested_seconds": seconds,
        "peak_dbfs": peak,
        "rms_dbfs": rms,
        "peak_to_rms_db": round(peak - rms, 2) if peak is not None and rms is not None else None,
        "near_silence": rms is None or rms < -70,
        "approximate_band_rms_dbfs": {
            label: db_field(summary, "RMS level dB")
            for (label, _, _), summary in zip(BANDS, summaries[1:])
        },
        "interpretation": "Post-fader excerpt measurements. Compare bands in context of the source and request. "
                          "Bands overlap and a loud band alone does not establish a mixing problem.",
    }
