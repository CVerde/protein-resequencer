"""Mise à l'échelle proportionnelle des quantités d'une recette TRN."""

import re
from dataclasses import replace


NUMBER_PATTERN = re.compile(r"(?<![\w])\d+(?:[.,]\d+)?")


def _format_number(value):
    rounded = round(value, 3)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.3f}".rstrip("0").rstrip(".").replace(".", ",")


def scale_quantity(quantity, factor):
    """Multiplie tous les nombres d'une quantité, en conservant son unité."""
    factor = float(factor)
    if not 0.01 <= factor <= 100:
        raise ValueError("Le facteur doit être compris entre 0,01 et 100")

    def substitute(match):
        value = float(match.group(0).replace(",", "."))
        return _format_number(value * factor)

    return NUMBER_PATTERN.sub(substitute, str(quantity))


def scale_recipe(recipe, factor):
    """Retourne une copie de recette dont les ingrédients sont proportionnels."""
    factor = float(factor)
    ingredients = {
        item_id: replace(item, quantity=scale_quantity(item.quantity, factor))
        for item_id, item in recipe.ingredients.items()
    }
    return replace(recipe, ingredients=ingredients)
