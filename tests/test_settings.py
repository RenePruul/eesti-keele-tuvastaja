import os
import unittest
from unittest.mock import patch

from keele_tuvastaja.settings import Settings


class SettingsTests(unittest.TestCase):
    def test_reads_limits_from_environment(self):
        values = {
            "KEELETUVASTAJA_MAX_TEXT_LENGTH": "123",
            "KEELETUVASTAJA_MAX_REQUEST_BYTES": "456",
            "KEELETUVASTAJA_REQUEST_TIMEOUT_SECONDS": "1.5",
        }
        with patch.dict(os.environ, values, clear=False):
            settings = Settings.from_env()

        self.assertEqual(settings.max_text_length, 123)
        self.assertEqual(settings.max_request_bytes, 456)
        self.assertEqual(settings.request_timeout_seconds, 1.5)

    def test_rejects_non_positive_integer(self):
        with patch.dict(
            os.environ, {"KEELETUVASTAJA_MAX_TEXT_LENGTH": "0"}, clear=False
        ):
            with self.assertRaises(RuntimeError):
                Settings.from_env()

    def test_rejects_invalid_timeout(self):
        with patch.dict(
            os.environ,
            {"KEELETUVASTAJA_REQUEST_TIMEOUT_SECONDS": "vale"},
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                Settings.from_env()


if __name__ == "__main__":
    unittest.main()
