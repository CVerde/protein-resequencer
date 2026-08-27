import tempfile
import unittest
from unittest.mock import patch

import app as app_module
from recipes.storage import RecipeStore
from test_recipes import VALID_RECIPE


class RecipeApiTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.previous_store = app_module.recipe_store
        app_module.recipe_store = RecipeStore(self.temporary.name)
        self.client = app_module.app.test_client()

    def tearDown(self):
        app_module.recipe_store = self.previous_store
        self.temporary.cleanup()

    def test_create_list_read_and_preview(self):
        response = self.client.put('/api/recipes/pain', json={'source': VALID_RECIPE})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/recipes').json[0]['title'], 'Pain test')
        self.assertEqual(self.client.get('/api/recipes/pain').status_code, 200)
        preview = self.client.get('/api/recipes/pain/preview.png')
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.mimetype, 'image/png')
        self.assertTrue(preview.data.startswith(b'\x89PNG'))

    def test_invalid_recipe_is_not_saved(self):
        response = self.client.put('/api/recipes/invalide', json={'source': 'title: Invalide'})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(app_module.recipe_store.path_for('invalide').exists())

    @patch.object(app_module.printer, 'is_available', return_value=False)
    def test_print_reports_unavailable_printer(self, _available):
        app_module.recipe_store.save('pain', VALID_RECIPE)
        response = self.client.post('/api/recipes/pain/print')
        self.assertEqual(response.status_code, 503)


if __name__ == '__main__':
    unittest.main()
