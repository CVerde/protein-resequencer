import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.print_daily_roon_additions import format_date, render_ticket


class DailyRoonAdditionsTest(unittest.TestCase):
    def test_ticket_contains_cover_blocks_and_is_rotated_monochrome(self):
        with tempfile.TemporaryDirectory() as directory:
            cover = Path(directory) / "cover.png"
            Image.new("RGB", (200, 200), "gray").save(cover)
            ticket = render_ticket({"date": "2026-09-01", "albums": [{
                "title": "Album", "artist": "Artiste", "year": None,
                "cover": str(cover),
            }]})
        self.assertEqual(ticket.width, 384)
        self.assertEqual(ticket.mode, "1")
        self.assertGreater(ticket.height, 400)

    def test_date_is_formatted_in_french(self):
        self.assertEqual(format_date("2026-09-01"), "1 septembre 2026")

    def test_missing_year_and_cover_are_accepted(self):
        ticket = render_ticket({"date": "2026-09-01", "albums": [{
            "title": "Album", "artist": "Artiste", "year": None,
        }]})
        self.assertEqual(ticket.width, 384)


if __name__ == "__main__":
    unittest.main()
