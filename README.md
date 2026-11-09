# Eesti keele tuvastaja

Pythoni teek ja HTTP API, mis otsustab, kas tekst on eesti keeles.

Vastus on `jah`, `ei` või `ebakindel`. `ebakindel` tähendab sisuliselt `ei`:
tekst pole kindlalt eestikeelne ja `is_estonian()` tagastab `False`.

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

## Uurimuse tulemused

Võrdlesime kahte varianti:

- **py3langid** – praegu kasutusel. Väike (~4,4 MB + NumPy ~34 MB) ja väga
  kiire.
- **Lingua** – täpsem lühikestel tekstidel, kuid paigaldus võtab ~293 MB.

### Testandmed ja allikad

Testis oli 4000 päris teksti avalikest
[Universal Dependencies](https://universaldependencies.org/)'i korpustest.
2000 teksti olid eestikeelsed. Ülejäänud 2000 olid muukeelsed ja jagunesid
seitsme keele vahel peaaegu võrdselt (284–288 teksti keele kohta).

| Keel    | Tekste | Korpus                                                                               |
| ------- | -----: | ------------------------------------------------------------------------------------ |
| eesti   |   2000 | [Estonian EWT](https://github.com/UniversalDependencies/UD_Estonian-EWT)             |
| soome   |    288 | [Finnish TDT](https://github.com/UniversalDependencies/UD_Finnish-TDT)               |
| inglise |    288 | [English EWT](https://github.com/UniversalDependencies/UD_English-EWT)               |
| vene    |    288 | [Russian SynTagRus](https://github.com/UniversalDependencies/UD_Russian-SynTagRus)   |
| läti    |    284 | [Latvian LVTB](https://github.com/UniversalDependencies/UD_Latvian-LVTB)             |
| leedu   |    284 | [Lithuanian ALKSNIS](https://github.com/UniversalDependencies/UD_Lithuanian-ALKSNIS) |
| saksa   |    284 | [German GSD](https://github.com/UniversalDependencies/UD_German-GSD)                 |
| rootsi  |    284 | [Swedish Talbanken](https://github.com/UniversalDependencies/UD_Swedish-Talbanken)   |

Tekstid jagati nelja pikkusrühma. Igas rühmas on 1000 teksti: 500 eesti ja
500 muukeelset (71–72 igast muust keelest). Näited on päris testandmetest:

| Rühm       | Mis see on                                             |
| ---------- | ------------------------------------------------------ |
| Üks sõna   | üksik sõna, nt `investeering`                          |
| Kaks sõna  | kaks järjestikust sõna lausest, nt `Unustasid mainida` |
| Kolm sõna  | kolm järjestikust sõna lausest, nt `autod olen müünud` |
| Pikk tekst | terve lause, vähemalt 5 sõna (vt allpool)              |

#### Mis on „pikk tekst”?

Pikk tekst on **üks terve lause**, mitte lõik ega pikem tekst. Lauses on
vähemalt 5 sõna:

- keskmiselt 12 sõna (umbes 85 tähemärki);
- 90% lausetest on lühemad kui 25 sõna;
- pikimas lauses on 63 sõna.

Näited testist:

| Sõnu | Lause                                                                                                                                                       |
| ---: | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
|    5 | Aianduskauplused müüvad küll metsmaasika seemneid.                                                                                                          |
|   12 | Aga see on oskus mille õppimiseks on vaja proovida ära ka kannatamine                                                                                       |
|   25 | Head autot ei ole nagunii raske müüa ja halva puhul ei oma nimi samuti tähtsust, sest olenemata kuulutamise viisist tuleb enne tehingut siiski kokku saada. |

Mitmest lausest koosnevat teksti ei testitud.

### Täpsus

Mõõdikud:

- **Õigeid vastuseid** – mitu protsenti kõigist vastustest olid õiged.
  `ebakindel` loetakse vastuseks `ei`: eestikeelse teksti puhul on see vale,
  muukeelse puhul õige.
- **Eesti tekste ära tuntud** – mitu protsenti eestikeelsetest tekstidest sai
  vastuse `jah`.
- **Vale `jah`** – mitu muukeelset teksti 500-st peeti ekslikult eestikeelseks.
- **Ebakindel** – mitu protsenti vastustest olid `ebakindel` (ehk `ei`).

**py3langid** (praegune lahendus):

| Rühm       | Õigeid vastuseid | Eesti tekste ära tuntud |   Vale `jah` | Ebakindel |
| ---------- | ---------------: | ----------------------: | -----------: | --------: |
| Üks sõna   |            69,3% |                   39,0% |      2 / 500 |     46,4% |
| Kaks sõna  |            86,1% |                   72,4% |      1 / 500 |     18,5% |
| Kolm sõna  |            97,3% |                   94,8% |      1 / 500 |      3,5% |
| Pikk tekst |            99,9% |                   99,8% |      0 / 500 |      0,1% |
| **Kokku**  |        **88,2%** |               **76,5%** | **4 / 2000** | **17,1%** |

**Lingua** (ei andnud testis kordagi vastust `ebakindel`):

| Rühm       | Õigeid vastuseid | Eesti tekste ära tuntud |   Vale `jah` |
| ---------- | ---------------: | ----------------------: | -----------: |
| Üks sõna   |            86,9% |                   74,4% |      3 / 500 |
| Kaks sõna  |            93,1% |                   86,8% |      3 / 500 |
| Kolm sõna  |            96,8% |                   93,8% |      1 / 500 |
| Pikk tekst |            99,9% |                   99,8% |      0 / 500 |
| **Kokku**  |        **94,2%** |               **88,7%** | **7 / 2000** |

Kokkuvõte: alates kolmest sõnast on mõlemad väga täpsed. Ühe-kahe sõna puhul
on Lingua selgelt parem. py3langid vastab siis sageli `ebakindel` ehk `ei`,
sest lühikesest sõnast jääb mudelile liiga vähe tähejadasid ja kindlus jääb
alla 0,20 läve. Seetõttu tunneb see ära vaid 39% eestikeelsetest üksikutest
sõnadest, aga peab muukeelset sõna eestikeelseks harva.

### Kiirus

Mõõdetud samadel 4000 tekstil, MacBook (Apple M3), üks lõim, pärast mudeli
laadimist. Aeg on ühe teksti kohta.

| Rühm       | py3langid |  Lingua |
| ---------- | --------: | ------: |
| Üks sõna   |  0,008 ms | 0,37 ms |
| Kaks sõna  |  0,010 ms | 0,42 ms |
| Kolm sõna  |  0,011 ms | 0,69 ms |
| Pikk tekst |  0,031 ms |  2,2 ms |

Eraldi mõõdeti ka palju pikemaid, umbes 350-sõnalisi tekste. Iga tekst on
liidetud samast korpusest järjestikustest päris lausetest. Tekste oli 160
(20 igas 8 keeles), pikkus 350–482 sõna, tavaliselt 357 sõna (~2600
tähemärki). Iga teksti mõõdeti 5 korda.

| ~350 sõna            | py3langid |  Lingua |
| -------------------- | --------: | ------: |
| Keskmine aeg         |   0,49 ms | 12,5 ms |
| Aeglaseimad 5% (P95) |   0,67 ms | 19,5 ms |
| Tekste sekundis      |     ~2000 |     ~80 |
| Õigeid vastuseid     |      100% |    100% |

py3langid on umbes 25–70 korda kiirem. Mõlemad on tavakasutuseks piisavalt
kiired. HTTP API koos võrguga vastas Dockeris keskmiselt 11,7 ms-ga
(10 samaaegset klienti, ~830 päringut sekundis).

### Eesti keele õppijate tekst

Õppija võib eesti lauses kasutada mõnda oma emakeele sõna. Testis võeti päris
eestikeelne lõik ja asendati selles üks sõna juhusliku soome, inglise, vene,
läti, leedu, saksa või rootsi sõnaga. Tegu on kunstlikult tehtud testiga, mitte
päris õppijate tekstidega.

Õige vastus oli alati `jah`, sest ülejäänud tekst on eestikeelne. Tulemused
(700 näidet kummagi pikkuse kohta):

| Teksti pikkus         | py3langid tunneb eesti keele ära | Lingua tunneb eesti keele ära |
| --------------------- | -------------------------------: | ----------------------------: |
| 3 sõna (1 võõrkeelne) |                            48,7% |                         48,0% |
| 9 sõna (1 võõrkeelne) |                            99,4% |                         94,4% |

Seega tasub tuvastajale saata vähemalt viimased 9 sõna.

## Testid

```bash
python -m unittest discover -s tests -v
```

## Litsents

[MIT](LICENSE)
