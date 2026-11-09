import asyncio
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
            Detection(Verdict.ESTONIAN, "et", 0.99, "test"),
            Detection(Verdict.NOT_ESTONIAN, "en", 0.98, "test"),
            Detection(Verdict.UNCERTAIN, None, 0.20, "test"),
        )
        app = create_app(_settings(), load_model=False)
        with TestClient(app) as client:
            for detection in cases:
                with self.subTest(verdict=detection.verdict):
                    with patch("keele_tuvastaja.api.detect", return_value=detection):
                        response = client.post("/detect", json={"text": "näide"})

                    self.assertEqual(response.status_code, 200)
                    payload = response.json()
                    self.assertEqual(set(payload), {"verdict"})
                    self.assertEqual(payload["verdict"], detection.verdict.value)
                    self.assertEqual(response.headers["cache-control"], "no-store")
                    self.assertEqual(response.headers["pragma"], "no-cache")

    def test_automaatkorrektor_contract_with_real_detector(self):
        with TestClient(create_app(_settings(), load_model=False)) as client:
            estonian = client.post(
                "/detect",
                headers={"Accept": "application/json"},
                json={"text": "Tere, kuidas sul läheb?"},
            )
            english = client.post(
                "/detect",
                headers={"Accept": "application/json"},
                json={"text": "my name is jeff"},
            )

        self.assertEqual(estonian.status_code, 200)
        self.assertEqual(estonian.json(), {"verdict": "jah"})
        self.assertEqual(english.status_code, 200)
        self.assertEqual(english.json(), {"verdict": "ei"})
        self.assertTrue(estonian.headers["content-type"].startswith("application/json"))

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
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_rejects_too_large_chunked_request(self):
        def chunks():
            yield b'{"text": "'
            yield b"a" * 50
            yield b'"}'

        settings = _settings(max_request_bytes=20)
        with TestClient(create_app(settings, load_model=False)) as client:
            response = client.post(
                "/detect",
                content=chunks(),
                headers={"Content-Type": "application/json"},
            )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json(), {"detail": "Päring on liiga suur"})
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_accepts_chunked_request_within_limit(self):
        def chunks():
            yield b'{"text": '
            yield b'"tere"}'

        detection = Detection(Verdict.ESTONIAN, "et", 1.0, "test")
        with TestClient(create_app(_settings(), load_model=False)) as client:
            with patch("keele_tuvastaja.api.detect", return_value=detection):
                response = client.post(
                    "/detect",
                    content=chunks(),
                    headers={"Content-Type": "application/json"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"verdict": "jah"})

    def test_stops_reading_body_at_limit(self):
        app = create_app(_settings(max_request_bytes=10), load_model=False)
        received = 0
        sent = []

        async def receive():
            nonlocal received
            received += 1
            return {"type": "http.request", "body": b"x" * 4, "more_body": True}

        async def send(message):
            sent.append(message)

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/detect",
            "raw_path": b"/detect",
            "root_path": "",
            "query_string": b"",
            "headers": [(b"content-type", b"application/json")],
            "client": ("testclient", 1),
            "server": ("testserver", 80),
        }
        asyncio.run(app(scope, receive, send))

        self.assertEqual(sent[0]["status"], 413)
        self.assertEqual(received, 3)

    def test_rejects_invalid_content_length(self):
        with TestClient(create_app(_settings(), load_model=False)) as client:
            response = client.post(
                "/detect",
                content=b'{"text": "tere"}',
                headers={"Content-Type": "application/json", "Content-Length": "abc"},
            )

        self.assertEqual(response.status_code, 400)

    def test_rejects_invalid_json_shape(self):
        with TestClient(create_app(_settings(), load_model=False)) as client:
            response = client.post("/detect", json={"wrong": "tere"})

        self.assertEqual(response.status_code, 422)

    def test_rejects_extra_json_fields(self):
        with TestClient(create_app(_settings(), load_model=False)) as client:
            response = client.post(
                "/detect",
                json={"text": "tere", "unused": "value"},
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.headers["cache-control"], "no-store")

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
