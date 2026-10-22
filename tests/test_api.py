import time
import unittest
from unittest.mock import patch

from starlette.testclient import TestClient

from keele_tuvastaja import Detection, Verdict
from keele_tuvastaja.api import create_app
from keele_tuvastaja.settings import Settings


def _settings(**overrides):
    values = {
        "max_text_length": 100,
        "max_request_bytes": 1_000,
        "request_timeout_seconds": 1.0,
    }
    values.update(overrides)
    return Settings(**values)


class ApiTests(unittest.TestCase):
    def test_health(self):
        with TestClient(create_app(_settings(), load_model=False)) as client:
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_all_detection_results(self):
        cases = (
            (Detection(Verdict.ESTONIAN, "et", 0.99, "test"), True),
            (Detection(Verdict.NOT_ESTONIAN, "en", 0.98, "test"), False),
            (Detection(Verdict.UNCERTAIN, None, 0.20, "test"), False),
        )
        app = create_app(_settings(), load_model=False)
        with TestClient(app) as client:
            for detection, expected_boolean in cases:
                with self.subTest(verdict=detection.verdict):
                    with patch("keele_tuvastaja.api.detect", return_value=detection):
                        response = client.post("/detect", json={"text": "näide"})

                    self.assertEqual(response.status_code, 200)
                    payload = response.json()
                    self.assertEqual(payload["verdict"], detection.verdict.value)
                    self.assertEqual(payload["is_estonian"], expected_boolean)

    def test_rejects_empty_text(self):
        with TestClient(create_app(_settings(), load_model=False)) as client:
            response = client.post("/detect", json={"text": "   "})

        self.assertEqual(response.status_code, 422)
        self.assertIn("ei tohi olla tühi", response.json()["detail"])

    def test_rejects_too_long_text(self):
        settings = _settings(max_text_length=5)
        with TestClient(create_app(settings, load_model=False)) as client:
            response = client.post("/detect", json={"text": "liiga pikk"})

        self.assertEqual(response.status_code, 413)

    def test_rejects_too_large_request(self):
        settings = _settings(max_request_bytes=10)
        with TestClient(create_app(settings, load_model=False)) as client:
            response = client.post("/detect", json={"text": "tere"})

        self.assertEqual(response.status_code, 413)

    def test_rejects_invalid_json_shape(self):
        with TestClient(create_app(_settings(), load_model=False)) as client:
            response = client.post("/detect", json={"wrong": "tere"})

        self.assertEqual(response.status_code, 422)

    def test_detection_timeout(self):
        settings = _settings(request_timeout_seconds=0.01)

        def slow_detection(_):
            time.sleep(0.05)
            return Detection(Verdict.ESTONIAN, "et", 1.0, "test")

        with TestClient(create_app(settings, load_model=False)) as client:
            with patch("keele_tuvastaja.api.detect", side_effect=slow_detection):
                response = client.post("/detect", json={"text": "tere"})

        self.assertEqual(response.status_code, 504)


if __name__ == "__main__":
    unittest.main()
