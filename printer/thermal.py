"""Couche ESC/POS minimale pour l'imprimante thermique USB EM5820."""

import os
import threading
import time
import unicodedata


DEFAULT_DEVICE = "/dev/usb/lp0"
PRINT_WIDTH = 384


class ThermalPrinter:
    def __init__(self, device=None, width=PRINT_WIDTH, stripe_height=128):
        self.device = device or os.environ.get("THERMAL_PRINTER_DEVICE", DEFAULT_DEVICE)
        self.width = width
        self.stripe_height = stripe_height
        self._lock = threading.Lock()

    def is_available(self):
        return os.path.exists(self.device) and os.access(self.device, os.W_OK)

    def _write(self, payload):
        if not os.path.exists(self.device):
            raise FileNotFoundError(f"Imprimante absente : {self.device}")
        with self._lock:
            with open(self.device, "ab", buffering=0) as output:
                output.write(payload)

    @staticmethod
    def _ascii(text):
        normalized = unicodedata.normalize("NFKD", str(text))
        return normalized.encode("ascii", "ignore")

    def print_text(self, text, align="left", initialize=True):
        alignments = {"left": 0, "center": 1, "right": 2}
        if align not in alignments:
            raise ValueError("align doit être 'left', 'center' ou 'right'")
        payload = b"\x1b@" if initialize else b""
        payload += b"\x1ba" + bytes((alignments[align],))
        payload += self._ascii(text)
        self._write(payload)

    def feed(self, lines=3):
        if not 0 <= lines <= 255:
            raise ValueError("lines doit être compris entre 0 et 255")
        self._write(b"\x1bd" + bytes((lines,)))

    @staticmethod
    def _raster_command(image):
        image = image.convert("1")
        width_bytes = (image.width + 7) // 8
        data = bytearray()
        pixels = image.load()
        for y in range(image.height):
            for byte_x in range(width_bytes):
                value = 0
                for bit in range(8):
                    x = byte_x * 8 + bit
                    if x < image.width and pixels[x, y] == 0:
                        value |= 0x80 >> bit
                data.append(value)
        return (
            b"\x1d\x76\x30\x00"
            + bytes((width_bytes & 0xFF, width_bytes >> 8,
                     image.height & 0xFF, image.height >> 8))
            + data
        )

    def print_image(self, image):
        """Imprime une image Pillow, limitée à la largeur validée de 384 dots."""
        if image.width > self.width:
            raise ValueError(f"Image trop large : {image.width} > {self.width} dots")
        if image.width < self.width:
            from PIL import Image
            canvas = Image.new("1", (self.width, image.height), 1)
            canvas.paste(image.convert("1"), (0, 0))
            image = canvas
        payloads = [b"\x1b@\x1ba\x00"]
        for top in range(0, image.height, self.stripe_height):
            bottom = min(top + self.stripe_height, image.height)
            payloads.append(self._raster_command(image.crop((0, top, self.width, bottom))))
        with self._lock:
            if not os.path.exists(self.device):
                raise FileNotFoundError(f"Imprimante absente : {self.device}")
            with open(self.device, "ab", buffering=0) as output:
                for payload in payloads:
                    output.write(payload)
                    time.sleep(0.08)
