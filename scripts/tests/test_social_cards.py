"""Cartes sociales : Instagram (via Make) n'accepte que le JPEG — les cartes
doivent être générées nativement en JPEG (avant : PNG + proxy wsrv.nl).

Lancer :  cd scripts && python -m unittest tests.test_social_cards
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from social_card import make_card


class TestMakeCardJpeg(unittest.TestCase):
    def test_extension_jpg_produit_un_vrai_jpeg_1200x630(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "carte.jpg"
            make_card("Un titre de test pour la carte", "FOOTBALL", "975/1000", out)
            with Image.open(out) as im:
                self.assertEqual(im.format, "JPEG")
                self.assertEqual(im.size, (1200, 630))

    def test_extension_png_reste_un_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "carte.png"
            make_card("Un titre de test pour la carte", "FOOTBALL", "975/1000", out)
            with Image.open(out) as im:
                self.assertEqual(im.format, "PNG")


if __name__ == "__main__":
    unittest.main()
