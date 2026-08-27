"""Rendu TRN monochrome optimisé pour une tête thermique de 384 dots."""

import os
import textwrap

from PIL import Image, ImageDraw, ImageFont


WIDTH = 384
MARGIN = 4
HEADER_WIDTH = 132
ROW_HEIGHT = 62


def _font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _ascii(value):
    # Le texte est rasterisé par Pillow : les accents et symboles sont conservés.
    return str(value)


def _wrapped(draw, box, text, font, max_chars, center=True):
    x0, y0, x1, y1 = box
    lines = textwrap.wrap(_ascii(text), width=max(3, max_chars)) or [""]
    line_height = max(11, font.size + 1 if hasattr(font, "size") else 12)
    lines = lines[:max(1, (y1 - y0 - 4) // line_height)]
    y = y0 + max(2, ((y1 - y0) - len(lines) * line_height) // 2)
    for line in lines:
        bounds = draw.textbbox((0, 0), line, font=font)
        x = x0 + 3 if not center else x0 + max(2, ((x1 - x0) - (bounds[2] - bounds[0])) // 2)
        draw.text((x, y), line, font=font, fill=0)
        y += line_height


def render_thermal(recipe):
    ingredients = recipe.ordered_ingredients()
    depth = recipe.operation_depth(recipe.finish)
    title_font, meta_font = _font(22, True), _font(13)
    body_bold = _font(12, True)
    title_lines = textwrap.wrap(recipe.title, width=30) or [recipe.title]
    title_height = max(30, len(title_lines) * 25)
    prep_blocks = [textwrap.wrap(f"PREP: {item}", width=50) or [item] for item in recipe.prep]
    prep_heights = [max(18, len(lines) * 15) for lines in prep_blocks]
    header_height = 8 + title_height + (18 if recipe.servings else 0) + sum(prep_heights) + 8
    table_top = header_height
    height = table_top + len(ingredients) * ROW_HEIGHT + 12
    image = Image.new("1", (WIDTH, height), 1)
    draw = ImageDraw.Draw(image)

    _wrapped(draw, (MARGIN, 2, WIDTH - MARGIN, 2 + title_height), recipe.title, title_font, 30)
    y = 2 + title_height
    if recipe.servings:
        _wrapped(draw, (MARGIN, y, WIDTH - MARGIN, y + 18), f"Pour {recipe.servings}", meta_font, 48)
        y += 18
    for prep, block_height in zip(recipe.prep, prep_heights):
        _wrapped(draw, (MARGIN, y, WIDTH - MARGIN, y + block_height), f"PREP: {prep}", meta_font, 50, False)
        y += block_height
    draw.line((MARGIN, table_top - 3, WIDTH - MARGIN, table_top - 3), fill=0, width=2)

    row_index = {ingredient.id: index for index, ingredient in enumerate(ingredients)}
    for index, ingredient in enumerate(ingredients):
        top = table_top + index * ROW_HEIGHT
        bottom = top + ROW_HEIGHT
        draw.rectangle((MARGIN, top, HEADER_WIDTH, bottom), outline=0, width=1)
        label = f"{ingredient.quantity}\n{ingredient.name}"
        _wrapped(draw, (MARGIN + 1, top + 1, HEADER_WIDTH - 1, bottom - 1),
                 label, body_bold, 19, False)

    operation_width = (WIDTH - MARGIN - HEADER_WIDTH) / depth
    operation_font = _font(13 if operation_width >= 48 else 10)
    operations = sorted(recipe.operations.values(), key=lambda item: recipe.operation_depth(item.id))
    for operation in operations:
        column = recipe.operation_depth(operation.id) - 1
        ingredient_ids = recipe.ingredient_ids(operation.id)
        start = min(row_index[item] for item in ingredient_ids)
        end = max(row_index[item] for item in ingredient_ids)
        left = round(HEADER_WIDTH + column * operation_width)
        right = round(HEADER_WIDTH + (column + 1) * operation_width)
        top = table_top + start * ROW_HEIGHT
        bottom = table_top + (end + 1) * ROW_HEIGHT
        draw.rectangle((left, top, right, bottom), outline=0, width=1)
        label = operation.action
        if operation.details:
            label += "\n" + operation.details
        chars = max(4, int((right - left) / (7 if operation_width >= 48 else 5.5)))
        _wrapped(draw, (left + 1, top + 1, right - 1, bottom - 1), label, operation_font, chars)

    return image
