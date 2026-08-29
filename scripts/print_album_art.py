#!/usr/bin/env python3
"""Prépare et imprime une pochette Roon sur l'EM5820."""

import argparse
import os
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import printer


WIDTH = 384
COVER_SIZE = 372
MARGIN = 6


def load_font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def wrapped_lines(text, width):
    return textwrap.wrap(str(text or "Inconnu"), width=width, break_long_words=True) or ["Inconnu"]


def render_album_ticket(image, album, artist, track="", year="", played_at=""):
    cover = ImageOps.exif_transpose(image).convert("RGB")
    cover.thumbnail((COVER_SIZE, COVER_SIZE), Image.Resampling.LANCZOS)
    cover_canvas = Image.new("RGB", (COVER_SIZE, COVER_SIZE), "white")
    cover_canvas.paste(cover, ((COVER_SIZE - cover.width) // 2, (COVER_SIZE - cover.height) // 2))
    cover_gray = ImageOps.autocontrast(cover_canvas.convert("L"), cutoff=1)

    album_font = load_font(20, bold=True)
    artist_font = load_font(16)
    detail_font = load_font(14)
    album_lines = wrapped_lines(album, 31)[:3]
    artist_lines = wrapped_lines(artist, 38)[:2]
    track_lines = wrapped_lines(track, 42)[:2] if track else []
    info_lines = []
    info_lines.append(f"Année : {year or 'inconnue'}")
    if played_at:
        info_lines.append(f"Diffusé à {played_at}")
    text_height = (10 + len(album_lines) * 24 + len(artist_lines) * 20 +
                   len(track_lines) * 18 + len(info_lines) * 18 + 12)
    canvas = Image.new("L", (WIDTH, MARGIN + COVER_SIZE + text_height), 255)
    canvas.paste(cover_gray, (MARGIN, MARGIN))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((MARGIN, MARGIN, MARGIN + COVER_SIZE - 1, MARGIN + COVER_SIZE - 1), outline=0, width=1)

    y = MARGIN + COVER_SIZE + 8
    for line in album_lines:
        box = draw.textbbox((0, 0), line, font=album_font)
        draw.text(((WIDTH - (box[2] - box[0])) // 2, y), line, font=album_font, fill=0)
        y += 24
    for line in artist_lines:
        box = draw.textbbox((0, 0), line, font=artist_font)
        draw.text(((WIDTH - (box[2] - box[0])) // 2, y), line, font=artist_font, fill=0)
        y += 20
    for line in track_lines:
        display = f"♪ {line}"
        box = draw.textbbox((0, 0), display, font=detail_font)
        draw.text(((WIDTH - (box[2] - box[0])) // 2, y), display, font=detail_font, fill=0)
        y += 18
    for line in info_lines:
        box = draw.textbbox((0, 0), line, font=detail_font)
        draw.text(((WIDTH - (box[2] - box[0])) // 2, y), line, font=detail_font, fill=0)
        y += 18
    ticket = canvas.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    return ticket.rotate(180)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--album", required=True)
    parser.add_argument("--artist", required=True)
    parser.add_argument("--track", default="")
    parser.add_argument("--year", default="")
    parser.add_argument("--played-at", default="")
    parser.add_argument("--output", help="Enregistre un PNG au lieu d'imprimer")
    args = parser.parse_args()

    with Image.open(args.image) as source:
        ticket = render_album_ticket(
            source, args.album, args.artist, args.track, args.year, args.played_at
        )
    if args.output:
        ticket.save(args.output)
        print(f"Aperçu enregistré : {args.output}")
        return
    if not printer.is_available():
        raise SystemExit("Imprimante indisponible")
    printer.print_image(ticket)
    printer.feed(4)
    print(f"Pochette imprimée : {args.artist} — {args.album}")


if __name__ == "__main__":
    main()
