import unittest
from pathlib import Path

from scripts.analyze_isbn_queue import isbn10_from_13, isbn_from_filename, valid_isbn13


class IsbnValidationTests(unittest.TestCase):
    def test_valid_isbn13(self):
        self.assertTrue(valid_isbn13("978-2-85313-711-9"))
        self.assertFalse(valid_isbn13("978-2-85313-711-8"))

    def test_isbn10_conversion(self):
        self.assertEqual(isbn10_from_13("9782853137119"), "2853137112")

    def test_filename_fallback(self):
        self.assertEqual(isbn_from_filename(Path("dos_978-2-85313-711-9.jpg")), "9782853137119")


if __name__ == "__main__":
    unittest.main()
