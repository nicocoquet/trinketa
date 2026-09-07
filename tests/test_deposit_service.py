import time
import unittest
from io import BytesIO

from fastapi import HTTPException
from PIL import Image

from service.app import Settings, allowed_return_url, normalize_to_jpeg, safe_filename, sign_payload, verify_payload


class DepositServiceTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings("client", "secret", "session-secret")

    def test_signed_state_round_trip(self):
        payload = {"returnTo": self.settings.pages_url, "exp": int(time.time()) + 60}
        self.assertEqual(verify_payload(sign_payload(payload, self.settings.session_secret), self.settings.session_secret), payload)

    def test_external_return_url_is_rejected(self):
        self.assertEqual(allowed_return_url("https://example.org/", self.settings.pages_url), self.settings.pages_url)

    def test_filename_rejects_paths(self):
        with self.assertRaises(HTTPException):
            safe_filename("../image.jpg")

    def test_filename_accepts_supported_image(self):
        self.assertEqual(safe_filename("isbn-9782853137119.JPG"), "isbn-9782853137119.JPG")

    def test_image_is_normalized_without_metadata(self):
        source = BytesIO()
        image = Image.new("RGB", (40, 30), "white")
        image.save(source, format="PNG", pnginfo=None)
        name, content = normalize_to_jpeg("photo.png", source.getvalue())
        self.assertEqual(name, "photo.jpg")
        with Image.open(BytesIO(content)) as normalized:
            self.assertEqual(normalized.format, "JPEG")
            self.assertEqual(normalized.mode, "RGB")
            self.assertFalse(normalized.getexif())


if __name__ == "__main__":
    unittest.main()
