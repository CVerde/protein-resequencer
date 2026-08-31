"""Stockage local et sûr des fichiers de recettes .trn."""

import os
import re
import tempfile
from pathlib import Path

from .parser import RecipeFormatError, parse_recipe


SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
DEFAULT_DIRECTORY = Path(__file__).resolve().parents[1] / "recipes_data"


def recipe_category(title):
    value = title.casefold()
    if any(word in value for word in ("shokupan", "pain", "focaccia")):
        return "Pains"
    if any(word in value for word in ("brioche", "kouign", "croissant")):
        return "Brioches"
    if any(word in value for word in ("tarte", "tartel")):
        return "Tartes"
    if any(word in value for word in ("cake", "madeleine", "gâteau", "gateau")):
        return "Gâteaux"
    return "Autres"


class RecipeStore:
    def __init__(self, directory=None):
        self.directory = Path(directory or os.environ.get("RECIPES_DIRECTORY", DEFAULT_DIRECTORY))
        self.directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def validate_slug(slug):
        if not SLUG_PATTERN.fullmatch(slug or ""):
            raise ValueError("Nom de fichier invalide (a-z, 0-9, _ ou -, 64 caractères max)")
        return slug

    def path_for(self, slug):
        return self.directory / f"{self.validate_slug(slug)}.trn"

    def list(self):
        result = []
        for path in sorted(self.directory.glob("*.trn")):
            entry = {"slug": path.stem, "filename": path.name}
            try:
                recipe = parse_recipe(path.read_text(encoding="utf-8"))
                entry.update({
                    "title": recipe.title,
                    "servings": recipe.servings,
                    "category": recipe_category(recipe.title),
                    "ingredients": len(recipe.ingredients),
                    "steps": len(recipe.operations),
                    "valid": True,
                })
            except (OSError, RecipeFormatError) as exc:
                entry.update({"title": path.stem, "valid": False, "errors": getattr(exc, "errors", [str(exc)])})
            result.append(entry)
        return result

    def read(self, slug):
        path = self.path_for(slug)
        source = path.read_text(encoding="utf-8")
        return source, parse_recipe(source)

    def save(self, slug, source):
        path = self.path_for(slug)
        recipe = parse_recipe(source)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{slug}-", suffix=".trn", dir=self.directory)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                output.write(source.rstrip() + "\n")
            os.replace(temporary, path)
        except Exception:
            if os.path.exists(temporary):
                os.unlink(temporary)
            raise
        return recipe

    def delete(self, slug):
        path = self.path_for(slug)
        path.unlink()
