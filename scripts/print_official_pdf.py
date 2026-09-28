#!/usr/bin/env python3
"""Compose et imprime une transcription thermique lisible d'un PDF administratif."""

import argparse
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import printer

WIDTH = 384
MARGIN = 12


def font(size, bold=False, mono=False):
    if mono:
        name = "DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf"
    else:
        name = "DejaVuSansCondensed-Bold.ttf" if bold else "DejaVuSansCondensed.ttf"
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu") / name,
        Path("/usr/share/fonts/truetype/dejavu") /
        ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def extract_text(pdf):
    result = subprocess.run(
        ["pdftotext", "-layout", "-nopgbrk", str(pdf), "-"],
        check=True, capture_output=True, text=True, encoding="utf-8",
    )
    return result.stdout.replace("\f", "").strip()


def is_heading(line):
    letters = "".join(character for character in line if character.isalpha())
    return bool(letters) and len(letters) >= 4 and letters.upper() == letters


def wrap_pixels(draw, line, used_font, width):
    line = re.sub(r"[ \t]{2,}", "   ", line.strip())
    if not line:
        return [""]
    if draw.textlength(line, font=used_font) <= width:
        return [line]
    words = line.split()
    output, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or draw.textlength(candidate, font=used_font) <= width:
            current = candidate
        else:
            output.append(current)
            current = word
    if current:
        output.append(current)
    return output


def render_document(text, title="RELEVÉ D’IDENTITÉ BANCAIRE"):
    title_font = font(23, bold=True)
    label_font = font(12, bold=True)
    body_font = font(13, mono=True)
    heading_font = font(14, bold=True)
    probe = Image.new("L", (WIDTH, 10), 255)
    draw = ImageDraw.Draw(probe)
    rows = []
    previous_blank = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            if rows and not previous_blank:
                rows.append(("", body_font, 9))
            previous_blank = True
            continue
        previous_blank = False
        used_font = heading_font if is_heading(stripped) else body_font
        for line in wrap_pixels(draw, stripped, used_font, WIDTH - 2 * MARGIN):
            rows.append((line, used_font, 19 if used_font == heading_font else 18))

    header_height = 96
    height = header_height + sum(step for _, _, step in rows) + 36
    image = Image.new("L", (WIDTH, height), 255)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH - 1, 78), fill=0)
    draw.text((MARGIN, 10), "DOCUMENT BANCAIRE", font=label_font, fill=255)
    title_lines = wrap_pixels(draw, title, title_font, WIDTH - 2 * MARGIN)
    y = 30
    for line in title_lines[:2]:
        draw.text((MARGIN, y), line, font=title_font, fill=255)
        y += 27
    draw.line((MARGIN, 87, WIDTH - MARGIN, 87), fill=0, width=2)
    y = header_height
    for line, used_font, step in rows:
        if line:
            draw.text((MARGIN, y), line, font=used_font, fill=0)
        y += step
    draw.line((MARGIN, y + 4, WIDTH - MARGIN, y + 4), fill=0, width=1)
    draw.text((MARGIN, y + 10), "Édité depuis le document PDF original", font=label_font, fill=0)
    return image.crop((0, 0, WIDTH, y + 32)).convert(
        "1", dither=Image.Dither.FLOYDSTEINBERG).rotate(180)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--title", default="RELEVÉ D’IDENTITÉ BANCAIRE")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    ticket = render_document(extract_text(args.pdf), args.title)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        ticket.save(args.output)
        print(f"Aperçu créé : {args.output}")
        return
    if not printer.is_available():
        raise SystemExit("Imprimante indisponible")
    printer.print_image(ticket)
    printer.feed(7)
    print("Document imprimé.")


if __name__ == "__main__":
    main()
