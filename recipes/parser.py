"""Parseur du format texte .trn."""

import re

from .model import Ingredient, Operation, Recipe


ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")


class RecipeFormatError(ValueError):
    def __init__(self, errors):
        self.errors = errors if isinstance(errors, list) else [str(errors)]
        super().__init__("\n".join(self.errors))


def _parts(value, expected, line_number):
    parts = [part.strip() for part in value.split("|")]
    if len(parts) < expected:
        raise RecipeFormatError(
            f"Ligne {line_number}: {expected} champs séparés par | sont requis"
        )
    return parts


def parse_recipe(source):
    recipe = Recipe(title="")
    errors = []

    for line_number, raw_line in enumerate(source.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            if ":" in line and line.split(":", 1)[0].lower() in {
                "title", "servings", "source", "prep", "finish"
            }:
                key, value = (part.strip() for part in line.split(":", 1))
                key = key.lower()
                if key == "prep":
                    recipe.prep.append(value)
                elif key == "finish":
                    recipe.finish = value
                else:
                    setattr(recipe, key, value)
                continue

            keyword, _, value = line.partition(" ")
            if keyword.lower() == "ingredient":
                parts = _parts(value, 3, line_number)
                item_id, quantity, name = parts[:3]
                _validate_id(item_id, line_number)
                if item_id in recipe.nodes:
                    raise RecipeFormatError(f"Ligne {line_number}: identifiant dupliqué {item_id}")
                recipe.ingredients[item_id] = Ingredient(item_id, quantity, name)
            elif keyword.lower() == "step":
                parts = _parts(value, 3, line_number)
                item_id, action, raw_inputs = parts[:3]
                details = " | ".join(parts[3:]) if len(parts) > 3 else ""
                _validate_id(item_id, line_number)
                if item_id in recipe.nodes:
                    raise RecipeFormatError(f"Ligne {line_number}: identifiant dupliqué {item_id}")
                inputs = tuple(item.strip() for item in raw_inputs.split(",") if item.strip())
                if not action or not inputs:
                    raise RecipeFormatError(f"Ligne {line_number}: action et entrées requises")
                recipe.operations[item_id] = Operation(item_id, action, inputs, details)
            else:
                raise RecipeFormatError(f"Ligne {line_number}: instruction inconnue")
        except RecipeFormatError as exc:
            errors.extend(exc.errors)

    errors.extend(_validate_recipe(recipe))
    if errors:
        raise RecipeFormatError(errors)
    return recipe


def _validate_id(item_id, line_number):
    if not ID_PATTERN.fullmatch(item_id):
        raise RecipeFormatError(
            f"Ligne {line_number}: identifiant invalide '{item_id}' (a-z, 0-9, _ ou -)"
        )


def _validate_recipe(recipe):
    errors = []
    if not recipe.title:
        errors.append("Le champ title est requis")
    if not recipe.ingredients:
        errors.append("Au moins un ingredient est requis")
    if not recipe.operations:
        errors.append("Au moins une step est requise")
    if not recipe.finish:
        errors.append("Le champ finish est requis")
    elif recipe.finish not in recipe.operations:
        errors.append("finish doit référencer une step")

    nodes = recipe.nodes
    consumers = {node_id: [] for node_id in nodes}
    for operation in recipe.operations.values():
        for input_id in operation.inputs:
            if input_id not in nodes:
                errors.append(f"{operation.id}: entrée inconnue '{input_id}'")
            else:
                consumers[input_id].append(operation.id)
    for node_id, uses in consumers.items():
        if len(uses) > 1:
            errors.append(
                f"'{node_id}' est utilisé par plusieurs branches ({', '.join(uses)}); "
                "déclarer des portions séparées"
            )

    visiting, visited = set(), set()

    def visit(node_id):
        if node_id in visiting:
            errors.append(f"Cycle détecté autour de '{node_id}'")
            return
        if node_id in visited or node_id not in recipe.operations:
            return
        visiting.add(node_id)
        for child in recipe.operations[node_id].inputs:
            visit(child)
        visiting.remove(node_id)
        visited.add(node_id)

    for operation_id in recipe.operations:
        visit(operation_id)

    if recipe.finish in recipe.operations and not errors:
        reachable = set(recipe.ingredient_ids(recipe.finish))
        unused = set(recipe.ingredients) - reachable
        if unused:
            errors.append("Ingrédients hors du graphe final : " + ", ".join(sorted(unused)))
        reachable_steps = set()

        def collect_steps(node_id):
            if node_id not in recipe.operations or node_id in reachable_steps:
                return
            reachable_steps.add(node_id)
            for child in recipe.operations[node_id].inputs:
                collect_steps(child)

        collect_steps(recipe.finish)
        unused_steps = set(recipe.operations) - reachable_steps
        if unused_steps:
            errors.append("Étapes hors du graphe final : " + ", ".join(sorted(unused_steps)))
        if recipe.operation_depth(recipe.finish) > 7:
            errors.append("La version thermique accepte au maximum 7 niveaux d'opérations")
    return errors
