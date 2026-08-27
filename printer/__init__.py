"""API d'impression indépendante du reste de Protein Resequencer."""

from .thermal import ThermalPrinter


_default_printer = ThermalPrinter()


def is_available():
    return _default_printer.is_available()


def print_text(text, align="left", initialize=True):
    return _default_printer.print_text(text, align=align, initialize=initialize)


def print_image(image):
    return _default_printer.print_image(image)


def feed(lines=3):
    return _default_printer.feed(lines)


__all__ = ["ThermalPrinter", "is_available", "print_text", "print_image", "feed"]
