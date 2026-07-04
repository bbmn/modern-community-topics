#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ICONSET = ROOT / "ModernCommunityTopics.iconset"
MASTER = ASSETS / "modern-community-topics-icon-1024.png"
ICNS = ROOT / "Modern Community Topics.app" / "Contents" / "Resources" / "ModernCommunityTopics.icns"

SIZES = [
    (16, "icon_16x16.png"),
    (32, "icon_16x16@2x.png"),
    (32, "icon_32x32.png"),
    (64, "icon_32x32@2x.png"),
    (128, "icon_128x128.png"),
    (256, "icon_128x128@2x.png"),
    (256, "icon_256x256.png"),
    (512, "icon_256x256@2x.png"),
    (512, "icon_512x512.png"),
    (1024, "icon_512x512@2x.png"),
]


def rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def draw_icon(size: int = 1024) -> Image.Image:
    scale = 4
    canvas_size = size * scale
    image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def s(value: float) -> int:
        return int(round(value * scale))

    base_box = (s(64), s(64), s(960), s(960))
    base_radius = s(170)

    shadow = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(base_box, radius=base_radius, fill=(5, 18, 28, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(s(28)))
    image.alpha_composite(shadow, (0, s(18)))

    draw.rounded_rectangle(base_box, radius=base_radius, fill=(28, 52, 66, 255))

    gold = (246, 195, 88, 255)
    gold_shadow = (123, 82, 20, 95)

    # RSS mark, using thick arcs and a dot so it stays readable in Dock-sized previews.
    origin = (s(250), s(760))
    dot_r = s(58)
    draw.ellipse(
        (origin[0] - dot_r, origin[1] - dot_r, origin[0] + dot_r, origin[1] + dot_r),
        fill=gold_shadow,
    )
    draw.ellipse(
        (origin[0] - dot_r, origin[1] - dot_r - s(8), origin[0] + dot_r, origin[1] + dot_r - s(8)),
        fill=gold,
    )

    for radius, width in [(260, 62), (440, 62)]:
        box = (
            origin[0] - s(radius),
            origin[1] - s(radius),
            origin[0] + s(radius),
            origin[1] + s(radius),
        )
        draw.arc(box, start=270, end=360, fill=gold_shadow, width=s(width))
        shadow_box = (box[0], box[1] - s(8), box[2], box[3] - s(8))
        draw.arc(shadow_box, start=270, end=360, fill=gold, width=s(width))

    image = image.resize((size, size), Image.Resampling.LANCZOS)
    return image


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    ICONSET.mkdir(exist_ok=True)
    master = draw_icon()
    master.save(MASTER)
    ICNS.parent.mkdir(exist_ok=True)
    master.save(
        ICNS,
        format="ICNS",
        sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)],
    )
    for size, name in SIZES:
        master.resize((size, size), Image.Resampling.LANCZOS).save(ICONSET / name)
    print(MASTER)
    print(ICNS)
    print(ICONSET)


if __name__ == "__main__":
    main()
