# Eesti keele tuvastaja

Väike Pythoni teek ja HTTP API, mis otsustab, kas sisestatud tekst on eesti
keeles. Lahendus kasutab `py3langid` mudelit ning konservatiivseid reegleid
kõige lühemate eestikeelsete väljendite jaoks.

Võimalikud vastused on:

- `jah` – tekst on eesti keeles;
- `ei` – tuvastati muu keel;
- `ebakindel` – usaldusväärseks otsuseks pole piisavalt infot.

## Paigaldamine

Vajalik on Python 3.10 või uuem.

```bash
git clone https://github.com/RenePruul/eesti-keele-tuvastaja.git
cd eesti-keele-tuvastaja
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

HTTP API ja testide sõltuvustega paigaldamiseks:

```bash
python -m pip install -e ".[api,test]"
```

## Kasutamine Pythonist

```python
from keele_tuvastaja import detect, is_estonian

result = detect("Tere maailm")

print(result.verdict.value)  # jah
print(result.language)       # et
print(result.confidence)     # 0.0–1.0
print(result.method)         # sonastik või py3langid

print(is_estonian("Tere maailm"))  # True
```

`detect()` tagastab detailse tulemuse. `is_estonian()` tagastab `True` ainult
kindla eestikeelse tulemuse korral; nii `ei` kui ka `ebakindel` annavad
`False`.

Käsurealt:

```bash
eesti-keel "Kuidas läheb?"
eesti-keel --json "How are you?"
```

## HTTP API

Käivita API:

```bash
keele-api
```

Kontrolli teksti:

```bash
curl -X POST http://127.0.0.1:8000/detect \
  -H 'Content-Type: application/json' \
  -d '{"text":"Tere, kuidas sul läheb?"}'
```

Näidisvastus:

```json
{
  "verdict": "jah"
}
```

HTTP API otsus tuleb väljast `verdict`: `jah`, `ei` või `ebakindel`.
Detailne `language`, `confidence` ja `method` jäävad Pythoni `detect()`
tulemusse ega kuulu HTTP vastusesse. Pythoni `is_estonian()` mugavusfunktsioon
ei kuulu samuti HTTP vastusesse.

Teenuse tervist saab kontrollida otspunktist `GET /health`. Interaktiivne
OpenAPI dokumentatsioon asub töötava serveri aadressil `/docs`.

`POST /detect` vastustele lisatakse `Cache-Control: no-store` ja
`Pragma: no-cache`. API ei logi päringu sisu. Uvicorni tavapärane ligipääsulogi
võib sisaldada kliendi IP-aadressi, meetodit, teed ja vastuse olekukoodi.

Seadistamiseks saab kasutada keskkonnamuutujaid:

- `KEELETUVASTAJA_HOST` – võrguliides, vaikimisi `127.0.0.1`;
- `KEELETUVASTAJA_PORT` – port, vaikimisi `8000`;
- `KEELETUVASTAJA_MAX_TEXT_LENGTH` – teksti suurim pikkus märkides;
- `KEELETUVASTAJA_MAX_REQUEST_BYTES` – HTTP päringu suurim maht baitides;
- `KEELETUVASTAJA_REQUEST_TIMEOUT_SECONDS` – tuvastuse ajalimiit sekundites.

## Kasutamine Automaatkorrektoriga

Kohalikuks kasutamiseks käivita API vaikimisi aadressil ja jäta
Automaatkorrektori keeleteenuse aadressiks `http://127.0.0.1:8000`:

```bash
keele-api
curl http://127.0.0.1:8000/health
```

Automaatkorrektor saadab kasutaja selgelt valitud teksti väljale `text` ja
kasutab vastusest ainult välja `verdict`. Keeleteenus ei paranda ega salvesta
teksti.

Kaugserveri korral pane API TLS-i lõpetava pöördproksi taha ning sisesta
Automaatkorrektorisse ainult origin, näiteks `https://keel.example.ee` ilma
`/detect` teeta. Klient lisab tee ise ja küsib enne teksti saatmist kasutaja
nõusolekut. Ära avalda Uvicorni HTTP-porti otse internetti. API-l pole
sisseehitatud autentimist ega kiirusepiirangut; seadista need vajaduse korral
pöördproksis ning väldi päringukehade logimist.

## Docker

```bash
docker compose up --build --wait -d
curl http://127.0.0.1:8000/health
docker compose down
```

Tõmmise nimi on `eesti-keele-api:latest`. Arenduskeskkonnas seotakse port
ainult aadressiga `127.0.0.1`, seega pole API vaikimisi kohtvõrgus avalik.

## Testid

```bash
python -m unittest discover -s tests -v
```

## Piirangud

- Ühe või kahe sõna keelt ei saa alati usaldusväärselt määrata.
- Segakeelne tekst saab ühe otsuse kogu sisendi kohta.
- `ebakindel` ei tähenda, et tekst on kindlasti muus keeles.
- Rakenduse pärisandmetel tuleb kvaliteeti eraldi valideerida.

## Litsents

[MIT](LICENSE)
