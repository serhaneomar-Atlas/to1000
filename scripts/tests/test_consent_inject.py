"""Injection du script de consentement avant le loader GA4 (Consent Mode v2).

Le script /consent.js doit être chargé de façon SYNCHRONE avant
googletagmanager.com/gtag pour poser les défauts de consentement (denied)
avant tout dépôt de cookie. L'injection en masse sur ~2400 pages doit être
idempotente et ne toucher que les pages qui embarquent gtag.

Lancer :  cd scripts && python -m unittest tests.test_consent_inject
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from add_consent_snippet import CONSENT_TAG, inject_consent

LOADER = '<script async src="https://www.googletagmanager.com/gtag/js?id=G-4V8Y6C38VN"></script>'
PAGE = f"<html><head>\n  {LOADER}\n  <script>gtag('js', new Date());</script>\n</head></html>"


class TestInjectConsent(unittest.TestCase):
    def test_insere_consent_js_avant_le_loader_gtag(self):
        out, changed = inject_consent(PAGE)
        self.assertTrue(changed)
        self.assertIn(CONSENT_TAG, out)
        self.assertLess(out.index(CONSENT_TAG), out.index("googletagmanager.com/gtag"))

    def test_idempotent(self):
        once, _ = inject_consent(PAGE)
        twice, changed = inject_consent(once)
        self.assertFalse(changed)
        self.assertEqual(once, twice)
        self.assertEqual(twice.count(CONSENT_TAG), 1)

    def test_page_sans_gtag_inchangee(self):
        html = "<html><head><title>x</title></head></html>"
        out, changed = inject_consent(html)
        self.assertFalse(changed)
        self.assertEqual(out, html)

    def test_preserve_le_reste_de_la_page(self):
        out, _ = inject_consent(PAGE)
        self.assertIn("gtag('js', new Date());", out)
        self.assertTrue(out.startswith("<html><head>"))


if __name__ == "__main__":
    unittest.main()
