Requirements:
Python 3.9
Poetry
Installation:
Install Python.
Install Poetry https://python-poetry.org/docs/
osx / linux / bashonwindows install instructions
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
windows powershell install instructions
(Invoke-WebRequest -Uri https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py -UseBasicParsing).Content | python -
Python dependency setup:
To install Python dependencies:
Run “poetry install” in both the “frontend” and “backend” directory.
VSCode workspace:
To get a preconfigured VSCode workspace with recommended settings:
Open “Honeypot.code-workspace” with VSCode.
Install the recommended extensions below.
If this shows up, press NO and restart the editor (else you will edit the shared workspace config).

Recommended extensions:
When the workspace has been opened in VSCode it will ask you to install recommended extensions. For easier coding we recommend you to add these.

How to run frontend or backend for development:
I frontendmappen(första): docker-compose build (Ifall Dockerfile eller docker-compose.yaml har ändrats, detta rebuildar)
docker-compose up
