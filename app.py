from __future__ import annotations

import asyncio
import json
import ssl
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
from pathlib import Path
import websockets

MONITOR_IP = "192.168.1.129"
MONITOR_PORT = 8002
TOKEN = "89413900"
APP_NAME_B64 = "RGlzcGxheUN0cmw="
SEQUENCE_FILE = Path(__file__).parent / "sequence.json"

# High-contrast Cyber-Cyan Dark Theme
BG_MAIN = "#121418"
BG_CARD = "#1a1d24"
BG_BUTTON = "#262b36"
BG_BUTTON_HOVER = "#323947"
BG_BUTTON_ACTIVE = "#1e222a"

ACCENT_CYAN = "#00e5ff"
ACCENT_BLUE = "#3b82f6"
TEXT_PRIMARY = "#f8fafc"
TEXT_SECONDARY = "#94a3b8"
TEXT_MUTED = "#64748b"
STATUS_GREEN = "#10b981"
STATUS_RED = "#ef4444"

FONT_TITLE = ("Helvetica Neue", 15, "bold")
FONT_SECTION = ("Helvetica Neue", 10, "bold")
FONT_BTN_LG = ("Helvetica Neue", 12, "bold")
FONT_BTN_MD = ("Helvetica Neue", 11, "bold")
FONT_BTN_SM = ("Helvetica Neue", 10, "bold")
FONT_STATUS = ("Helvetica Neue", 10)


class SamsungRemoteClient:
    """Manages asynchronous WebSocket communication with the monitor in a worker thread."""

    def __init__(self, ip: str, port: int, token: str):
        self.ip = ip
        self.port = port
        self.token = token
        self.loop: asyncio.AbstractEventLoop | None = None
        self.thread: threading.Thread | None = None
        self.queue: asyncio.Queue | None = None
        self.running = False
        self.status_callback = None
        self._start_worker()

    def _start_worker(self):
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.queue = asyncio.Queue()
        self.loop.run_until_complete(self._worker())

    async def _worker(self):
        while self.running:
            task = await self.queue.get()
            cmd_type, payload = task
            try:
                if cmd_type == "single_key":
                    await self._send_key_direct(payload)
                elif cmd_type == "sequence":
                    await self._send_sequence_direct(payload)
            except Exception as e:
                self._update_status(f"Error: {e}", STATUS_RED)
            finally:
                self.queue.task_done()

    async def _send_key_direct(self, key: str):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        uri = f"wss://{self.ip}:{self.port}/api/v2/channels/samsung.remote.control?name={APP_NAME_B64}&token={self.token}"

        try:
            async with websockets.connect(uri, ssl=ctx, open_timeout=3) as ws:
                await ws.recv()
                msg = {
                    "method": "ms.remote.control",
                    "params": {
                        "Cmd": "Click",
                        "DataOfCmd": key,
                        "Option": "false",
                        "TypeOfRemote": "SendRemoteKey",
                    },
                }
                await ws.send(json.dumps(msg))
                self._update_status(f"Sent {key}", STATUS_GREEN)
        except Exception as e:
            self._update_status(f"Connect failed: {e}", STATUS_RED)

    async def _send_sequence_direct(self, seq_params: dict):
        direction = seq_params["direction"]
        steps = seq_params["steps"]
        speed = seq_params.get("speed", 1.0)
        adjust_key = "KEY_RIGHT" if direction == "up" else "KEY_LEFT"

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
        if SEQUENCE_FILE.exists():
            try:
                with open(SEQUENCE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    raw_seq = data.get("sequence", raw_seq)
            except Exception:
                pass

        sequence: list[tuple[str, float]] = []
        for item in raw_seq:
            key = item["key"]
            delay = float(item.get("delay", 0.3)) * speed
            if key == "ADJUST":
                for _ in range(max(1, steps)):
                    sequence.append((adjust_key, 0.1 * speed))
            else:
                sequence.append((key, delay))

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        uri = f"wss://{self.ip}:{self.port}/api/v2/channels/samsung.remote.control?name={APP_NAME_B64}&token={self.token}"

        try:
            self._update_status(f"Adjusting brightness {direction} ({steps}x)...", ACCENT_CYAN)
            async with websockets.connect(uri, ssl=ctx, open_timeout=4) as ws:
                await ws.recv()
                for key, delay in sequence:
                    msg = {
                        "method": "ms.remote.control",
                        "params": {
                            "Cmd": "Click",
                            "DataOfCmd": key,
                            "Option": "false",
                            "TypeOfRemote": "SendRemoteKey",
                        },
                    }
                    await ws.send(json.dumps(msg))
                    if delay > 0:
                        await asyncio.sleep(delay)
            self._update_status(f"Brightness {direction} complete!", STATUS_GREEN)
        except Exception as e:
            self._update_status(f"Sequence failed: {e}", STATUS_RED)

    def _update_status(self, text: str, color: str):
        if self.status_callback:
            self.status_callback(text, color)

    def send_key(self, key: str):
        if self.loop and self.queue:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, ("single_key", key))

    def send_sequence(self, direction: str, steps: int = 5, speed: float = 1.0):
        if self.loop and self.queue:
            self.loop.call_soon_threadsafe(
                self.queue.put_nowait,
                ("sequence", {"direction": direction, "steps": steps, "speed": speed}),
            )


