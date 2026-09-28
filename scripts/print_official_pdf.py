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

PRINT_WIDTH = 384
LANDSCAPE_HEIGHT = 384
COLUMN_WIDTH = 340
MARGIN = 16


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
    title_font = font(28, bold=True)
    label_font = font(14, bold=True)
    body_font = font(17, mono=True)
    heading_font = font(19, bold=True)
    probe = Image.new("L", (COLUMN_WIDTH, 10), 255)
    draw = ImageDraw.Draw(probe)
    rows = []
    previous_blank = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            if rows and not previous_blank:
                rows.append(("", body_font, 11))
            previous_blank = True
            continue
        previous_blank = False
        used_font = heading_font if is_heading(stripped) else body_font
        for line in wrap_pixels(draw, stripped, used_font, COLUMN_WIDTH - 2 * MARGIN):
            rows.append((line, used_font, 27 if used_font == heading_font else 24))

    content_top = 92
    content_bottom = LANDSCAPE_HEIGHT - 26
    columns = [[]]
    used_height = content_top
    for row in rows:
        if used_height + row[2] > content_bottom and columns[-1]:
            columns.append([])
            used_height = content_top
        columns[-1].append(row)
        used_height += row[2]

    width = max(700, len(columns) * COLUMN_WIDTH)
    image = Image.new("L", (width, LANDSCAPE_HEIGHT), 255)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width - 1, 74), fill=0)
    draw.text((MARGIN, 8), "DOCUMENT BANCAIRE", font=label_font, fill=255)
    draw.text((MARGIN, 32), title, font=title_font, fill=255)
    draw.line((MARGIN, 82, width - MARGIN, 82), fill=0, width=2)
    for column_index, column in enumerate(columns):
        x = column_index * COLUMN_WIDTH + MARGIN
        y = content_top
        if column_index:
            divider = column_index * COLUMN_WIDTH
            draw.line((divider, content_top, divider, content_bottom), fill=160, width=1)
        for line, used_font, step in column:
            if line:
                draw.text((x, y), line, font=used_font, fill=0)
            y += step
    footer = "Édité depuis le document PDF original"
    draw.text((MARGIN, LANDSCAPE_HEIGHT - 21), footer, font=label_font, fill=0)
    ticket = image.convert("1", dither=Image.Dither.FLOYDSTEINBERG).rotate(90, expand=True)
    if ticket.width != PRINT_WIDTH:
        raise ValueError(f"Largeur thermique invalide : {ticket.width}")
    return ticket


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
