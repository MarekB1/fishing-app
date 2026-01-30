```md
## Env
Create `.env` in project root (see example in chat).

## Setup (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

Make sure PostgreSQL has database `fishing_app` created and credentials match `.env`.