class CustomButton(tk.Label):
    """Reliable, modern styled button using tk.Label with hover and active states."""

    def __init__(
        self,
        parent,
        text: str = "",
        command=None,
        bg_color: str = BG_BUTTON,
        hover_color: str = BG_BUTTON_HOVER,
        active_color: str = BG_BUTTON_ACTIVE,
        text_color: str = TEXT_PRIMARY,
        font=FONT_BTN_MD,
        padx: int = 12,
        pady: int = 8,
        relief: str = "flat",
        bd: int = 0,
        **kwargs,
    ):
        super().__init__(
            parent,
            text=text,
            bg=bg_color,
            fg=text_color,
            font=font,
            padx=padx,
            pady=pady,
            relief=relief,
            bd=bd,
            cursor="pointinghand",
            justify="center",
            anchor="center",
            **kwargs,
        )
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.active_color = active_color
        self.text_color = text_color

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, _):
        self.configure(bg=self.hover_color)

    def _on_leave(self, _):
        self.configure(bg=self.bg_color)

    def _on_press(self, _):
        self.configure(bg=self.active_color)

    def _on_release(self, _):
        self.configure(bg=self.hover_color)
        if self.command:
            self.command()


class OdysseyRemoteApp(tk.Tk):
    """Main Application Window for Samsung Odyssey G70B Remote Control."""

    def __init__(self):
        super().__init__()

        self.title("Samsung Odyssey Remote")
        self.geometry("380x690")
        self.minsize(360, 650)
        self.configure(bg=BG_MAIN)
        self.always_on_top = False

        # Initialize network client
        self.client = SamsungRemoteClient(MONITOR_IP, MONITOR_PORT, TOKEN)
        self.client.status_callback = self._on_status_update

        self.step_var = tk.IntVar(value=5)

        self._build_ui()
        self._bind_keyboard_shortcuts()

        # Center on screen and bring to front
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        w = 380
        h = 690
        x = max(50, (screen_w - w) // 2)
        y = max(50, (screen_h - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.lift()
        self.attributes("-topmost", True)
        self.after(600, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def _build_ui(self):
        # 1. Header Frame
        header = tk.Frame(self, bg=BG_MAIN)
        header.pack(fill="x", padx=16, pady=(16, 8))

        title_lbl = tk.Label(
            header,
            text="ODYSSEY G70B",
            font=FONT_TITLE,
            fg=TEXT_PRIMARY,
            bg=BG_MAIN,
        )
        title_lbl.pack(side="left")

        # Pin / Always on Top toggle
        self.pin_btn = CustomButton(
            header,
            text="📌 Pin",
            font=FONT_BTN_SM,
            bg_color=BG_CARD,
            hover_color=BG_BUTTON_HOVER,
            text_color=TEXT_MUTED,
            padx=10,
            pady=4,
            command=self._toggle_always_on_top,
        )
        self.pin_btn.pack(side="right")

        # 2. Status Card
        status_card = tk.Frame(self, bg=BG_CARD, padx=12, pady=8)
        status_card.pack(fill="x", padx=16, pady=(0, 12))

        self.dot = tk.Canvas(status_card, width=10, height=10, bg=BG_CARD, highlightthickness=0)
        self.dot.pack(side="left", padx=(0, 8))
        self.dot_circle = self.dot.create_oval(1, 1, 9, 9, fill=STATUS_GREEN, outline="")

        self.status_lbl = tk.Label(
            status_card,
            text=f"Ready • {MONITOR_IP}",
            font=FONT_STATUS,
            fg=TEXT_SECONDARY,
            bg=BG_CARD,
        )
        self.status_lbl.pack(side="left")

        # 3. Brightness Macro Card
        bright_card = tk.Frame(self, bg=BG_CARD, padx=14, pady=12)
        bright_card.pack(fill="x", padx=16, pady=(0, 12))

        bright_header = tk.Frame(bright_card, bg=BG_CARD)
        bright_header.pack(fill="x", pady=(0, 10))

        b_title = tk.Label(
            bright_header,
            text="BRIGHTNESS MACRO",
            font=FONT_SECTION,
            fg=ACCENT_CYAN,
            bg=BG_CARD,
        )
        b_title.pack(side="left")

        # Step count selectors (1, 5, 10)
        steps_frame = tk.Frame(bright_header, bg=BG_CARD)
        steps_frame.pack(side="right")
        for val in [1, 5, 10]:
            rb = tk.Radiobutton(
                steps_frame,
                text=f"{val}",
                value=val,
                variable=self.step_var,
                font=FONT_BTN_SM,
                fg=TEXT_SECONDARY,
                selectcolor=BG_BUTTON,
                activebackground=BG_CARD,
                bg=BG_CARD,
                highlightthickness=0,
            )
            rb.pack(side="left", padx=2)

        # Brightness Buttons
        b_btn_frame = tk.Frame(bright_card, bg=BG_CARD)
        b_btn_frame.pack(fill="x")

        CustomButton(
            b_btn_frame,
            text="🔅 Dimmer -",
            command=lambda: self.client.send_sequence("down", self.step_var.get()),
            bg_color="#1e2430",
            hover_color="#2b3445",
            text_color="#e2e8f0",
            font=FONT_BTN_MD,
            pady=10,
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        CustomButton(
            b_btn_frame,
            text="🔆 Brighter +",
            command=lambda: self.client.send_sequence("up", self.step_var.get()),
            bg_color="#0e3a47",
            hover_color="#155366",
            text_color=ACCENT_CYAN,
            font=FONT_BTN_MD,
            pady=10,
        ).pack(side="right", fill="x", expand=True, padx=(6, 0))

        # 4. Quick Top Controls (Menu, Home, Tools)
        top_ctrls = tk.Frame(self, bg=BG_MAIN)
        top_ctrls.pack(fill="x", padx=16, pady=(0, 12))

        CustomButton(
            top_ctrls,
            text="MENU",
            command=lambda: self.client.send_key("KEY_MENU"),
            bg_color=BG_CARD,
            hover_color=BG_BUTTON_HOVER,
            text_color=ACCENT_CYAN,
            font=FONT_BTN_SM,
            pady=8,
        ).pack(side="left", fill="x", expand=True, padx=4)

        CustomButton(
            top_ctrls,
            text="HOME",
            command=lambda: self.client.send_key("KEY_HOME"),
            bg_color=BG_CARD,
            hover_color=BG_BUTTON_HOVER,
            text_color=TEXT_PRIMARY,
            font=FONT_BTN_SM,
            pady=8,
        ).pack(side="left", fill="x", expand=True, padx=4)

        CustomButton(
            top_ctrls,
            text="TOOLS",
            command=lambda: self.client.send_key("KEY_TOOLS"),
            bg_color=BG_CARD,
            hover_color=BG_BUTTON_HOVER,
            text_color=TEXT_SECONDARY,
            font=FONT_BTN_SM,
            pady=8,
        ).pack(side="left", fill="x", expand=True, padx=4)

        # 5. D-PAD Section
        dpad_card = tk.Frame(self, bg=BG_CARD, padx=10, pady=16)
        dpad_card.pack(fill="x", padx=16, pady=(0, 12))

        # D-pad Up
        dpad_top = tk.Frame(dpad_card, bg=BG_CARD)
        dpad_top.pack()
        CustomButton(
            dpad_top,
            text="▲\nW",
            command=lambda: self.client.send_key("KEY_UP"),
            bg_color=BG_BUTTON,
            hover_color=BG_BUTTON_HOVER,
            font=FONT_BTN_MD,
            padx=20,
            pady=6,
        ).pack()

        # D-pad Middle (Left, OK/Enter, Right)
        dpad_mid = tk.Frame(dpad_card, bg=BG_CARD)
        dpad_mid.pack(pady=8)

        CustomButton(
            dpad_mid,
            text="◀ A",
            command=lambda: self.client.send_key("KEY_LEFT"),
            bg_color=BG_BUTTON,
            hover_color=BG_BUTTON_HOVER,
            font=FONT_BTN_MD,
            padx=16,
            pady=12,
        ).pack(side="left", padx=8)

        CustomButton(
            dpad_mid,
            text="OK\n(E)",
            command=lambda: self.client.send_key("KEY_ENTER"),
            bg_color=ACCENT_BLUE,
            hover_color="#2563eb",
            text_color="#ffffff",
            font=FONT_BTN_MD,
            padx=18,
            pady=6,
        ).pack(side="left", padx=8)

        CustomButton(
            dpad_mid,
            text="D ▶",
            command=lambda: self.client.send_key("KEY_RIGHT"),
            bg_color=BG_BUTTON,
            hover_color=BG_BUTTON_HOVER,
            font=FONT_BTN_MD,
            padx=16,
            pady=12,
        ).pack(side="left", padx=8)

        # D-pad Down
        dpad_bot = tk.Frame(dpad_card, bg=BG_CARD)
        dpad_bot.pack()
        CustomButton(
            dpad_bot,
            text="S\n▼",
            command=lambda: self.client.send_key("KEY_DOWN"),
            bg_color=BG_BUTTON,
            hover_color=BG_BUTTON_HOVER,
            font=FONT_BTN_MD,
            padx=20,
            pady=6,
        ).pack()

        # 6. Bottom Controls (Back, Exit)
        bottom_ctrls = tk.Frame(self, bg=BG_MAIN)
        bottom_ctrls.pack(fill="x", padx=16, pady=(0, 10))

        CustomButton(
            bottom_ctrls,
            text="↩ BACK (B)",
            command=lambda: self.client.send_key("KEY_RETURN"),
            bg_color=BG_CARD,
            hover_color=BG_BUTTON_HOVER,
            text_color=TEXT_SECONDARY,
            font=FONT_BTN_SM,
            pady=10,
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        CustomButton(
            bottom_ctrls,
            text="✕ EXIT (X)",
            command=lambda: self.client.send_key("KEY_EXIT"),
            bg_color=BG_CARD,
            hover_color=BG_BUTTON_HOVER,
            text_color="#f87171",
            font=FONT_BTN_SM,
            pady=10,
        ).pack(side="right", fill="x", expand=True, padx=(6, 0))

        # 7. Keyboard Hint Footer
        footer = tk.Label(
            self,
            text="Keyboard active: WASD / Arrows / Enter / Esc / M",
            font=FONT_STATUS,
            fg=TEXT_MUTED,
            bg=BG_MAIN,
        )
        footer.pack(side="bottom", pady=(0, 10))

    def _toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        self.attributes("-topmost", self.always_on_top)
        if self.always_on_top:
            self.pin_btn.configure(fg=ACCENT_CYAN, text="📌 Pinned")
        else:
            self.pin_btn.configure(fg=TEXT_MUTED, text="📌 Pin")

    def _on_status_update(self, text: str, color: str):
        self.after(0, self._set_status_ui, text, color)

    def _set_status_ui(self, text: str, color: str):
        self.status_lbl.config(text=text, fg=TEXT_PRIMARY)
        self.dot.itemconfig(self.dot_circle, fill=color)

    def _bind_keyboard_shortcuts(self):
        """Binds direct keyboard keys to monitor actions when window has focus."""
        key_mappings = {
            "w": "KEY_UP",
            "W": "KEY_UP",
            "Up": "KEY_UP",
            "s": "KEY_DOWN",
            "S": "KEY_DOWN",
            "Down": "KEY_DOWN",
            "a": "KEY_LEFT",
            "A": "KEY_LEFT",
            "Left": "KEY_LEFT",
            "d": "KEY_RIGHT",
            "D": "KEY_RIGHT",
            "Right": "KEY_RIGHT",
            "Return": "KEY_ENTER",
            "e": "KEY_ENTER",
            "E": "KEY_ENTER",
            "space": "KEY_ENTER",
            "BackSpace": "KEY_RETURN",
            "b": "KEY_RETURN",
            "B": "KEY_RETURN",
            "Escape": "KEY_EXIT",
            "x": "KEY_EXIT",
            "X": "KEY_EXIT",
            "m": "KEY_MENU",
            "M": "KEY_MENU",
            "h": "KEY_HOME",
            "H": "KEY_HOME",
            "t": "KEY_TOOLS",
            "T": "KEY_TOOLS",
        }

        def on_key(event):
            key = event.keysym
            target = key_mappings.get(key) or key_mappings.get(event.char)
            if target:
                self.client.send_key(target)

        self.bind("<Key>", on_key)


def main():
    app = OdysseyRemoteApp()
    app.mainloop()


if __name__ == "__main__":
    main()
