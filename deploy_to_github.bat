@echo off
chcp 65001 > nul

echo Tworzenie pliku .gitignore...
(
    echo # Pliki skompilowane / zoptymalizowane / DLL
    echo __pycache__/
    echo *.py[cod]
    echo *$py.class
    echo.
    echo # Rozszerzenia C
    echo *.so
    echo.
    echo # Dystrybucja / pakowanie
    echo .Python
    echo build/
    echo develop-eggs/
    echo dist/
    echo downloads/
    echo eggs/
    echo .eggs/
    echo lib/
    echo lib64/
    echo parts/
    echo sdist/
    echo var/
    echo wheels/
    echo pip-wheel-metadata/
    echo share/python-wheels/
    echo *.egg-info/
    echo .installed.cfg
    echo *.egg
    echo MANIFEST
    echo.
    echo # PyInstaller
    echo *.manifest
    echo *.spec
    echo.
    echo # Logi instalatora
    echo pip-log.txt
    echo pip-delete-this-directory.txt
    echo.
    echo # Raporty z testow jednostkowych / pokrycia kodu
    echo htmlcov/
    echo .tox/
    echo .nox/
    echo .coverage
    echo .coverage.*
    echo .cache
    echo nosetests.xml
    echo coverage.xml
    echo *.cover
    echo .hypothesis/
    echo .pytest_cache/
    echo.
    echo # Tlumaczenia
    echo *.mo
    echo *.pot
    echo.
    echo # Rzeczy zwiazane z Django:
    echo *.log
    echo local_settings.py
    echo db.sqlite3
    echo db.sqlite3-journal
    echo.
    echo # Rzeczy zwiazane z Flaskiem:
    echo instance/
    echo .webassets-cache
    echo.
    echo # Rzeczy zwiazane ze Scrapy:
    echo .scrapy
    echo.
    echo # Dokumentacja Sphinx
    echo docs/_build/
    echo.
    echo # PyBuilder
    echo target/
    echo.
    echo # Jupyter Notebook
    echo .ipynb_checkpoints
    echo.
    echo # IPython
    echo profile_default/
    echo ipython_config.py
    echo.
    echo # pyenv
    echo .python-version
    echo.
    echo # PEP 582; __pypackages__
    echo __pypackages__/
    echo.
    echo # Rzeczy zwiazane z Celery
    echo celerybeat-schedule
    echo celerybeat.pid
    echo.
    echo # Pliki sparsowane przez SageMath
    echo *.sage.py
    echo.
    echo # Srodowiska
    echo .env
    echo .venv
    echo env/
    echo venv/
    echo ENV/
    echo env.bak
    echo venv.bak
    echo.
    echo # Ustawienia projektu Spyder
    echo .spyderproject
    echo .spyproject
    echo.
    echo # Ustawienia projektu Rope
    echo .ropeproject
    echo.
    echo # Dokumentacja mkdocs
    echo /site
    echo.
    echo # mypy
    echo .mypy_cache/
    echo .dmypy.json
    echo dmypy.json
    echo.
    echo # Analizator statyczny Pyre
    echo .pyre/
    echo.
    echo # Analizator statyczny pytype
    echo .pytype/
    echo.
    echo # Symbole debugowania Cython
    echo cython_debug/
    echo.
    echo # Baza danych
    echo ksiegarnia.db
) > .gitignore
echo Plik .gitignore zostal stworzony.

echo Inicjalizacja repozytorium Git...
git init
git add .gitignore
git commit -m "Initial commit: Add .gitignore"

echo.
echo --- Commit Kacpra (Backend/Baza Danych) ---
git config user.name "Kacper"
git config user.email "kac.gla12@gmail.com"

git add config.py main_asgi.py run.py seed_data.py stworz-db.py requirements.txt .env.example
git add api/
git add aplikacja/models.py aplikacja/app.py aplikacja/__init__.py aplikacja/routes.py
git add aplikacja/admin/
git add aplikacja/auth/
git add aplikacja/services/
git add migrations/
git commit -m "feat(backend): Konfiguracja backendu, bazy danych i logiki aplikacji" --author="Kacper <kac.gla12@gmail.com>"
echo Commit Kacpra zostal stworzony.

echo.
echo --- Commit Arka (Frontend/UI) ---
git config user.name "Arek"
git config user.email "aron0120@wp.pl"

git add aplikacja/static/
git add aplikacja/templates/
git commit -m "feat(frontend): Implementacja interfejsu uzytkownika i stylow" --author="Arek <aron0120@wp.pl>"
echo Commit Arka zostal stworzony.

echo.
echo --- Commit Kamila (Full-stack/Testy) ---
git config user.name "Kamil"
git config user.email "kamil.ilczuk@yahoo.com"

git add .
git commit -m "feat(fullstack): Integracja calosci, dodanie pozostalych modulow i plikow" --author="Kamil <kamil.ilczuk@yahoo.com>"
echo Commit Kamila zostal stworzony.

echo.
echo Wszystkie commity zostaly utworzone.
echo.

set /p repo_url="Wprowadz adres URL zdalnego repozytorium GitHub (np. https://github.com/uzytkownik/repozytorium.git): "
git remote add origin "%repo_url%"
git branch -M main
git push -u origin main

echo.
echo Kod zostal wyslany do zdalnego repozytorium!

pause