#!/usr/bin/env bash
# Skrypt budowania dla Render (ustaw jako Build Command: ./build.sh)
set -o errexit

pip install -r requirements.txt

# Zbiera WSZYSTKIE pliki statyczne (z /static/ i z aplikacji) do
# STATIC_ROOT (/staticfiles/) - WhiteNoise serwuje je odtad.
# --upload-unhashed-files jest WYMAGANE gdy USE_CLOUDINARY=True:
# django-cloudinary-storage nadpisuje komende 'collectstatic' i domyslnie
# NIE kopiuje nieshashowanych plikow na dysk (zaklada, ze CSS/JS tez
# idzie do Cloudinary). My uzywamy Cloudinary TYLKO dla zdjec (media),
# a CSS/JS ma iść przez WhiteNoise - ta flaga wymusza normalne
# dzialanie. Flaga jest bezpieczna/no-op gdy USE_CLOUDINARY=False.
python manage.py collectstatic --noinput --upload-unhashed-files

# Uruchamia migracje bazy danych PRZED wystartowaniem serwera - bez tego
# pierwsze wdrozenie (albo kazda zmiana modeli) nie zadziala.
python manage.py migrate
