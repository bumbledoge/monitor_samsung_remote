from __future__ import annotations

import asyncio
import json
import ssl
import sys
import websockets

MONITOR_IP = "192.168.1.129"
MONITOR_PORT = 8002
TOKEN = "89413900"
APP_NAME_B64 = "RGlzcGxheUN0cmw="

# Key candidates that might trigger the monitor's center JOG button / quick OSD menu
CANDIDATE_KEYS = [
    ("KEY_TOOLS", "Tools / Quick Menu"),
    ("KEY_MENU", "Menu"),
    ("KEY_MORE", "More / 123 / Quick Bar"),
    ("KEY_ENTER", "Center Enter (when idle)"),
    ("KEY_CONTROL", "Monitor Control / Function"),
    ("KEY_INFO", "Info / Display info"),
    ("KEY_FUNCTION", "Function Key"),
    ("KEY_QUICK_SETTINGS", "Quick Settings"),
    ("KEY_PANEL_ENTER", "Physical Panel Center Push"),
    ("KEY_PANEL_MENU", "Physical Panel Menu"),
    ("KEY_SMART_CONTROL", "Smart Control OSD"),
    ("KEY_HELP", "Help / OSD"),
    ("KEY_OSD", "On-Screen Display Menu"),
    ("KEY_GAME_BAR", "Game Bar"),
    ("KEY_SETTINGS", "Settings"),
]


async def send_single_key(key: str):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    uri = f"wss://{MONITOR_IP}:{MONITOR_PORT}/api/v2/channels/samsung.remote.control?name={APP_NAME_B64}&token={TOKEN}"

    async with websockets.connect(uri, ssl=ctx, open_timeout=5) as ws:
        await ws.recv()
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


async def run_tester():
    print("=" * 60)
    print(" Samsung Odyssey G70B — JOG / Quick Menu Key Discovery Tool")
    print("=" * 60)
    print("We will send candidate keys to your monitor one by one.")
    print("Watch your monitor screen to see which key opens the small JOG menu!")
    print("=" * 60 + "\n")

    for idx, (key, desc) in enumerate(CANDIDATE_KEYS, 1):
        input(f"[{idx}/{len(CANDIDATE_KEYS)}] Press [Enter] to send '{key}' ({desc})... ")
        try:
            await send_single_key(key)
            print(f"  -> Sent {key}! Did the small menu appear? (Check screen)")
        except Exception as e:
            print(f"  -> Error sending {key}: {e}")

    print("\nTest completed.")
    print("If one of the keys worked, note which one it was!")


if __name__ == "__main__":
    asyncio.run(run_tester())
