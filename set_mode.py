import asyncio
import json
import ssl
import websockets


async def change_brightness(direction="up"):
    key = "KEY_BRIGHTNESS_UP" if direction == "up" else "KEY_BRIGHTNESS_DOWN"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    uri = "wss://192.168.1.129:8002/api/v2/channels/samsung.remote.control?name=RGlzcGxheUN0cmw=&token=89413900"
    async with websockets.connect(uri, ssl=ctx) as ws:
        await ws.recv()
        await ws.send(
            json.dumps(
                {
                    "method": "ms.remote.control",
                    "params": {
                        "Cmd": "Click",
                        "DataOfCmd": key,
                        "Option": "false",
                        "TypeOfRemote": "SendRemoteKey",
                    },
                }
            )
        )


if __name__ == "__main__":
    asyncio.run(change_brightness("up"))
