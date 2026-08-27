import os
import tempfile
import unittest

from PIL import Image

from printer.thermal import ThermalPrinter


class ThermalPrinterTest(unittest.TestCase):
    def setUp(self):
        descriptor, self.path = tempfile.mkstemp()
        os.close(descriptor)
        self.printer = ThermalPrinter(device=self.path, stripe_height=8)

    def tearDown(self):
        os.unlink(self.path)

    def read_output(self):
        with open(self.path, "rb") as output:
            return output.read()

    def test_text_is_transliterated_and_feed_is_escpos(self):
        self.printer.print_text("Mélanger", align="center")
        self.printer.feed(3)
        payload = self.read_output()
        self.assertIn(b"Melanger", payload)
        self.assertIn(b"\x1ba\x01", payload)
        self.assertTrue(payload.endswith(b"\x1bd\x03"))

    def test_bitmap_uses_48_bytes_for_384_dots(self):
        self.printer.print_image(Image.new("1", (384, 8), 1))
        payload = self.read_output()
        self.assertIn(b"\x1d\x76\x30\x00\x30\x00\x08\x00", payload)

    def test_rejects_images_wider_than_print_head(self):
        with self.assertRaises(ValueError):
            self.printer.print_image(Image.new("1", (385, 1), 1))


if __name__ == "__main__":
    unittest.main()
