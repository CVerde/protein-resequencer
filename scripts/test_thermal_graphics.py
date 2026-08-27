#!/usr/bin/env python3
"""Test graphique autonome pour l'imprimante thermique EM5820 (384 dots)."""

import argparse
import os
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 384
DEFAULT_DEVICE = "/dev/usb/lp0"
DEFAULT_OUTPUT = "/tmp/em5820-graphics-test.png"


def load_font(size, bold=False):
    names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationMono-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
    ]
    for name in names:
        if os.path.exists(name):
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def centered(draw, y, text, font, fill=0):
    box = draw.textbbox((0, 0), text, font=font)
    x = (WIDTH - (box[2] - box[0])) // 2
    draw.text((x, y), text, font=font, fill=fill)


def create_test_image():
    image = Image.new("1", (WIDTH, 920), 1)
    draw = ImageDraw.Draw(image)
    normal = load_font(18)
    small = load_font(14)
    bold = load_font(21, bold=True)

    centered(draw, 8, "EM5820 - TEST 384 DOTS", bold)
    draw.line((0, 40, WIDTH - 1, 40), fill=0, width=1)
    draw.line((0, 48, WIDTH - 1, 48), fill=0, width=2)
    draw.line((0, 58, WIDTH - 1, 58), fill=0, width=4)

    # Cadre bord à bord et lignes verticales permettant de vérifier la largeur.
    draw.rectangle((0, 72, WIDTH - 1, 166), outline=0, width=1)
    for x in range(0, WIDTH, 48):
        draw.line((x, 72, x, 166), fill=0, width=1)
        draw.text((x + 2, 80), str(x), font=small, fill=0)
    draw.line((WIDTH - 1, 72, WIDTH - 1, 166), fill=0, width=1)
    centered(draw, 130, "0       REGLE EN DOTS       383", small)

    # Traits et rectangles de plusieurs épaisseurs.
    y = 184
    for thickness in (1, 2, 3, 4, 6, 8):
        draw.line((18, y, 365, y), fill=0, width=thickness)
        draw.text((4, y + 5), f"{thickness} px", font=small, fill=0)
        y += 28
    draw.rectangle((18, 354, 112, 416), outline=0, width=1)
    draw.rectangle((144, 354, 238, 416), outline=0, width=3)
    draw.rectangle((270, 354, 365, 416), outline=0, width=6)

    centered(draw, 438, "FAUX DIAGRAMME RECETTE", bold)
    draw.line((20, 470, 363, 470), fill=0, width=2)

    # Diagramme volontairement rasterisé : aucune dépendance aux glyphes internes.
    draw.text((8, 494), "100 g FARINE", font=normal, fill=0)
    draw.text((8, 554), " 70 g EAU", font=normal, fill=0)
    draw.line((145, 507, 196, 507), fill=0, width=2)
    draw.line((145, 567, 196, 567), fill=0, width=2)
    draw.line((196, 507, 196, 567), fill=0, width=2)
    draw.line((196, 537, 224, 537), fill=0, width=2)
    draw.polygon(((224, 537), (214, 532), (214, 542)), fill=0)
    draw.text((232, 524), "MELANGER", font=normal, fill=0)

    draw.line((296, 562, 296, 610), fill=0, width=2)
    draw.polygon(((296, 610), (291, 600), (301, 600)), fill=0)
    centered(draw, 620, "PETRIR", bold)
    centered(draw, 648, "8 min", normal)
    draw.line((192, 680, 192, 724), fill=0, width=2)
    draw.polygon(((192, 724), (187, 714), (197, 714)), fill=0)
    centered(draw, 736, "CUIRE", bold)
    centered(draw, 766, "250 C", normal)
    centered(draw, 792, "12 min", normal)

    draw.line((0, 840, WIDTH - 1, 840), fill=0, width=1)
    centered(draw, 852, "BORD GAUCHE  |  BORD DROIT", small)
    draw.rectangle((0, 884, WIDTH - 1, 919), outline=0, width=1)
    return image


def raster_command(image):
    """Encode une image 1-bit en commande ESC/POS GS v 0."""
    image = image.convert("1")
    width_bytes = (image.width + 7) // 8
    data = bytearray()
    pixels = image.load()
    for y in range(image.height):
        for byte_x in range(width_bytes):
            value = 0
            for bit in range(8):
                x = byte_x * 8 + bit
                if x < image.width and pixels[x, y] == 0:
                    value |= 0x80 >> bit
            data.append(value)
    return (
        b"\x1d\x76\x30\x00"
        + bytes((width_bytes & 0xFF, width_bytes >> 8, image.height & 0xFF, image.height >> 8))
        + data
    )


def print_image(device, image, stripe_height=128):
    with open(device, "wb", buffering=0) as printer:
        printer.write(b"\x1b@\x1ba\x00")
        for top in range(0, image.height, stripe_height):
            stripe = image.crop((0, top, image.width, min(top + stripe_height, image.height)))
            printer.write(raster_command(stripe))
            time.sleep(0.08)
        printer.write(b"\n\n\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default=DEFAULT_DEVICE)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--no-print", action="store_true")
    args = parser.parse_args()

    image = create_test_image()
    output = Path(args.output)
    image.save(output)
    print(f"Aperçu enregistré : {output}")

    if not args.no_print:
        if not os.path.exists(args.device):
            raise SystemExit(f"Imprimante absente : {args.device}")
        print_image(args.device, image)
        print(f"Test graphique envoyé à {args.device}")


if __name__ == "__main__":
    main()
