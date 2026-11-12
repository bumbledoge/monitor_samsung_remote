from __future__ import annotations

import argparse
import asyncio
import json
import ssl
import sys
from pathlib import Path
import websockets

MONITOR_IP = "192.168.1.129"
MONITOR_PORT = 8002
TOKEN = "89413900"
APP_NAME_B64 = "RGlzcGxheUN0cmw="  # Base64 for "DisplayCtrl"
SEQUENCE_FILE = Path(__file__).parent / "sequence.json"


def load_sequence(direction: str, steps: int, speed: float) -> list[tuple[str, float]]:
    """Loads sequence from sequence.json and expands the ADJUST step."""
    adjust_key = "KEY_RIGHT" if direction.lower() == "up" else "KEY_LEFT"

    if SEQUENCE_FILE.exists():
        with open(SEQUENCE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw_seq = data.get("sequence", [])
    else:
        # Fallback to default verified sequence
        raw_seq = [
            {"key": "KEY_MENU", "delay": 0.4},
            {"key": "KEY_ENTER", "delay": 0.35},
            {"key": "KEY_DOWN", "delay": 0.18},
            {"key": "KEY_DOWN", "delay": 0.18},
            {"key": "KEY_DOWN", "delay": 0.18},
            {"key": "KEY_ENTER", "delay": 0.35},
            {"key": "KEY_ENTER", "delay": 0.35},
            {"key": "ADJUST", "delay": 0.1},
            {"key": "KEY_RETURN", "delay": 0.25},
            {"key": "KEY_MENU", "delay": 0.25},
            {"key": "KEY_MENU", "delay": 0.2},
        ]

    result: list[tuple[str, float]] = []
    for item in raw_seq:
        key = item["key"]
        delay = float(item.get("delay", 0.3)) * speed

        if key == "ADJUST":
            for _ in range(max(1, steps)):
                result.append((adjust_key, 0.1 * speed))
        else:
            result.append((key, delay))

    return result


async def change_brightness(direction: str = "up", steps: int = 5, speed: float = 1.0):
    """Adjusts brightness on Samsung Odyssey G70B via WebSocket remote simulation."""
    sequence = load_sequence(direction=direction, steps=steps, speed=speed)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    uri = f"wss://{MONITOR_IP}:{MONITOR_PORT}/api/v2/channels/samsung.remote.control?name={APP_NAME_B64}&token={TOKEN}"

    async with websockets.connect(uri, ssl=ctx, open_timeout=5) as ws:
        await ws.recv()  # Initial handshake

        for key, delay in sequence:
            payload = {
                "method": "ms.remote.control",
                "params": {
                    "Cmd": "Click",
                    "DataOfCmd": key,
                    "Option": "false",
                    "TypeOfRemote": "SendRemoteKey",
                },
            }
            await ws.send(json.dumps(payload))
            if delay > 0:
                await asyncio.sleep(delay)


def main():
    parser = argparse.ArgumentParser(description="Samsung Odyssey G70B Brightness Control")
    parser.add_argument(
        "direction",
        nargs="?",
        choices=["up", "down"],
        default="up",
        help="Adjustment direction: 'up' (increase) or 'down' (decrease) [default: up]",
    )
    parser.add_argument(
        "steps",
        nargs="?",
        type=int,
        default=5,
        help="Number of adjustment steps [default: 5]",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Speed multiplier (e.g. 0.7 for faster, 1.2 for slower) [default: 1.0]",
    )

    args = parser.parse_args()
    print(f"Adjusting brightness {args.direction} by {args.steps} steps...")
    asyncio.run(change_brightness(direction=args.direction, steps=args.steps, speed=args.speed))
    print("Done.")


if __name__ == "__main__":
    main()
