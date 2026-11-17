from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

PROJECT_DIR = Path(__file__).parent.resolve()
VENV_PYTHON = PROJECT_DIR / ".venv" / "bin" / "python3"
APP_PY = PROJECT_DIR / "app.py"
APP_NAME = "Odyssey Remote.app"
APPLICATIONS_DIR = Path("/Applications")
TARGET_APP_PATH = APPLICATIONS_DIR / APP_NAME


def generate_icon(output_icns: Path):
    """Generates a sleek dark Odyssey monitor icon and builds an Apple .icns file."""
    iconset_dir = PROJECT_DIR / "AppIcon.iconset"
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
    iconset_dir.mkdir(parents=True, exist_ok=True)

    # 1024x1024 master icon
    size = 1024
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer squircle / rounded app background
    margin = 70
    bg_box = [margin, margin, size - margin, size - margin]
    draw.rounded_rectangle(bg_box, radius=200, fill="#121418", outline="#00e5ff", width=12)

    # Inner decorative cyber glow
    glow_box = [margin + 20, margin + 20, size - margin - 20, size - margin - 20]
    draw.rounded_rectangle(glow_box, radius=180, outline="#00e5ff33", width=6)

    # Monitor Screen Frame
    mon_top = 260
    mon_bottom = 660
    mon_left = 180
    mon_right = 844
    draw.rounded_rectangle(
        [mon_left, mon_top, mon_right, mon_bottom],
        radius=30,
        fill="#1a1d24",
        outline="#00e5ff",
        width=10,
    )

    # Monitor Screen Inner Display area
    draw.rounded_rectangle(
        [mon_left + 16, mon_top + 16, mon_right - 16, mon_bottom - 16],
        radius=20,
        fill="#0b0e14",
    )

    # Brightness sun icon inside monitor
    sun_center = (size // 2, (mon_top + mon_bottom) // 2)
    sun_radius = 65
    draw.ellipse(
        [
            sun_center[0] - sun_radius,
            sun_center[1] - sun_radius,
            sun_center[0] + sun_radius,
            sun_center[1] + sun_radius,
        ],
        fill="#00e5ff",
    )

    # Monitor Stand Base
    stand_width = 80
    stand_top = mon_bottom
    stand_bottom = 760
    draw.polygon(
        [
            (size // 2 - stand_width // 2, stand_top),
            (size // 2 + stand_width // 2, stand_top),
            (size // 2 + stand_width // 2 + 30, stand_bottom),
            (size // 2 - stand_width // 2 - 30, stand_bottom),
        ],
        fill="#262b36",
        outline="#00e5ff",
    )

    # V-shaped Gaming Stand Feet
    feet_y = stand_bottom
    draw.line(
        [(size // 2 - 160, feet_y + 40), (size // 2, feet_y), (size // 2 + 160, feet_y + 40)],
        fill="#00e5ff",
        width=16,
    )

    # Generate all macOS icon sizes
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    for s in sizes:
        resized = img.resize((s, s), Image.LANCZOS)
        resized.save(iconset_dir / f"icon_{s}x{s}.png")
        if s * 2 <= 1024:
            resized_2x = img.resize((s * 2, s * 2), Image.LANCZOS)
            resized_2x.save(iconset_dir / f"icon_{s}x{s}@2x.png")

    # Run iconutil to create .icns
    subprocess.run(["iconutil", "-c", "icns", str(iconset_dir), "-o", str(output_icns)], check=True)
    shutil.rmtree(iconset_dir)
    print(f"Generated icon: {output_icns}")


def build_app():
    print(f"Building {APP_NAME}...")

    contents_dir = TARGET_APP_PATH / "Contents"
    macos_dir = contents_dir / "MacOS"
    resources_dir = contents_dir / "Resources"

    if TARGET_APP_PATH.exists():
        shutil.rmtree(TARGET_APP_PATH)

    macos_dir.mkdir(parents=True, exist_ok=True)
    resources_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate icon
    icon_path = resources_dir / "AppIcon.icns"
    generate_icon(icon_path)

    # 2. Write Info.plist
    info_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Odyssey Remote</string>
    <key>CFBundleDisplayName</key>
    <string>Odyssey Remote</string>
    <key>CFBundleIdentifier</key>
    <string>com.bumbledoge.odysseyremote</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleExecutable</key>
    <string>OdysseyRemote</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>
"""
    (contents_dir / "Info.plist").write_text(info_plist, encoding="utf-8")

    # 3. Write executable launcher script
    launcher_script = f"""#!/bin/bash
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"
cd "{PROJECT_DIR}"
exec "{VENV_PYTHON}" "{APP_PY}"
"""
    executable_path = macos_dir / "OdysseyRemote"
    executable_path.write_text(launcher_script, encoding="utf-8")
    executable_path.chmod(0o755)

    print(f"\nSUCCESS: Installed application to {TARGET_APP_PATH}")
    print("You can now open it from Spotlight, Launchpad, or the Applications folder!")


if __name__ == "__main__":
    build_app()
