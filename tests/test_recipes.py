import tempfile
import unittest

from recipes import RecipeFormatError, parse_recipe, render_thermal, scale_quantity, scale_recipe
from recipes.storage import RecipeStore, recipe_category


VALID_RECIPE = """\
title: Pain test
servings: 1 pain
ingredient farine | 100 g | Farine
ingredient eau | 70 g | Eau
step melange | MELANGER | farine, eau
step cuisson | CUIRE | melange | 250 C / 12 min
finish: cuisson
"""


class RecipeEngineTest(unittest.TestCase):
    def test_parses_graph_and_orders_ingredients(self):
        recipe = parse_recipe(VALID_RECIPE)
        self.assertEqual([item.id for item in recipe.ordered_ingredients()], ["farine", "eau"])
        self.assertEqual(recipe.operation_depth(recipe.finish), 2)

    def test_rejects_unknown_input(self):
        with self.assertRaises(RecipeFormatError):
            parse_recipe(VALID_RECIPE.replace("farine, eau", "farine, levure"))

    def test_rejects_cycle(self):
        source = VALID_RECIPE.replace(
            "step melange | MELANGER | farine, eau",
            "step melange | MELANGER | cuisson, eau",
        )
        with self.assertRaises(RecipeFormatError):
            parse_recipe(source)

    def test_rejects_a_node_reused_by_two_branches(self):
        source = """\
title: Partage ambigu
ingredient eau | 100 g | Eau
ingredient farine | 100 g | Farine
step branche1 | MELANGER | eau, farine
step branche2 | CHAUFFER | eau
step fin | REUNIR | branche1, branche2
finish: fin
"""
        with self.assertRaisesRegex(RecipeFormatError, "portions séparées"):
            parse_recipe(source)

    def test_renders_exact_thermal_width(self):
        image = render_thermal(parse_recipe(VALID_RECIPE))
        self.assertEqual(image.width, 384)
        self.assertEqual(image.mode, "1")

    def test_accepts_and_renders_six_operation_levels(self):
        source = """\
title: Processus long
ingredient base | 100 g | Base
step s1 | ETAPE 1 | base
step s2 | ETAPE 2 | s1
step s3 | ETAPE 3 | s2
step s4 | ETAPE 4 | s3
step s5 | ETAPE 5 | s4
step s6 | ETAPE 6 | s5
finish: s6
"""
        recipe = parse_recipe(source)
        self.assertEqual(recipe.operation_depth(recipe.finish), 6)
        self.assertEqual(render_thermal(recipe).width, 384)

    def test_long_title_increases_header_height(self):
        short = render_thermal(parse_recipe(VALID_RECIPE))
        long_source = VALID_RECIPE.replace(
            "title: Pain test", "title: Shokupan Pullman express au tangzhong"
        )
        long = render_thermal(parse_recipe(long_source))
        self.assertGreater(long.height, short.height)

    def test_store_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RecipeStore(directory)
            store.save("pain-test", VALID_RECIPE)
            source, recipe = store.read("pain-test")
            self.assertIn("Pain test", source)
            self.assertEqual(recipe.title, "Pain test")
            self.assertTrue(store.list()[0]["valid"])

    def test_scales_simple_range_and_decimal_quantities(self):
        self.assertEqual(scale_quantity("100 g", 1.5), "150 g")
        self.assertEqual(scale_quantity("135 à 145 g", 2), "270 à 290 g")
        self.assertEqual(scale_quantity("1,5 pincée", 2), "3 pincée")
        self.assertEqual(scale_quantity("quantité non définie", 4),
                         "quantité non définie")

    def test_scaled_recipe_keeps_graph_and_scales_every_ingredient(self):
        recipe = scale_recipe(parse_recipe(VALID_RECIPE), 2.5)
        self.assertEqual(recipe.ingredients["farine"].quantity, "250 g")
        self.assertEqual(recipe.ingredients["eau"].quantity, "175 g")
        self.assertEqual(recipe.finish, "cuisson")

    def test_recipe_categories_are_touch_navigation_friendly(self):
        self.assertEqual(recipe_category("Shokupan Pullman"), "Pains")
        self.assertEqual(recipe_category("Brioche au lait"), "Brioches")
        self.assertEqual(recipe_category("Tarte rhubarbe"), "Tartes")


if __name__ == "__main__":
    unittest.main()
