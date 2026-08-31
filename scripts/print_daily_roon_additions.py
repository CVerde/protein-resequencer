#!/usr/bin/env python3
"""Imprime le ticket quotidien des albums ajoutés à Roon."""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import printer


WIDTH = 384
MARGIN = 10
COVER_SIZE = 340


def load_font(size, bold=False):
    names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for name in names:
        if os.path.exists(name):
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def format_date(value):
    months = ["janvier", "février", "mars", "avril", "mai", "juin",
              "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    date = datetime.date.fromisoformat(value)
    return f"{date.day} {months[date.month - 1]} {date.year}"


def wrap_pixels(draw, text, font, max_width, max_lines=3):
    words = str(text or "").split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:max_lines] or [""]


def prepare_cover(path):
    if path and Path(path).exists():
        with Image.open(path) as source:
            cover = ImageOps.exif_transpose(source).convert("RGB")
            cover.thumbnail((COVER_SIZE, COVER_SIZE), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (COVER_SIZE, COVER_SIZE), "white")
            canvas.paste(cover, ((COVER_SIZE - cover.width) // 2,
                                 (COVER_SIZE - cover.height) // 2))
            return ImageOps.autocontrast(canvas.convert("L"), cutoff=1)
    canvas = Image.new("L", (COVER_SIZE, COVER_SIZE), 255)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, COVER_SIZE - 1, COVER_SIZE - 1), outline=0, width=2)
    draw.line((0, 0, COVER_SIZE - 1, COVER_SIZE - 1), fill=0, width=2)
    draw.line((COVER_SIZE - 1, 0, 0, COVER_SIZE - 1), fill=0, width=2)
    return canvas


def render_ticket(report):
    title_font = load_font(30, bold=True)
    date_font = load_font(22)
    album_font = load_font(21, bold=True)
    artist_font = load_font(18)
    probe = ImageDraw.Draw(Image.new("L", (WIDTH, 10), 255))
    blocks = []
    for album in report.get("albums", []):
        title = str(album.get("title") or "")
        year = album.get("year")
        if year:
            title += f" ({year})"
        title_lines = wrap_pixels(probe, title, album_font, WIDTH - 2 * MARGIN)
        artist_lines = wrap_pixels(probe, album.get("artist"), artist_font,
                                   WIDTH - 2 * MARGIN, max_lines=2)
        height = COVER_SIZE + 12 + len(title_lines) * 27 + len(artist_lines) * 23 + 24
        blocks.append((album, title_lines, artist_lines, height))
    height = 18 + 40 + 31 + 24 + sum(block[3] for block in blocks) + 24
    canvas = Image.new("L", (WIDTH, height), 255)
    draw = ImageDraw.Draw(canvas)
    y = 14
    for text, font, step in (("Ajouté aujourd'hui", title_font, 40),
                             (format_date(report["date"]), date_font, 31)):
        box = draw.textbbox((0, 0), text, font=font)
        draw.text(((WIDTH - (box[2] - box[0])) // 2, y), text, font=font, fill=0)
        y += step
    y += 24
    for album, title_lines, artist_lines, _ in blocks:
        cover = prepare_cover(album.get("cover"))
        canvas.paste(cover, ((WIDTH - COVER_SIZE) // 2, y))
        y += COVER_SIZE + 12
        for line in title_lines:
            box = draw.textbbox((0, 0), line, font=album_font)
            draw.text(((WIDTH - (box[2] - box[0])) // 2, y), line,
                      font=album_font, fill=0)
            y += 27
        for line in artist_lines:
            box = draw.textbbox((0, 0), line, font=artist_font)
            draw.text(((WIDTH - (box[2] - box[0])) // 2, y), line,
                      font=artist_font, fill=0)
            y += 23
        y += 24
    return canvas.crop((0, 0, WIDTH, min(y + 20, height))).convert(
        "1", dither=Image.Dither.FLOYDSTEINBERG).rotate(180)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    ticket = render_ticket(report)
    if args.output:
        ticket.save(args.output)
        return
    if not report.get("albums"):
        return
    if not printer.is_available():
        raise SystemExit("Imprimante indisponible")
    printer.print_image(ticket)
    printer.feed(7)


if __name__ == "__main__":
    main()
