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
    draw.rounded_rectangle(bg_box, radius=200, fill="#121418", outline="#00e5ff", width=14)

    # Inner decorative cyber glow
    glow_box = [margin + 20, margin + 20, size - margin - 20, size - margin - 20]
    draw.rounded_rectangle(glow_box, radius=180, outline="#008b99", width=6)

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
    print(f"Building native {APP_NAME}...")

    if TARGET_APP_PATH.exists():
        shutil.rmtree(TARGET_APP_PATH)

    # 1. Compile native macOS app bundle using osacompile
    applescript = f'do shell script "\\"{VENV_PYTHON}\\" \\"{APP_PY}\\" > /dev/null 2>&1 &"'
    subprocess.run(["osacompile", "-o", str(TARGET_APP_PATH), "-e", applescript], check=True)

    # 2. Generate and place custom cyber-cyan Odyssey icon
    resources_dir = TARGET_APP_PATH / "Contents" / "Resources"
    icon_path = resources_dir / "applet.icns"
    generate_icon(icon_path)

    # Also copy to AppIcon.icns for compatibility
    shutil.copy(icon_path, resources_dir / "AppIcon.icns")

    # 3. Touch app bundle to refresh LaunchServices / Finder cache
    subprocess.run(["touch", str(TARGET_APP_PATH)], check=True)

    print(f"\nSUCCESS: Installed application to {TARGET_APP_PATH}")
    print("You can now open it from Spotlight, Launchpad, or the Applications folder!")


if __name__ == "__main__":
    build_app()
