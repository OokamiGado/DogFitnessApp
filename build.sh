#!/usr/bin/env bash
# Skrypt budowania dla Render (ustaw jako Build Command: ./build.sh)
set -o errexit

# --no-cache-dir: wymusza SWIEZA instalacje pakietow, bez cache pip
# na serwerze budujacym - zapobiega mieszaniu plikow z roznych wersji
# pakietow miedzy deployami.
pip install --no-cache-dir -r requirements.txt

# Zbiera WSZYSTKIE pliki statyczne (z /static/ i z aplikacji) do
# STATIC_ROOT (/staticfiles/) - WhiteNoise serwuje je odtad.
# --clear usuwa WSZYSTKIE pliki z poprzedniego builda przed skopiowaniem
# nowych - zapobiega mieszaniu starego manifestu z nowymi plikami.
python manage.py collectstatic --noinput --clear

# Uruchamia migracje bazy danych PRZED wystartowaniem serwera - bez tego
# pierwsze wdrozenie (albo kazda zmiana modeli) nie zadziala.
python manage.py migrate
