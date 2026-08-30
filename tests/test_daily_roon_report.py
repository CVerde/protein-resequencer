import unittest

from scripts.print_daily_roon_report import (
    format_entry, format_long_date, format_total_duration, render_report,
)


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
        self.assertEqual(text, "14h07 -  Titre, sur Album, 1993 par Artiste")

    def test_entry_omits_an_unknown_year(self):
        text = format_entry({"time": "14h07", "title": "Titre", "album": "Album",
                             "year": None, "artist": "Artiste"})
        self.assertEqual(text, "14h07 -  Titre, sur Album par Artiste")
        self.assertNotIn("inconnue", text)

    def test_formats_long_french_date_and_total_duration(self):
        self.assertEqual(format_long_date("2008-08-30"), "Samedi 30 Août 2008")
        self.assertEqual(format_total_duration([{"duration": 3600}, {"duration": 125}]),
                         "1h02min")


if __name__ == "__main__":
    unittest.main()
