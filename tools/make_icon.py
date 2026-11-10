"""Pravi src/autostakla/resources/icon.ico (vetrobran na plavoj podlozi)."""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "src" / "autostakla" / "resources" / "icon.ico"


def draw(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 256
    d.rounded_rectangle([8 * s, 8 * s, 248 * s, 248 * s], radius=48 * s, fill=(21, 67, 120, 255))
    # vetrobran: trapez
    glass = [(52 * s, 70 * s), (204 * s, 70 * s), (226 * s, 186 * s), (30 * s, 186 * s)]
    d.polygon(glass, fill=(150, 205, 245, 255))
    d.line(glass + [glass[0]], fill=(235, 245, 255, 255), width=max(1, int(8 * s)))
    # odsjaj
    d.line([(80 * s, 160 * s), (120 * s, 92 * s)], fill=(255, 255, 255, 200), width=max(1, int(10 * s)))
    d.line([(112 * s, 168 * s), (140 * s, 120 * s)], fill=(255, 255, 255, 160), width=max(1, int(7 * s)))
    return img


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    draw().save(OUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(OUT)
