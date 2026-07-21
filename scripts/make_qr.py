"""Generate the matcha repo QR used by the projector slide.

Developer tool only:

    pip install qrcode
    python scripts/make_qr.py
"""
from pathlib import Path

import qrcode
from qrcode.image.svg import SvgPathImage


URL = "https://github.com/di-omics/bay-hack"
OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "qr.svg"


def main() -> None:
    image = qrcode.make(URL, image_factory=SvgPathImage, box_size=8, border=2)
    image.save(OUTPUT)
    svg = OUTPUT.read_text().replace('fill="#000000"', 'fill="#3c8446"')
    OUTPUT.write_text(svg)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()

