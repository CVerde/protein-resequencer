#!/usr/bin/env python3
"""Imprime le compte rendu quotidien des écoutes Roon."""

import argparse
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import printer


WIDTH = 384
MARGIN = 10


def load_font(size, bold=False):
    names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for name in names:
        if os.path.exists(name):
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def wrap_pixels(draw, text, font, max_width):
    words = str(text).split()
    if not words:
        return [""]
    lines, current = [], words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def format_entry(entry):
    year = entry.get("year") or "année inconnue"
    return (f'{entry["time"]} -  {entry["title"]}, sur {entry["album"]}, '
            f'{year} par {entry["artist"]}')


def render_report(report):
    font = load_font(24)
    header_font = load_font(30, bold=True)
    probe = Image.new("L", (WIDTH, 10), 255)
    draw = ImageDraw.Draw(probe)
    date = report["date"].split("-")
    heading = f"ÉCOUTES DU {date[2]}/{date[1]}/{date[0]}"
    entries = report.get("tracks", [])
    blocks = [wrap_pixels(draw, format_entry(entry), font, WIDTH - 2 * MARGIN)
              for entry in entries]
    if not blocks:
        blocks = [["Aucun titre diffusé."]]
    height = 18 + 38 + 12 + sum(len(lines) * 31 + 15 for lines in blocks) + 18
    canvas = Image.new("L", (WIDTH, height), 255)
    draw = ImageDraw.Draw(canvas)
    box = draw.textbbox((0, 0), heading, font=header_font)
    draw.text(((WIDTH - (box[2] - box[0])) // 2, 12), heading, font=header_font, fill=0)
    y = 62
    for lines in blocks:
        for line in lines:
            draw.text((MARGIN, y), line, font=font, fill=0)
            y += 31
        y += 15
    return canvas.convert("1", dither=Image.Dither.FLOYDSTEINBERG).rotate(180)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", help="Fichier JSON du rapport quotidien")
    parser.add_argument("--output", help="Enregistre un aperçu PNG")
    args = parser.parse_args()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    ticket = render_report(report)
    if args.output:
        ticket.save(args.output)
        return
    if not printer.is_available():
        raise SystemExit("Imprimante indisponible")
    printer.print_image(ticket)
    printer.feed(7)


if __name__ == "__main__":
    main()
