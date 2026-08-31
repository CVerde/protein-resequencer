import unittest

from scripts.print_daily_roon_report import (
    format_entry, format_long_date, format_total_duration, load_font,
    render_report, shorten_title, styled_entry_runs, truncate_single_line,
)
from PIL import Image, ImageDraw


class DailyRoonReportTest(unittest.TestCase):
    def test_report_is_thermal_width_monochrome_and_rotated(self):
        report = {"date": "2026-08-30", "tracks": [{
            "time": "14h07", "title": "Un morceau au titre très long",
            "album": "Un album", "year": 1993, "artist": "Un artiste", "duration": 245,
        }]}
        ticket = render_report(report)
        self.assertEqual(ticket.width, 384)
        self.assertEqual(ticket.mode, "1")
        self.assertGreater(ticket.height, 150)

    def test_entry_uses_requested_format(self):
        text = format_entry({"time": "14h07", "title": "Titre", "album": "Album",
                             "year": 1993, "artist": "Artiste"})
        self.assertEqual(text, "14h07 · Titre · Album · Artiste")
        self.assertNotIn("1993", text)

    def test_entry_omits_an_unknown_year(self):
        text = format_entry({"time": "14h07", "title": "Titre", "album": "Album",
                             "year": None, "artist": "Artiste"})
        self.assertEqual(text, "14h07 · Titre · Album · Artiste")
        self.assertNotIn("inconnue", text)

    def test_long_entry_is_fitted_to_one_thermal_line(self):
        draw = ImageDraw.Draw(Image.new("L", (384, 30), 255))
        font = load_font(12)
        text = truncate_single_line(
            draw,
            "17h03 · Un titre vraiment extrêmement long · Un album également très long · Un artiste",
            font,
            364,
        )
        self.assertLessEqual(draw.textbbox((0, 0), text, font=font)[2], 364)

    def test_title_is_limited_to_28_characters(self):
        title = shorten_title("You Make A Mark Like A Calf Branding")
        self.assertEqual(len(title), 28)
        self.assertTrue(title.endswith("…"))

    def test_entry_styles_fit_one_line(self):
        draw = ImageDraw.Draw(Image.new("L", (384, 30), 255))
        runs = styled_entry_runs(draw, {
            "time": "17h03", "title": "Minimal", "album": "Sudden Fictions",
            "artist": "Bo Ningen / Bobby Gillespie",
        }, 364)
        self.assertLessEqual(sum(draw.textlength(text, font=font)
                                 for text, font, _ in runs), 364)
        self.assertTrue(any(text == "Sudden Fictions" and underline
                            for text, _, underline in runs))

    def test_formats_long_french_date_and_total_duration(self):
        self.assertEqual(format_long_date("2008-08-30"), "Samedi 30 Août 2008")
        self.assertEqual(format_total_duration([{"duration": 3600}, {"duration": 125}]),
                         "1h02min")


if __name__ == "__main__":
    unittest.main()
