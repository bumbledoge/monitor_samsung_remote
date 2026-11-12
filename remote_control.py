from __future__ import annotations

import argparse
import asyncio
import json
import os
import select
import ssl
import sys
import termios
import time
import tty
from pathlib import Path
import websockets

MONITOR_IP = "192.168.1.129"
MONITOR_PORT = 8002
TOKEN = "89413900"
APP_NAME_B64 = "RGlzcGxheUN0cmw="  # Base64 for "DisplayCtrl"
SEQUENCE_FILE = Path(__file__).parent / "sequence.json"


async def send_single_key_ws(ws, key: str):
    """Sends a single key event over an active websocket connection."""
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


async def send_keys(keys: list[str], delays: list[float] | float = 0.5):
    """Sends a sequence of remote key presses."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    uri = f"wss://{MONITOR_IP}:{MONITOR_PORT}/api/v2/channels/samsung.remote.control?name={APP_NAME_B64}&token={TOKEN}"

    if isinstance(delays, (int, float)):
        delays = [float(delays)] * len(keys)

    async with websockets.connect(uri, ssl=ctx, open_timeout=5) as ws:
        await ws.recv()
        for i, key in enumerate(keys):
            print(f"  [{i+1}/{len(keys)}] Sending {key}...")
            await send_single_key_ws(ws, key)
            delay = delays[i] if i < len(delays) else 0.5
            if delay > 0:
                await asyncio.sleep(delay)


def get_single_char() -> str:
    """Reads a single keypress or escape sequence immediately from terminal."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":  # Escape or arrow key sequence
            # Check if more characters follow immediately
            r, _, _ = select.select([sys.stdin], [], [], 0.05)
            if r:
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    if ch3 == "A":
                        return "UP_ARROW"
                    elif ch3 == "B":
                        return "DOWN_ARROW"
                    elif ch3 == "C":
                        return "RIGHT_ARROW"
                    elif ch3 == "D":
                        return "LEFT_ARROW"
                return "ESC"
            return "ESC"
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


async def instant_interactive_remote():
    """Instant live remote control — keystrokes and arrow keys are sent immediately with no Enter needed."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    uri = f"wss://{MONITOR_IP}:{MONITOR_PORT}/api/v2/channels/samsung.remote.control?name={APP_NAME_B64}&token={TOKEN}"

    print(f"Connecting to {MONITOR_IP}...")
    async with websockets.connect(uri, ssl=ctx, open_timeout=5) as ws:
        await ws.recv()

        print("\n" + "=" * 65)
        print("  SAMSUNG ODYSSEY G70B — INSTANT LIVE REMOTE (NO ENTER NEEDED)")
        print("=" * 65)
        print("Controls (press any key directly on your keyboard):")
        print("  W / A / S / D     : Up / Left / Down / Right")
        print("  [Arrow Keys]      : Up / Down / Left / Right")
        print("  [Enter] or e      : Select / Enter (KEY_ENTER)")
        print("  [Backspace] or b  : Back / Return (KEY_RETURN)")
        print("  m                 : Menu / Toggle (KEY_MENU)")
        print("  h                 : Home (KEY_HOME)")
        print("  [Esc] or x        : Exit Menu (KEY_EXIT)")
        print("  c                 : Cancel (KEY_CANCEL)")
        print("  q                 : Quit interactive mode")
        print("=" * 65)
        print("Ready! Press buttons to control monitor in real-time:\n")

        KEY_MAP = {
            # WASD navigation
            "w": "KEY_UP",
            "W": "KEY_UP",
            "a": "KEY_LEFT",
            "A": "KEY_LEFT",
            "s": "KEY_DOWN",
            "S": "KEY_DOWN",
            "d": "KEY_RIGHT",
            "D": "KEY_RIGHT",
            # Arrow keys
            "UP_ARROW": "KEY_UP",
            "DOWN_ARROW": "KEY_DOWN",
            "LEFT_ARROW": "KEY_LEFT",
            "RIGHT_ARROW": "KEY_RIGHT",
            # Selection & Return
            "\r": "KEY_ENTER",
            "\n": "KEY_ENTER",
            "e": "KEY_ENTER",
            "E": "KEY_ENTER",
            "\x7f": "KEY_RETURN",
            "\x08": "KEY_RETURN",
            "b": "KEY_RETURN",
            "B": "KEY_RETURN",
            # Menu controls
            "m": "KEY_MENU",
            "M": "KEY_MENU",
            "h": "KEY_HOME",
            "H": "KEY_HOME",
            "ESC": "KEY_EXIT",
            "x": "KEY_EXIT",
            "X": "KEY_EXIT",
            "c": "KEY_CANCEL",
            "C": "KEY_CANCEL",
            # Legacy u/d/l/r aliases
            "u": "KEY_UP",
            "l": "KEY_LEFT",
            "r": "KEY_RIGHT",
        }

        loop = asyncio.get_running_loop()

        while True:
            char = await loop.run_in_executor(None, get_single_char)

            if char == "q" or char == "Q" or char == "\x03":  # Ctrl+C or 'q'
                print("\nExiting interactive remote.")
                break

            target_key = KEY_MAP.get(char)
            if target_key:
                await send_single_key_ws(ws, target_key)
                print(f" -> Sent: {target_key}")
            else:
                print(f" -> Unmapped key: {repr(char)}")


def main():
    parser = argparse.ArgumentParser(description="Samsung Odyssey G70B Remote Simulator")
    parser.add_argument(
        "mode",
        choices=["interactive", "key"],
        nargs="?",
        default="interactive",
        help="Mode: 'interactive' (instant keypress remote), 'key' (send single key)",
    )
    parser.add_argument("--key", type=str, default="KEY_MENU", help="Key name for 'key' mode")

    args = parser.parse_args()

    if args.mode == "interactive":
        asyncio.run(instant_interactive_remote())
    elif args.mode == "key":
        key = args.key.upper()
        if not key.startswith("KEY_"):
            key = f"KEY_{key}"
        asyncio.run(send_keys([key]))


if __name__ == "__main__":
    main()
