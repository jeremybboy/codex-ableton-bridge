"""Ableton Live entry point for the CodexAbletonBridge Control Surface."""
import json
import math
import time
import wave
from pathlib import Path

from .protocol import EFFECTS, inbox, write_json


def create_instance(c_instance):
    from _Framework.ControlSurface import ControlSurface

    class CodexAbletonBridge(ControlSurface):
        def __init__(self):
            super().__init__(c_instance)
            self.requests = inbox()
            self.log_message("CodexAbletonBridge ready")

        def update_display(self):
            super().update_display()
            for pending in sorted(self.requests.glob("*.request")):
                if self.process(pending):
                    break

        def process(self, pending):
            # Unlinking the request claims it before any edit. Another instance or
            # a timed-out caller can only cancel or claim it before that point.
            try:
                request = json.loads(pending.read_text(encoding="utf-8"))
                pending.unlink()
            except FileNotFoundError:
                return False
            except (ValueError, OSError):
                pending.unlink(missing_ok=True)
                return False

            if not isinstance(request, dict):
                return False
            expires = request.get("expires")
            if type(expires) not in (int, float) or not math.isfinite(expires) or expires <= time.time():
                return False
            try:
                response = dispatch(self.song(), request["action"], request["arguments"])
            except Exception as exc:
                response = {"error": str(exc) or type(exc).__name__}
            try:
                if time.time() < expires:
                    write_json(pending.with_suffix(".reply"), response)
            except OSError as exc:
                self.log_message("CodexAbletonBridge reply failed: %s" % exc)
            return True

    return CodexAbletonBridge()


def describe_device(device, slot):
    return {
        "slot": slot,
        "name": device.name,
        "class": device.class_name,
        "active": bool(device.is_active),
    }


def describe_parameter(parameter):
    result = {
        "name": parameter.name,
        "raw": parameter.value,
        "display": str(parameter),
        "min": parameter.min,
        "max": parameter.max,
        "writable": bool(parameter.is_enabled),
    }
    if parameter.is_quantized:
        result["choices"] = list(parameter.value_items)
    return result


def describe_clip(clip):
    return {"name": clip.name, "start_beat": clip.start_time, "end_beat": clip.end_time,
            "file": str(clip.file_path) if clip.is_audio_clip else None}


def dispatch(song, action, args):
    tracks = tuple(song.tracks) + tuple(song.return_tracks) + (song.master_track,)
    selected = song.view.selected_track
    if action == "tracks":
        return {"tracks": [
            {"slot": slot, "name": track.name, "selected": track == selected,
             "kind": "main" if track == song.master_track else
                     "return" if track in song.return_tracks else "track"}
            for slot, track in enumerate(tracks, 1)
        ], "available_effects": EFFECTS}

    slot = args["track_slot"]
    if type(slot) is not int or not 1 <= slot <= len(tracks) or tracks[slot - 1].name != args["track_name"]:
        raise ValueError("The track no longer matches. List tracks again before continuing.")
    track = tracks[slot - 1]
    result = {"track_slot": slot, "track_name": track.name}
    if action == "arrangement":
        result["clips"] = [describe_clip(clip) for clip in track.arrangement_clips]
        return result

    if action == "insert_wav":
        if track not in song.tracks or not track.has_audio_input:
            raise ValueError("A WAV needs a regular audio track.")
        if song.is_playing:
            raise ValueError("Stop playback before inserting an Arrangement clip.")
        start = args["start_beat"]
        if type(start) not in (float, int) or not math.isfinite(start) or start < 0:
            raise ValueError("Choose a finite nonnegative start beat.")
        path = Path(args["file"]).expanduser().resolve(strict=True)
        if not path.is_file() or path.suffix.lower() != ".wav":
            raise ValueError("Provide a local PCM WAV.")
        with wave.open(str(path), "rb") as source:
            duration = source.getnframes() / source.getframerate() * song.tempo / 60
        clips = tuple(track.arrangement_clips)
        if any(clip.start_time < start + duration - 0.00001 and clip.end_time > start + 0.00001
               for clip in clips):
            raise ValueError("The requested region overlaps a clip already on this track.")
        track.create_audio_clip(str(path), float(start))
        inserted = [clip for clip in track.arrangement_clips if clip not in clips]
        if len(inserted) != 1:
            raise RuntimeError("Live did not confirm one insertion. Inspect the arrangement before retrying.")
        clip = inserted[0]
        if clip.warping:
            clip.warping = False
        result["clip"] = describe_clip(clip)
        return result

    if action == "chain":
        result["devices"] = [describe_device(dev, i) for i, dev in enumerate(track.devices, 1)]
        return result

    if action == "add":
        effect = args["effect"]
        if effect not in EFFECTS:
            raise ValueError("Choose one of the supported stock effects: " + ", ".join(EFFECTS))
        count = len(track.devices)
        track.insert_device(effect)
        devices = tuple(track.devices)
        if len(devices) != count + 1:
            raise RuntimeError("Live did not confirm the insertion. Inspect the chain before retrying.")
        device = devices[-1]
        result["device"] = describe_device(device, count + 1)
        result["parameters"] = [describe_parameter(p) for p in device.parameters]
        return result

    devices = tuple(track.devices)
    index = args["device_slot"]
    if type(index) is not int or not 1 <= index <= len(devices) or devices[index - 1].name != args["device_name"]:
        raise ValueError("The device no longer matches. Inspect the chain again before continuing.")
    device = devices[index - 1]
    result["device"] = describe_device(device, index)
    if action == "parameters":
        result["parameters"] = [describe_parameter(p) for p in device.parameters]
        return result

    matches = [p for p in device.parameters if p.name == args["parameter"]]
    if len(matches) != 1:
        raise ValueError("Use a unique parameter name returned by the bridge.")
    parameter = matches[0]
    raw = args["raw"]
    if type(raw) not in (int, float) or not math.isfinite(raw) or not parameter.min <= raw <= parameter.max:
        raise ValueError("The requested value is outside this parameter's raw range.")
    if action == "preview":
        result["parameter"] = {"name": parameter.name, "raw": raw, "display": parameter.str_for_value(raw)}
        return result
    if action != "set":
        raise ValueError("Unknown action.")
    if not parameter.is_enabled or (parameter.is_quantized and raw != int(raw)):
        raise ValueError("This parameter is disabled or requires a valid integer choice.")
    if int(parameter.automation_state) != 0:
        raise ValueError("Live reports automation on this parameter. Edit it in Live to preserve intent.")
    parameter.value = raw
    result["parameter"] = describe_parameter(parameter)
    return result
