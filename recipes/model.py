from dataclasses import dataclass, field


@dataclass(frozen=True)
class Ingredient:
    id: str
    quantity: str
    name: str


@dataclass(frozen=True)
class Operation:
    id: str
    action: str
    inputs: tuple[str, ...]
    details: str = ""


@dataclass
class Recipe:
    title: str
    servings: str = ""
    source: str = ""
    prep: list[str] = field(default_factory=list)
    ingredients: dict[str, Ingredient] = field(default_factory=dict)
    operations: dict[str, Operation] = field(default_factory=dict)
    finish: str = ""

    @property
    def nodes(self):
        return {**self.ingredients, **self.operations}

    def ingredient_ids(self, node_id):
        seen = set()

        def visit(current):
            if current in self.ingredients:
                return [current]
            if current in seen:
                return []
            seen.add(current)
            result = []
            for child in self.operations[current].inputs:
                for ingredient_id in visit(child):
                    if ingredient_id not in result:
                        result.append(ingredient_id)
            return result

        return visit(node_id)

    def ordered_ingredients(self):
        ordered = self.ingredient_ids(self.finish)
        return [self.ingredients[item_id] for item_id in ordered]

    def operation_depth(self, operation_id):
        operation = self.operations[operation_id]
        child_depths = [self.operation_depth(item) if item in self.operations else 0
                        for item in operation.inputs]
        return 1 + max(child_depths, default=0)

    def to_dict(self):
        return {
            "title": self.title,
            "servings": self.servings,
            "source": self.source,
            "prep": self.prep,
            "ingredients": [vars(item) for item in self.ordered_ingredients()],
            "operations": [
                {**vars(item), "inputs": list(item.inputs)}
                for item in self.operations.values()
            ],
            "finish": self.finish,
            "depth": self.operation_depth(self.finish),
        }
