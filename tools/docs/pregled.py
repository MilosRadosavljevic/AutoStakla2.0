"""PDF -> slike strana (mreža po 6) za vizuelni pregled.  pregled.py <pdf> <izlazni_folder> [dpi]"""
import sys
from pathlib import Path

import pymupdf
from PIL import Image

pdf, out = Path(sys.argv[1]), Path(sys.argv[2])
dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 45
out.mkdir(parents=True, exist_ok=True)
for f in out.glob(f"{pdf.stem}_*.png"):
    f.unlink()
doc = pymupdf.open(pdf)
imgs = []
for page in doc:
    pix = page.get_pixmap(dpi=dpi)
    imgs.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
print("strana:", len(imgs))
per = 6
for g in range(0, len(imgs), per):
    chunk = imgs[g:g + per]
    w, h = chunk[0].size
    cols = 3
    rows = (len(chunk) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w + (cols + 1) * 10, rows * h + (rows + 1) * 10), (120, 120, 120))
    for i, im in enumerate(chunk):
        sheet.paste(im, (10 + (i % cols) * (w + 10), 10 + (i // cols) * (h + 10)))
    p = out / f"{pdf.stem}_{g // per + 1:02d}.png"
    sheet.save(p)
    print(p)
