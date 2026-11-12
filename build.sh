#!/usr/bin/env bash
# Skrypt budowania dla Render (ustaw jako Build Command: ./build.sh)
set -o errexit

pip install -r requirements.txt

# Zbiera WSZYSTKIE pliki statyczne (z /static/ i z aplikacji) do
# STATIC_ROOT (/staticfiles/) - WhiteNoise serwuje je odtad.
python manage.py collectstatic --noinput --clear

# Uruchamia migracje bazy danych PRZED wystartowaniem serwera - bez tego
# pierwsze wdrozenie (albo kazda zmiana modeli) nie zadziala.
python manage.py migrate
