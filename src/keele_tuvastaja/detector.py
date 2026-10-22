"""Kiire ja väike eesti keele tuvastaja lühitekstidele."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from enum import Enum
from functools import lru_cache
from importlib.resources import as_file, files


class Verdict(str, Enum):
    ESTONIAN = "jah"
    NOT_ESTONIAN = "ei"
    UNCERTAIN = "ebakindel"


@dataclass(frozen=True)
class Detection:
    """Keeletuvastuse tulemus.

    ``confidence`` on mudeli normaliseeritud tõenäosus. Sõnastikureegli puhul
    on see 1.0, sest reegel on deterministlik, mitte statistiline hinnang.
    """

    verdict: Verdict
    language: str | None
    confidence: float
    method: str

    @property
    def is_estonian(self) -> bool:
        """True ainult kindla eestikeelse tulemuse korral."""

        return self.verdict is Verdict.ESTONIAN


# Need vormid aitavad just 1–3-sõnalisi tekste, mil statistilisel mudelil on
# liiga vähe n-gramme. Loend on meelega lühike ja konservatiivne.
_STRONG_ESTONIAN_WORDS = frozenset(
    {
        "aitäh",
        "armastan",
        "eestikeelne",
        "eestikeelse",
        "eestikeelset",
        "hüvasti",
        "kuidas",
        "küsimus",
        "läheb",
        "palun",
        "sõna",
        "sõnad",
        "sõnu",
        "tere",
        "vabandust",
        "vastus",
        "õhtu",
    }
)
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def _normalise(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


@lru_cache(maxsize=1)
def _identifier():
    """Laadi py3langid mudel esimesel kasutusel ja hoia mälus."""

    import py3langid
    from py3langid.langid import LanguageIdentifier

    resource = files(py3langid).joinpath("data/model.npz.xz")
    with as_file(resource) as model_path:
        return LanguageIdentifier.from_modelpath(
            model_path,
            norm_probs=True,
            min_confidence=0.20,
        )


def detect(text: str) -> Detection:
    """Otsusta, kas ``text`` on eesti keeles.

    Tühi, numbriline või liiga ebaselge sisend annab ``ebakindel`` tulemuse.
    See on ausam kui juhuslikult mõne keele kasuks otsustamine.
    """

    if not isinstance(text, str):
        raise TypeError("text peab olema str")

    normalised = _normalise(text)
    words = _WORD_RE.findall(normalised.casefold())
    if not words:
        return Detection(Verdict.UNCERTAIN, None, 0.0, "sisend")

    if any(word in _STRONG_ESTONIAN_WORDS for word in words):
        return Detection(Verdict.ESTONIAN, "et", 1.0, "sonastik")

    language, confidence = _identifier().classify(normalised)
    confidence = float(confidence)
    if language == "und":
        return Detection(Verdict.UNCERTAIN, None, confidence, "py3langid")
    if language == "et":
        return Detection(Verdict.ESTONIAN, language, confidence, "py3langid")
    return Detection(Verdict.NOT_ESTONIAN, language, confidence, "py3langid")


def is_estonian(text: str) -> bool:
    """Lihtne jah/ei API; ebakindel tulemus loetakse ``False``-iks."""

    return detect(text).is_estonian


def warm_up() -> None:
    """Laadi statistiline mudel enne esimese päringu vastuvõtmist mällu."""

    _identifier()


def main() -> None:
    parser = argparse.ArgumentParser(description="Kontrolli, kas tekst on eesti keeles.")
    parser.add_argument("text", nargs="+", help="kontrollitav tekst")
    parser.add_argument("--json", action="store_true", help="väljasta JSON")
    args = parser.parse_args()

    result = detect(" ".join(args.text))
    if args.json:
        payload = asdict(result)
        payload["verdict"] = result.verdict.value
        print(json.dumps(payload, ensure_ascii=False))
    else:
        language = result.language or "määramata"
        print(
            f"{result.verdict.value} "
            f"(keel={language}, kindlus={result.confidence:.3f}, meetod={result.method})"
        )


if __name__ == "__main__":
    main()
