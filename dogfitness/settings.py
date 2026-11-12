from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

# ALLOWED_HOSTS - domyslnie localhost (dev). Na produkcji dodaj domeny w
# .env jako ALLOWED_HOSTS=twoja-domena.onrender.com,inna-domena.pl
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Render automatycznie ustawia RENDER_EXTERNAL_HOSTNAME dla kazdego
# serwisu (np. 'dogfitness.onrender.com') - dodajemy ja automatycznie,
# zeby nie trzeba było jej recznie wpisywac w zmiennych srodowiskowych.
RENDER_EXTERNAL_HOSTNAME = config('RENDER_EXTERNAL_HOSTNAME', default='')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# ============ CLOUDINARY (opcjonalny storage zdjec w chmurze) ============
# Domyslnie WYLACZONE (USE_CLOUDINARY=False) - zdjecia trafiaja na dysk
# lokalny serwera (jak dotychczas), zero zmian w dzialaniu aplikacji.
#
# Aby WLACZYC Cloudinary (trwaly storage w chmurze, darmowy plan 25GB):
#   1. Zaloz darmowe konto na https://cloudinary.com
#   2. Zainstaluj wymagane pakiety:
#        pip install django-cloudinary-storage cloudinary
#   3. W pliku .env ustaw:
#        USE_CLOUDINARY=True
#        CLOUDINARY_CLOUD_NAME=twoj_cloud_name
#        CLOUDINARY_API_KEY=twoj_api_key
#        CLOUDINARY_API_SECRET=twoj_api_secret
#   4. Zrestartuj serwer (python manage.py runserver)
#
# Od tego momentu WSZYSTKIE nowo wgrywane zdjecia trafia do Cloudinary.
# Zdjecia wgrane WCZESNIEJ (lokalnie) NIE zostana automatycznie przeniesione.
USE_CLOUDINARY = config('USE_CLOUDINARY', default=False, cast=bool)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
]

if USE_CLOUDINARY:
    # 'cloudinary_storage' MUSI byc przed 'django.contrib.staticfiles'
    INSTALLED_APPS += ['cloudinary_storage']

INSTALLED_APPS += ['django.contrib.staticfiles']

if USE_CLOUDINARY:
    # 'cloudinary' MUSI byc po 'django.contrib.staticfiles'
    INSTALLED_APPS += ['cloudinary']

INSTALLED_APPS += ['exercises', 'clients', 'plans', 'scheduling', 'dashboard', 'finance']

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'dogfitness.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'scheduling.context_processors.pending_requests_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'dogfitness.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    }
}

LANGUAGE_CODE = 'pl'
TIME_ZONE = 'Europe/Warsaw'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
# STATIC_ROOT - katalog, do ktorego 'collectstatic' zbiera WSZYSTKIE pliki
# statyczne (wymagane przez Render - bez tego 'collectstatic' nie ma gdzie
# zapisac plikow, a WhiteNoise nie ma czego serwowac na produkcji).
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ============ DEFINITYWNE ROZWIAZANIE (po wielu nieudanych podejsciach) ============
# HISTORIA PROBLEMU: Django/WhiteNoise majа mechanizm "post-processing"
# plikow statycznych (hashowanie nazw dla cache-bustingu I/LUB kompresja
# gzip/brotli), ktory przy KAZDYM wdrozeniu na Render PRZERYWAL caly
# build z powodu:
#   1. Brakujacych plikow panelu Django /admin/ (sorting-icons.svg,
#      icon-yes.svg) - przyczyna poza nasza kontrola (specyfika
#      srodowiska budowania Render).
#   2. Wyscigu wielowatkowej kompresji (ThreadPoolExecutor), ktory
#      czasem odwolywal sie do plikow w trakcie ich usuwania/nadpisywania.
#
# KAZDA z tych usterek jest CZESCIA mechanizmu post-processingu - nie da
# sie ich "naprawic" pojedynczo, bo kolejna wyskakuje przy nastepnym
# wdrozeniu. JEDYNE DEFINITYWNE rozwiazanie: CALKOWICIE WYLACZYC
# post-processing. Uzywamy wiec zwyklego, "glupiego" kopiowania plikow
# (StaticFilesStorage) ZAWSZE - rowniez na produkcji - BEZ hashowania,
# BEZ kompresji, BEZ weryfikowania jakichkolwiek wewnetrznych odwolan w
# CSS/JS. 'collectstatic' teraz tylko KOPIUJE pliki 1:1 - nic wiecej nie
# moze sie w tym kroku zepsuc, bo nie ma nic do zepsucia.
#
# WhiteNoise middleware (w MIDDLEWARE powyzej) i tak poprawnie serwuje
# te pliki na produkcji - kompresja/hashowanie byly tylko optymalizacja
# wydajnosci, NIE wymogiem dzialania. Jedyny praktyczny "koszt": po
# zmianie CSS/JS czasem warto zrobic hard-refresh (Ctrl+Shift+R) w
# przegladarce, zamiast automatycznego cache-bustingu. To jest drobiazg
# kosmetyczny, nieporownywalny z bledem wywalajacym cala produkcje.
_STATICFILES_BACKEND = 'django.contrib.staticfiles.storage.StaticFilesStorage'
STATICFILES_STORAGE = _STATICFILES_BACKEND

