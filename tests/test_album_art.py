import unittest

from PIL import Image

from scripts.print_album_art import render_album_ticket


class AlbumArtRendererTest(unittest.TestCase):
    def test_render_is_thermal_width_and_monochrome(self):
        ticket = render_album_ticket(
            Image.new("RGB", (600, 600), "navy"),
            "Un titre d'album assez long pour revenir à la ligne",
            "Un artiste",
            "Un morceau",
            "2024",
            "21:37",
        )
        self.assertEqual(ticket.width, 384)
        self.assertEqual(ticket.mode, "1")
        self.assertGreater(ticket.height, 400)


if __name__ == "__main__":
    unittest.main()
