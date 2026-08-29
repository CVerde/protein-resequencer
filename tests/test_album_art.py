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

    def test_ticket_is_rotated_180_degrees(self):
        source = Image.new("RGB", (372, 372), "white")
        source.putpixel((1, 1), (0, 0, 0))
        ticket = render_album_ticket(source, "Album", "Artiste")

        # La pochette commence en bas après la rotation du ticket complet.
        self.assertEqual(ticket.getpixel((376, ticket.height - 8)), 0)
        self.assertEqual(ticket.getpixel((7, 7)), 255)


if __name__ == "__main__":
    unittest.main()
