#!/usr/bin/env python3
"""Imprime le compte rendu quotidien des écoutes Roon."""

import argparse
import datetime
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
    year = entry.get("year")
    dated = f', {year}' if year else ''
    return (f'{entry["time"]} -  {entry["title"]}, sur {entry["album"]}'
            f'{dated} par {entry["artist"]}')


def format_long_date(value):
    weekdays = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    months = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
              "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    date = datetime.date.fromisoformat(value)
    return f"{weekdays[date.weekday()]} {date.day} {months[date.month - 1]} {date.year}"


def format_total_duration(entries):
    minutes = round(sum(float(entry.get("duration") or 0) for entry in entries) / 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}min"


def render_report(report):
    font = load_font(24)
    header_font = load_font(26, bold=True)
    summary_font = load_font(21, bold=True)
    probe = Image.new("L", (WIDTH, 10), 255)
    draw = ImageDraw.Draw(probe)
    entries = report.get("tracks", [])
    heading = format_long_date(report["date"])
    count = len(entries)
    summary = f"{count} track{'s' if count != 1 else ''} lu{'s' if count != 1 else ''}, total : {format_total_duration(entries)}"
    heading_lines = wrap_pixels(draw, heading, header_font, WIDTH - 2 * MARGIN)
    summary_lines = wrap_pixels(draw, summary, summary_font, WIDTH - 2 * MARGIN)
    blocks = [wrap_pixels(draw, format_entry(entry), font, WIDTH - 2 * MARGIN)
              for entry in entries]
    if not blocks:
        blocks = [["Aucun titre diffusé."]]
    header_height = len(heading_lines) * 35 + len(summary_lines) * 31 + 2 * 31 + 18
    height = 12 + header_height + sum(len(lines) * 31 + 15 for lines in blocks) + 18
    canvas = Image.new("L", (WIDTH, height), 255)
    draw = ImageDraw.Draw(canvas)
    y = 12
    for line in heading_lines:
        box = draw.textbbox((0, 0), line, font=header_font)
        draw.text(((WIDTH - (box[2] - box[0])) // 2, y), line, font=header_font, fill=0)
        y += 35
    for line in summary_lines:
        box = draw.textbbox((0, 0), line, font=summary_font)
        draw.text(((WIDTH - (box[2] - box[0])) // 2, y), line, font=summary_font, fill=0)
        y += 31
    y += 2 * 31
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
