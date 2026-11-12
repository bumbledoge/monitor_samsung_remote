# Samsung Odyssey G70B Monitor Remote & Brightness Control

Control Samsung Odyssey G70B (and other Samsung Tizen Smart Monitors / Smart TVs) over local WebSocket connection from Python / terminal.

## Features

- **Automated Brightness Control (`set_brightness.py`)**: Automatically navigates the monitor's OSD via WebSocket key simulation to adjust brightness up/down and exits cleanly.
- **Instant Live Terminal Remote (`remote_control.py`)**: Full real-time keyboard control with WASD & Arrow keys (no Enter required).
- **Key Discovery Tool (`test_keys.py`)**: Tests candidate remote control keys against your monitor's OSD.
- **Hardware LUT Dimmer (`dimmer.py`)**: Native macOS GPU look-up table software dimmer for night-time sub-zero dimming.

---

## Setup

1. **Install dependencies**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure IP and Token**:
   Edit `set_brightness.py` / `remote_control.py` with your monitor's IP address and remote token if different:
   ```python
   MONITOR_IP = "192.168.1.129"
   TOKEN = "89413900"
   ```

---

## Usage

### 1. Automated Brightness Adjustment
```bash
# Increase brightness by 5 steps
python set_brightness.py up 5

# Decrease brightness by 10 steps
python set_brightness.py down 10

# Adjust speed multiplier (optional)
python set_brightness.py up 5 --speed 0.85
```

### 2. Instant Live Remote (Terminal UI)
```bash
python remote_control.py
```

| Key | Action | Remote Code |
| :--- | :--- | :--- |
| **`W` / `A` / `S` / `D`** | Up / Left / Down / Right | `KEY_UP`, `KEY_LEFT`, `KEY_DOWN`, `KEY_RIGHT` |
| **`↑` / `←` / `↓` / `→`** | Up / Left / Down / Right | `KEY_UP`, `KEY_LEFT`, `KEY_DOWN`, `KEY_RIGHT` |
| **`E` / `Enter`** | Select / Enter | `KEY_ENTER` |
| **`B` / `Backspace`** | Back / Return | `KEY_RETURN` |
| **`M`** | Open / Toggle Menu | `KEY_MENU` |
| **`H`** | Home | `KEY_HOME` |
| **`X` / `Esc`** | Exit Menu | `KEY_EXIT` |
| **`Q`** | Quit Remote | — |

---

## Sequence Customization
The automated menu path is defined in `sequence.json`. You can modify the keys or delay timings directly in that file.
