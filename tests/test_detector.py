import unittest

from keele_tuvastaja import Verdict, detect, is_estonian


class DetectorTests(unittest.TestCase):
    def test_estonian_sentences(self):
        samples = (
            "Tere maailm",
            "Kuidas läheb?",
            "See on väga hea",
            "paar sõna",
            "ma armastan sind",
            "See on üks pikem eestikeelne lause.",
        )
        for text in samples:
            with self.subTest(text=text):
                self.assertEqual(detect(text).verdict, Verdict.ESTONIAN)

    def test_non_estonian_sentences(self):
        samples = (
            "How are you?",
            "This is very good",
            "Mitä kuuluu?",
            "Det här är svenska",
            "Das ist gut",
            "Bonjour le monde",
        )
        for text in samples:
            with self.subTest(text=text):
                self.assertEqual(detect(text).verdict, Verdict.NOT_ESTONIAN)

    def test_ambiguous_input_is_uncertain(self):
        for text in ("", "12345", "OK", "menu", "internet"):
            with self.subTest(text=text):
                self.assertEqual(detect(text).verdict, Verdict.UNCERTAIN)

    def test_boolean_api(self):
        self.assertTrue(is_estonian("aitäh"))
        self.assertFalse(is_estonian("hello"))
        self.assertFalse(is_estonian("123"))

    def test_rejects_non_string(self):
        with self.assertRaises(TypeError):
            detect(None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
