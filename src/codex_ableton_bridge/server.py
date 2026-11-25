"""Local Codex MCP server and a direct diagnostic CLI."""
import json
import math
import sys
import time
import uuid
from importlib.metadata import version

from CodexAbletonBridge.protocol import EFFECTS, inbox, write_json

from .audio import analyze, measure_main_render

TRACK = {"track_slot": {"type": "integer", "minimum": 1}, "track_name": {"type": "string"}}
DEVICE = dict(TRACK, device_slot={"type": "integer", "minimum": 1}, device_name={"type": "string"})
PARAMETER = dict(DEVICE, parameter={"type": "string"}, raw={"type": "number"})
AUDIO = {"file": {"type": "string"}, "start": {"type": "number", "minimum": 0},
         "seconds": {"type": "number", "minimum": 2, "maximum": 60}}


def tool(name, description, properties, required=None):
    return {"name": name, "description": description, "inputSchema": {
        "type": "object", "properties": properties, "additionalProperties": False,
        "required": list(properties) if required is None else required,
    }}


TOOLS = [
    tool("tracks", "List Live tracks, selection and supported stock effects. Use returned slot and name.", {}),
    tool("arrangement", "List a track's Arrangement clips, source paths and beat positions.", TRACK),
    tool("insert_wav", "Insert a local PCM WAV at a zero-based beat in a regular Arrangement audio track. "
                      "Use only on user-requested edits. Inspect Arrangement before retrying a timeout.",
         dict(TRACK, file={"type": "string"}, start_beat={"type": "number", "minimum": 0})),
    tool("chain", "Read the top-level effects and devices on one Live track.", TRACK),
    tool("add", "Append one stock audio effect to a verified Live track. Use only when the user requests an edit. "
                "Returns the inserted device and its current parameters. A timeout requires inspecting the chain "
                "before retrying, to avoid inserting duplicates.",
         dict(TRACK, effect={"type": "string", "enum": list(EFFECTS)})),
    tool("parameters", "Read raw ranges, displayed values and choices for one device.", DEVICE),
    tool("preview", "Convert a proposed raw setting to the displayed Ableton value without editing.", PARAMETER),
    tool("set", "Set one device parameter after verifying the track, device and displayed units. "
                "Use only when the user requests an edit. Returns the resulting value.", PARAMETER),
    tool("analyze_render", "Analyze a local audio excerpt rendered from the intended Ableton track. "
                           "Returns peak, RMS, approximate frequency-band levels and silence detection. "
                           "For requests to make mixing decisions from audio, analyze the track's render before "
                           "editing and avoid inferring a problem from any single spectral band. "
                           "This analysis uses measurements from audio and does not provide auditory perception.",
         AUDIO, ["file"]),
    tool("measure_main_render", "Measure a local, unnormalized Ableton Main render over its full duration: "
                                "sample peak (dBFS), true peak (dBTP), headroom, integrated loudness (LUFS) "
                                "and loudness range. Render the actual Main output and compare the same range "
                                "before and after any requested mix change.",
         {"file": {"type": "string"}}),
]
BY_NAME = {entry["name"]: entry for entry in TOOLS}
LIVE_TIMEOUT_SECONDS = 5
PROTOCOL_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")


def validate_arguments(schema, arguments):
    properties = schema["properties"]
    if (not isinstance(arguments, dict) or set(arguments) - properties.keys()
            or set(schema["required"]) - arguments.keys()):
        raise ValueError("Arguments do not match the tool schema.")
    for key, value in arguments.items():
        field = properties[key]
        kind = field["type"]
        if kind == "string" and not isinstance(value, str):
            raise ValueError("%s must be a string." % key)
        if kind == "integer" and type(value) is not int:
            raise ValueError("%s must be an integer." % key)
        if kind in ("integer", "number"):
            if type(value) not in (int, float) or abs(value) > sys.float_info.max or not math.isfinite(value):
                raise ValueError("%s must be finite." % key)
            if not field.get("minimum", -math.inf) <= value <= field.get("maximum", math.inf):
                raise ValueError("%s is out of range." % key)
        if "enum" in field and value not in field["enum"]:
            raise ValueError("%s is not an allowed choice." % key)


def call(name, arguments):
    validate_arguments(BY_NAME[name]["inputSchema"], arguments)
    if name == "analyze_render":
        return analyze(**arguments)
    if name == "measure_main_render":
        return measure_main_render(**arguments)

    folder = inbox()
    request = folder / (uuid.uuid4().hex + ".request")
    reply = request.with_suffix(".reply")
    deadline = time.time() + LIVE_TIMEOUT_SECONDS
    wait_until = time.monotonic() + LIVE_TIMEOUT_SECONDS
    write_json(request, {"action": name, "arguments": arguments, "expires": deadline})
    try:
        while time.monotonic() < wait_until:
            try:
                response = json.loads(reply.read_text(encoding="utf-8"))
            except FileNotFoundError:
                time.sleep(0.04)
                continue
            if "error" in response:
                raise ValueError(response["error"])
            return response
        raise TimeoutError("Live did not reply. Check the CodexAbletonBridge Control Surface. "
                           "After an edit request, inspect its target in Live before retrying.")
    finally:
        request.unlink(missing_ok=True)
        reply.unlink(missing_ok=True)


def send(message):
    print(json.dumps(message, allow_nan=False), flush=True)


def serve():
    for line in sys.stdin:
        try:
            message = json.loads(line)
        except ValueError:
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Invalid JSON."}})
            continue
        if (not isinstance(message, dict) or message.get("jsonrpc") != "2.0"
                or not isinstance(message.get("method"), str)):
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid request."}})
            continue
        if "id" not in message:
            continue
        request_id = message["id"]
        if type(request_id) not in (str, int):
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid request ID."}})
            continue
        response = {"jsonrpc": "2.0", "id": request_id}
        method = message["method"]
        params = message.get("params", {})
        if not isinstance(params, dict):
            response["error"] = {"code": -32602, "message": "Expected named parameters."}
        elif method == "initialize":
            wanted = params.get("protocolVersion")
            protocol = wanted if wanted in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[-1]
            response["result"] = {
                "protocolVersion": protocol, "capabilities": {"tools": {}},
                "serverInfo": {"name": "codex-ableton-bridge", "version": version("codex-ableton-bridge")},
                "instructions": "Use tracks before edits. For audio-informed requests, analyze an excerpt rendered "
                                "from the requested track and use its measurements alongside the user's intent.",
            }
        elif method == "tools/list":
            response["result"] = {"tools": TOOLS}
        elif method == "tools/call":
            try:
                result = call(params["name"], params.get("arguments", {}))
                response["result"] = {"content": [{"type": "text", "text": json.dumps(result, allow_nan=False)}]}
            except (KeyError, ValueError, TypeError, RuntimeError, OSError) as exc:
                response["result"] = {"isError": True, "content": [{"type": "text", "text": str(exc)}]}
        elif method == "ping":
            response["result"] = {}
        else:
            response["error"] = {"code": -32601, "message": "Unknown MCP method."}
        send(response)


def main():
    if len(sys.argv) == 1:
        serve()
    else:
        try:
            if len(sys.argv) > 3:
                raise ValueError("Usage: codex-ableton-bridge [tool [JSON arguments]]")
            arguments = json.loads(sys.argv[2]) if len(sys.argv) == 3 else {}
            print(json.dumps(call(sys.argv[1], arguments), indent=2, allow_nan=False))
        except (KeyError, ValueError, TypeError, RuntimeError, OSError) as exc:
            sys.exit(str(exc))


if __name__ == "__main__":
    main()
