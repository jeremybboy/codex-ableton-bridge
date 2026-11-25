import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import CodexAbletonBridge as surface
from CodexAbletonBridge.protocol import inbox, write_json
from codex_ableton_bridge import server
from examples.synthetic_wav import write_wav


class StdioTests(unittest.TestCase):
    def test_stdio_recovers_from_bad_input_and_exposes_tools(self):
        messages = [
            "{",
            "[]",
            '{"jsonrpc":"2.0","id":NaN,"method":"ping"}',
            {"id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}},
            {"method": "notifications/initialized"},
            {"id": 2, "method": "tools/list"},
            {"id": 3, "method": "tools/call", "params": {"name": "insert_wav", "arguments": {}}},
            {"id": 4, "method": "ping"},
        ]
        lines = [value if isinstance(value, str) else json.dumps({"jsonrpc": "2.0", **value})
                 for value in messages]
        result = subprocess.run(
            [sys.executable, "-m", "codex_ableton_bridge.server"], input="\n".join(lines) + "\n",
            capture_output=True, text=True, check=True, timeout=15,
        )
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(responses), 7)
        self.assertEqual([item["error"]["code"] for item in responses[:3]], [-32700, -32600, -32600])
        self.assertEqual(responses[3]["result"]["protocolVersion"], "2025-11-25")
        names = {entry["name"] for entry in responses[4]["result"]["tools"]}
        self.assertTrue({"tracks", "insert_wav", "measure_main_render"} <= names)
        self.assertTrue(responses[5]["result"]["isError"])
        self.assertEqual(responses[6]["result"], {})

    def test_invalid_slots_never_reach_the_inbox(self):
        for slot in (True, 1.5, 0, "1"):
            with self.subTest(slot=slot), patch.object(server, "inbox") as open_inbox:
                with self.assertRaises(ValueError):
                    server.call("chain", {"track_slot": slot, "track_name": "Audio"})
                open_inbox.assert_not_called()


@unittest.skipUnless(hasattr(os, "getuid"), "POSIX request directory required")
class RequestTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.base = Path(directory.name)
        self.folder = inbox(self.base)

    def test_rejects_nonprivate_directories_and_symlinks(self):
        self.folder.chmod(0o755)
        with self.assertRaises(RuntimeError):
            inbox(self.base)
        self.folder.rmdir()
        other = self.base / "other"
        other.mkdir(mode=0o700)
        self.folder.symlink_to(other, target_is_directory=True)
        with self.assertRaises(RuntimeError):
            inbox(self.base)

    def test_surface_reads_request_once_and_returns_readback(self):
        song = SimpleNamespace(tracks=(), return_tracks=(), master_track=SimpleNamespace(name="Main"))
        song.view = SimpleNamespace(selected_track=song.master_track)

        class ControlSurface:
            def __init__(self, instance):
                self.instance = instance

            def song(self):
                return self.instance

            def log_message(self, message):
                pass

        framework = SimpleNamespace(ControlSurface=ControlSurface)
        with patch.dict(sys.modules, {"_Framework.ControlSurface": framework}), \
                patch.object(surface, "inbox", return_value=self.folder), \
                patch.object(server, "inbox", return_value=self.folder):
            live = surface.create_instance(song)
            expired = self.folder / "expired.request"
            write_json(expired, {"action": "tracks", "arguments": {}, "expires": time.time() - 1})
            self.assertFalse(live.process(expired))
            self.assertFalse(expired.with_suffix(".reply").exists())
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(server.call, "tracks", {})
                deadline = time.monotonic() + 3
                while not (pending := next(self.folder.glob("*.request"), None)):
                    if time.monotonic() >= deadline:
                        self.fail("The client never wrote a request.")
                    time.sleep(0.01)
                self.assertTrue(live.process(pending))
                self.assertFalse(live.process(pending))
                self.assertEqual(future.result(timeout=2)["tracks"][0]["name"], "Main")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_timeout_removes_unclaimed_request(self):
        with patch.object(server, "inbox", return_value=self.folder), \
                patch.object(server, "LIVE_TIMEOUT_SECONDS", 0.05):
            with self.assertRaises(TimeoutError):
                server.call("tracks", {})
        self.assertEqual(list(self.folder.iterdir()), [])


class SurfaceDispatchTests(unittest.TestCase):
    def setUp(self):
        self.parameter = SimpleNamespace(name="Cutoff", value=0.5, min=0, max=1,
                                         is_enabled=True, is_quantized=False, automation_state=0)
        effect = SimpleNamespace(name="Filter", class_name="Filter", is_active=True, parameters=[self.parameter])
        self.track = SimpleNamespace(name="Audio", devices=[effect], has_audio_input=True, arrangement_clips=[])
        self.song = SimpleNamespace(tracks=[self.track], return_tracks=[], master_track=object(),
                                    view=SimpleNamespace(selected_track=self.track), is_playing=False, tempo=120)
        self.args = {"track_slot": 1, "track_name": "Audio"}

    def test_writes_only_to_confirmed_unautomated_parameters(self):
        edit = dict(self.args, device_slot=1, device_name="Filter", parameter="Cutoff", raw=0.75)
        with self.assertRaises(ValueError):
            surface.dispatch(self.song, "set", dict(edit, track_name="Stale"))
        with self.assertRaises(ValueError):
            surface.dispatch(self.song, "set", dict(edit, device_name="Stale"))
        self.parameter.automation_state = 1
        with self.assertRaisesRegex(ValueError, "automation"):
            surface.dispatch(self.song, "set", edit)
        self.assertEqual(self.parameter.value, 0.5)
        self.parameter.automation_state = 0
        self.assertEqual(surface.dispatch(self.song, "set", edit)["parameter"]["raw"], 0.75)

    def test_wav_rejects_existing_overlap_and_preserves_start_beat(self):
        def create_audio_clip(path, start):
            self.track.arrangement_clips.append(SimpleNamespace(
                name="Tone", start_time=start, end_time=start + 6, file_path=path,
                is_audio_clip=True, warping=True,
            ))

        self.track.create_audio_clip = create_audio_clip
        with tempfile.TemporaryDirectory() as folder:
            wav = Path(folder) / "tone.wav"
            write_wav(wav)
            edit = dict(self.args, file=str(wav), start_beat=8)
            inserted = surface.dispatch(self.song, "insert_wav", edit)["clip"]
            self.assertEqual(inserted["start_beat"], 8)
            self.assertFalse(self.track.arrangement_clips[0].warping)
            with self.assertRaisesRegex(ValueError, "overlaps"):
                surface.dispatch(self.song, "insert_wav", edit)
            self.assertEqual(len(self.track.arrangement_clips), 1)
