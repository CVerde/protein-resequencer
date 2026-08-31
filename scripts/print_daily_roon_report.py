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
TITLE_MAX_CHARS = 28


def load_font(size, bold=False, italic=False):
    if italic:
        names = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Oblique.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Italic.ttf",
        ]
    else:
        names = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf" if bold else
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
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


def shorten_title(value, limit=TITLE_MAX_CHARS):
    title = str(value)
    return title if len(title) <= limit else title[:limit - 1].rstrip() + "…"


def format_entry(entry):
    return (f'{entry["time"]} · {shorten_title(entry["title"])} · '
            f'{entry["album"]} · {entry["artist"]}')


def truncate_single_line(draw, text, font, max_width):
    if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
        return text
    shortened = text
    while shortened and draw.textbbox((0, 0), shortened + "…", font=font)[2] > max_width:
        shortened = shortened[:-1]
    return shortened.rstrip() + "…"


def styled_entry_runs(draw, entry, max_width, size=12):
    regular = load_font(size)
    italic = load_font(size, italic=True)
    bold = load_font(size, bold=True)
    values = {
        "time": str(entry["time"]),
        "title": shorten_title(entry["title"]),
        "album": str(entry["album"]),
        "artist": str(entry["artist"]),
    }

    def runs():
        return [
            (values["time"] + " · ", regular, False),
            (values["title"], italic, False),
            (" · ", regular, False),
            (values["album"], regular, True),
            (" · ", regular, False),
            (values["artist"], bold, False),
        ]

    def width():
        return sum(draw.textlength(text, font=font) for text, font, _ in runs())

    for field in ("title", "album", "artist"):
        while len(values[field]) > 1 and width() > max_width:
            raw = values[field].removesuffix("…")[:-1].rstrip()
            values[field] = raw + "…"
    return runs()


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
    entry_font = load_font(12)
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
    lines = [styled_entry_runs(draw, entry, WIDTH - 2 * MARGIN) for entry in entries]
    if not lines:
        lines = [[("Aucun titre diffusé.", entry_font, False)]]
    header_height = len(heading_lines) * 35 + len(summary_lines) * 31 + 2 * 31 + 18
    ascent, descent = entry_font.getmetrics()
    line_height = ascent + descent
    height = 12 + header_height + len(lines) * line_height + 18
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
    for runs in lines:
        x = MARGIN
        for text, run_font, underline in runs:
            draw.text((x, y), text, font=run_font, fill=0)
            width = draw.textlength(text, font=run_font)
            if underline and text:
                draw.line((x, y + ascent + 1, x + width, y + ascent + 1), fill=0, width=1)
            x += width
        y += line_height
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
