from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import json
import sys
from pathlib import Path

# Load macOS CoreGraphics framework
cg_lib = ctypes.util.find_library("CoreGraphics")
if not cg_lib:
    print("Error: CoreGraphics framework not found", file=sys.stderr)
    sys.exit(1)

cg = ctypes.cdll.LoadLibrary(cg_lib)

TABLE_SIZE = 256
FloatArray = ctypes.c_float * TABLE_SIZE
STATE_FILE = Path(__file__).parent / ".dimmer_state.json"


def get_online_displays() -> list[int]:
    """Returns a list of all active display IDs."""
    max_displays = 16
    displays = (ctypes.c_uint32 * max_displays)()
    display_count = ctypes.c_uint32()

    err = cg.CGGetOnlineDisplayList(max_displays, displays, ctypes.byref(display_count))
    if err != 0:
        return [cg.CGMainDisplayID()]
    return [displays[i] for i in range(display_count.value)]


def get_current_brightness() -> float:
    """Reads the saved software brightness state (default: 1.0)."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return float(data.get("brightness", 1.0))
        except Exception:
            pass
    return 1.0


def save_current_brightness(val: float):
    """Saves the current software brightness state."""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"brightness": round(val, 3)}, f)
    except Exception:
        pass


def set_display_brightness(level: float, display_ids: list[int] | None = None):
    """
    Sets GPU ColorSync LUT brightness scaling.
    level: 0.0 (black) to 1.0 (full normal brightness).
    """
    level = max(0.01, min(1.0, float(level)))

    if display_ids is None:
        display_ids = get_online_displays()

    # Generate linear ramp scaled by `level`
    r_table = FloatArray(*[float(i) / (TABLE_SIZE - 1) * level for i in range(TABLE_SIZE)])
    g_table = FloatArray(*[float(i) / (TABLE_SIZE - 1) * level for i in range(TABLE_SIZE)])
    b_table = FloatArray(*[float(i) / (TABLE_SIZE - 1) * level for i in range(TABLE_SIZE)])

    for disp in display_ids:
        if level >= 0.999:
            cg.CGDisplayRestoreColorSyncSettings()
        else:
            cg.CGSetDisplayTransferByTable(disp, TABLE_SIZE, r_table, g_table, b_table)

    save_current_brightness(level)
    print(f"Software brightness set to: {int(level * 100)}% ({level:.2f})")


def restore_default():
    """Restores native macOS ColorSync settings (100% normal)."""
    cg.CGDisplayRestoreColorSyncSettings()
    save_current_brightness(1.0)
    print("Software brightness restored to 100% (Native ColorSync).")


def main():
    parser = argparse.ArgumentParser(
        description="Direct macOS GPU Hardware LUT Dimmer (No Overlays, True Sub-Zero Dimming)"
    )
    parser.add_argument(
        "value",
        nargs="?",
        default=None,
        help="Brightness level: 0.0 to 1.0 (or 0%% to 100%%), 'up', 'down', or 'reset'",
    )
    parser.add_argument(
        "step",
        nargs="?",
        type=float,
        default=0.1,
        help="Step size for up/down (e.g. 0.1 for 10%%) [default: 0.1]",
    )

    args = parser.parse_args()

    if args.value is None or args.value == "status":
        current = get_current_brightness()
        print(f"Current software brightness: {int(current * 100)}% ({current:.2f})")
        return

    cmd = args.value.strip().lower()

    if cmd == "reset" or cmd == "restore" or cmd == "max":
        restore_default()
        return

    current = get_current_brightness()

    if cmd == "up":
        step_val = args.step if args.step <= 1.0 else args.step / 100.0
        new_val = min(1.0, current + step_val)
        set_display_brightness(new_val)
    elif cmd == "down":
        step_val = args.step if args.step <= 1.0 else args.step / 100.0
        new_val = max(0.02, current - step_val)
        set_display_brightness(new_val)
    else:
        # Numeric value
        val_str = cmd.rstrip("%")
        try:
            num = float(val_str)
            if num > 1.0:
                num = num / 100.0
            set_display_brightness(num)
        except ValueError:
            print(f"Invalid brightness value: '{args.value}'", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
