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
# WhiteNoise - serwuje pliki statyczne (CSS, fonty) bezposrednio z Django,
# bez potrzeby osobnego serwera (nginx) - wystarczajace dla skali tej
# aplikacji. CompressedManifestStaticFilesStorage dodaje hash do nazwy
# pliku (cache busting) i kompresuje gzip/brotli przy 'collectstatic'.
#
# WAZNE: Django 5.1+ USUNAL wsparcie dla starego ustawienia
# 'STATICFILES_STORAGE' (string) - jest teraz CICHO ignorowane, bez
# bledu/ostrzezenia! Trzeba uzyc nowego formatu 'STORAGES' (dict).
# Bez tego CSS/fonty sa serwowane bez hasha w nazwie pliku - przegladarka
#/CDN moze cache'owac stara wersje pod tym samym URL-em, co przy kazdym
# redeployu grozi bledem typu "corrupted content" (niezgodna zawartosc
# pod tym samym adresem miedzy wersjami).
# WAZNE (kompatybilnosc z django-cloudinary-storage 0.3.0):
# Ta biblioteka ma WLASNY kod obslugi 'collectstatic', ktory wewnetrznie
# odwoluje sie do STAREGO ustawienia 'STATICFILES_STORAGE' (string) -
# nie zostala zaktualizowana pod Django 5.1+, ktory usunal to ustawienie
# na rzecz 'STORAGES' (dict). Trzymamy WIEC OBIE nazwy - w 100% bezpieczne.
# WAZNE - DEFINITYWNE ROZWIAZANIE problemu "plik X nie zostal znaleziony"
# (sorting-icons.svg, icon-yes.svg, itd.) ktory wielokrotnie psul build
# na Render:
#
# 'CompressedManifestStaticFilesStorage' (poprzedni backend) oprocz
# kompresji dodaje HASH do nazwy KAZDEGO pliku statycznego (cache-
# busting), a do tego PRZY TEJ OKAZJI probuje otworzyc/zweryfikowac
# KAZDY plik, do ktorego odwoluje sie jakikolwiek CSS/JS (np.
# url(../img/cos.svg) w plikach panelu Django /admin/, ktorych NIE
# kontrolujemy). Jesli JAKIKOLWIEK z tych plikow nie jest widoczny w
# danym momencie na serwerze budujacym (z przyczyn poza nasza kontrola,
# specyficznych dla Render) - CALY build pada z bledem.
#
# 'CompressedStaticFilesStorage' robi TYLKO kompresje (gzip/brotli) -
# BEZ hashowania nazw i BEZ weryfikowania zadnych referencji w CSS/JS.
# To CALKOWICIE i NA ZAWSZE eliminuje te klase bledow, bo mechanizm
# ktory je powodowal juz nie jest uzywany.
#
# Jedyny "koszt": pliki CSS/JS nie majа hasha w nazwie - po zmianie CSS
# czasem warto zrobic hard-refresh (Ctrl+Shift+R) w przegladarce. To
# drobiazg kosmetyczny, nieporownywalny z bledem wywalajacym cala
# produkcje.
_STATICFILES_BACKEND = (
    'whitenoise.storage.CompressedStaticFilesStorage' if not DEBUG
    else 'django.contrib.staticfiles.storage.StaticFilesStorage'
)
STATICFILES_STORAGE = _STATICFILES_BACKEND

# WHITENOISE_MANIFEST_STRICT = False: siatka bezpieczenstwa. Domyslnie
# (True) WhiteNoise PRZERYWA caly 'collectstatic' (a wiec caly build na
# Render) jesli JAKIKOLWIEK plik CSS/JS odwoluje sie do pliku, ktory nie
# istnieje (np. plik admina Django w niezgodnej/uszkodzonej wersji
# pakietu w cache serwera budujacego - co bylo przyczyna bledu
# 'sorting-icons.svg could not be found'). Ustawiajac False, taki JEDEN
# brakujacy plik jest cicho pomijany, a reszta plikow nadal dostaje
# poprawny hash - build NIE PADA z tego powodu.
WHITENOISE_MANIFEST_STRICT = False

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
