# Eesti keele tuvastaja

Pythoni teek ja HTTP API, mis otsustab, kas tekst on eesti keeles.

Vastus on `jah`, `ei` või `ebakindel`.

## Paigaldamine

Vajalik on Python 3.10 või uuem.

```bash
git clone https://github.com/RenePruul/eesti-keele-tuvastaja.git
cd eesti-keele-tuvastaja
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[api,test]"
```

## Kasutamine

Pythonist:

```python
from keele_tuvastaja import detect, is_estonian

print(detect("Tere maailm").verdict.value)  # jah
print(is_estonian("Tere maailm"))           # True
```

Käsurealt:

```bash
eesti-keel "Kuidas läheb?"
eesti-keel --json "How are you?"
```

`--json` väljastab

```bash
{
"verdict": "ei",
"language": "en",
"confidence": 0.99,
"method": "py3langid"
}
```

## HTTP API

Käivita API:

```bash
keele-api
```

Saada tekst kontrollimiseks:

```bash
curl -X POST http://127.0.0.1:8000/detect \
  -H 'Content-Type: application/json' \
  -d '{"text":"Tere, kuidas sul läheb?"}'
```

Vastus:

```json
{ "verdict": "jah" }
```

Lisaks:

- `GET /health` – teenuse tervisekontroll;

## Docker

```bash
docker compose up --build --wait -d
curl http://127.0.0.1:8000/health
docker compose down
```

## Testid

```bash
python -m unittest discover -s tests -v
```

## Litsents

[MIT](LICENSE)