# ============ WHITENOISE_USE_FINDERS = True (KLUCZOWA ZMIANA) ============
# PRZYCZYNA bledu "404 dla style.css mimo ze build przeszedl": mechanizm
# 'collectstatic -> STATIC_ROOT -> WhiteNoise' okazal sie niestabilny
# na tym konkretnym srodowisku Render (seria bledow post-processingu
# pokazala, ze proces budowania/kopiowania plikow do STATIC_ROOT nie
# jest w 100% przewidywalny).
#
# WHITENOISE_USE_FINDERS = True sprawia, ze WhiteNoise NIE zalezy
# WYLACZNIE od STATIC_ROOT - szuka plikow TAKZE wprost w
# STATICFILES_DIRS (czyli w commitowanym katalogu 'static/' naszego
# projektu), ktory ZAWSZE istnieje w repo, niezaleznie od tego co sie
# dzieje z collectstatic. To ELIMINUJE cala klase bledow "plik nie
# zostal znaleziony w runtime, mimo ze build przeszedl".
WHITENOISE_USE_FINDERS = True

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': _STATICFILES_BACKEND,
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

if USE_CLOUDINARY:
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
        'API_KEY': config('CLOUDINARY_API_KEY', default=''),
        'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
    }
    # WAZNE: Django 5.1+ wymaga, by storage dla plikow media byl
    # ustawiony przez STORAGES['default'] (nowy styl), NIE przez stary
    # 'DEFAULT_FILE_STORAGE' (string) - te dwa style sie WYKLUCZAJA.
    # Nadpisujemy wiec wczesniej zdefiniowany STORAGES['default']
    # (FileSystemStorage) na storage Cloudinary.
    STORAGES['default'] = {
        'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============ LOGOWANIE ============
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard_home'
LOGOUT_REDIRECT_URL = 'login'

# ============ MONITOROWANIE MIEJSCA (Neon / storage dashboard) ============
# Limit darmowego planu Neon dla calej bazy Postgres (w MB). Zmien jesli
# masz inny plan / inny limit. UWAGA: ten limit dotyczy TYLKO bazy danych,
# NIE dotyczy zdjec (pliki media sa na dysku serwera, np. Render, albo
# w Cloudinary jesli USE_CLOUDINARY=True - to OSOBNE limity).
NEON_DB_LIMIT_MB = 1024

# ============ BEZPIECZENSTWO PRODUKCYJNE (Render) ============

# CSRF_TRUSTED_ORIGINS - Django 4+ wymaga explicite podanych originow
# (z protokolem https://), z ktorych akceptuje POST z CSRF tokenem.
# Bez tego KAZDY formularz (logowanie, dodanie klienta, cokolwiek) zwroci
# blad 403 "CSRF verification failed" na domenie produkcyjnej.
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')

# Render (jak wiekszosc hostingow) terminuje HTTPS na reverse proxy i
# przekazuje do aplikacji juz zwykle polaczenie HTTP wewnatrz swojej
# sieci - ten naglowek mowi Django "ten request BYL po HTTPS, nie
# przekierowuj go w kolko" (bez tego SECURE_SSL_REDIRECT=True powoduje
# nieskonczona petle przekierowan). Bezpieczne w dev - naglowek po prostu
# nigdy tam nie wystepuje.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Ustawienia WYMUSZAJACE HTTPS i bezpieczne ciasteczka - wlaczone TYLKO
# gdy DEBUG=False (czyli na produkcji). Lokalnie (DEBUG=True, http://
# localhost) te ustawienia by tylko przeszkadzaly (np. wylogowywaly przy
# kazdym requescie, bo ciasteczko 'Secure' nie dziala bez HTTPS).
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # HSTS - mowi przegladarce "pamietaj uzywac HTTPS dla tej domeny
    # przez N sekund, nawet jesli ktos wpisze http://". Zaczynamy od
    # 7 dni (bezpieczny start) - mozna zwiekszyc do roku (31536000)
    # gdy jestes pewien ze HTTPS dziala stabilnie.
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
