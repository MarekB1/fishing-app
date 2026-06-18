# Fishing App (Django)

Webová aplikácia pre rybársku súťaž (Django monolit + PostgreSQL + HTMX + Channels/WebSockets).

## Požiadavky

- **Python 3.12 (odporúčané)**  
  > Na Windows sa pri novších verziách (napr. 3.14) môžu niektoré balíky (napr. `Pillow`) kompilovať zo source a padnúť.  
- **PostgreSQL** (lokálne) – DB `fishing_app` musí existovať a údaje sedia s `.env`
- **Redis server** (len pre realtime notifikácie cez Channels) – viď sekcia *Redis*

## .env

Vytvor súbor `.env` v root priečinku projektu (podľa príkladu, ktorý máte v chate/projekte).

## Setup (Windows PowerShell) — rýchly štart

```powershell
# v root priečinku projektu
py -0p                    # skontroluj dostupné Pythony
py -3.12 -m venv .venv    # vytvor venv (odporúčané)

.\.venv\Scripts\Activate.ps1
python -V

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python manage.py migrate
python manage.py runserver
```

---

# Nový PC / čistý setup krok po kroku (odporúčané)

## 1) Nainštaluj Python 3.12 (Windows)

### Cez príkazový riadok (`winget`)
```powershell
winget install -e --id Python.Python.3.12
```

Over:
```powershell
py -0p
```

## 2) Vytvor `.venv` (správnou verziou Pythonu)

```powershell
# v root priečinku projektu
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -V
python -c "import sys; print(sys.executable)"
```

> Tip: na inštaláciu balíkov používaj vždy `python -m pip ...`, aby si mal istotu, že inštaluješ do správneho venv.

## 3) Nainštaluj requirements

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 4) Spusti migrácie a server

```powershell
python manage.py migrate
python manage.py runserver
```

---

# Časté problémy a riešenia

## `ModuleNotFoundError: No module named 'django'`
- Nemáš aktívny venv, alebo si doň neinštaloval requirements.

Riešenie:
```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## `ModuleNotFoundError: No module named 'daphne'`
- Projekt používa ASGI server `daphne` (Channels/WebSockets), ale nie je nainštalovaný.

Riešenie:
```powershell
python -m pip install daphne
```

> Odporúčanie: maj `daphne` aj v `requirements.txt`, aby sa to na novom PC nestávalo.

## Problém s `Pillow` (build zo source, zlib missing)
- Typicky nastane na Windows, keď používaš Python verziu bez dostupných wheels pre `Pillow`.

Riešenie:
- používaj Python **3.12** (alebo 3.11) a vytvor nový `.venv`.

## Zmena Python verzie = treba vytvoriť nový `.venv`
Virtuálne prostredie je „pripútané“ k verzii Pythonu, ktorou bolo vytvorené.

Rýchly postup:
```powershell
deactivate 2>$null
taskkill /F /IM python.exe 2>$null
taskkill /F /IM pythonw.exe 2>$null

# PowerShell delete (môže zlyhať ak je .venv locknutý)
Remove-Item -Recurse -Force .venv

# alebo spoľahlivo cez CMD
cmd /c "rmdir /s /q .venv"

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Ak hlási „Access denied“ pri mazaní `.venv`:
- zavri VS Code (Python/Pylance často lockuje súbory)
- ukonči `python.exe` / `Code.exe`
- potom skús zmazať znova.

---

## Ako spustiť Redis lokálne (Windows)

### Docker
```powershell
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

Test:
```powershell
docker ps
```

> Bez bežiaceho Redis servera realtime notifikácie cez WebSockets nemusia fungovať (podľa nastavenia `CHANNEL_LAYERS`).

<!-- Pre tunel  -->
```Install
winget install --id Cloudflare.cloudflared
```

```Root priečinok (Docker beží)
python manage.py runserver 127.0.0.1:8000
```

``` Nový PowerShell - zobrazí URL 
cloudflared tunnel --url http://127.0.0.1:8000 --protocol http2
```

## projekt_kontext.txt súbor pre Gemini
Get-ChildItem -Recurse -Include "models.py","views.py","urls.py","consumers.py","routing.py","settings.py","base.html","nav.html" | 
Where-Object { $_.FullName -notmatch "node_modules|venv|\.git" } | 
ForEach-Object { 
    "--- FILE: $($_.FullName) ---`n" | Out-File -FilePath "projekt_kontext.txt" -Append -Encoding utf8
    Get-Content $_.FullName | Out-File -FilePath "projekt_kontext.txt" -Append -Encoding utf8
    "`n`n" | Out-File -FilePath "projekt_kontext.txt" -Append -Encoding utf8
}


## Push a pull dát z databázy 
<!--- Export dát s TODO --->
python manage.py dumpdata core.todotask --indent 4 -o todos.json

<!--- Export dát s TODO --->
klasický commit a push

<!--- Export dát s TODO --->
<!-- Teorecitky to viem spraviť aj cez klasický push a potom do terminálu import databázy -->
git pull
python manage.py loaddata todos.json

