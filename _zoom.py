"""Zoom into candidate site regions on VLR's Ascent map to read the plant markers."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

BASE = Path(r"D:\好玩的项目\valorant-analytics")
MAP = BASE / "_cache" / "maps" / "vlr_ascent.png"
OUT = BASE / "figures"

# candidate boxes (x0, y0, x1, y1)
BOXES = {
    "left_region": (120, 240, 460, 420),
    "right_region": (780, 210, 980, 380),
    "top_region": (400, 40, 640, 220),
    "bottom_region": (380, 680, 760, 980),
}


def main() -> None:
    img = Image.open(MAP).convert("RGBA")
    bg = Image.new("RGBA", img.size, (14, 19, 27, 255))
    bg.alpha_composite(img)
    rgb = bg.convert("RGB")

    for name, box in BOXES.items():
        crop = rgb.crop(box)
        crop = crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS)
        p = OUT / f"zoom_{name}.png"
        crop.save(p)
        print(f"{name:<14} {box} -> {p}  ({crop.size[0]}x{crop.size[1]})")


if __name__ == "__main__":
    main()
