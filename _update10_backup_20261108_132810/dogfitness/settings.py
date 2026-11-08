from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

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

INSTALLED_APPS += ['exercises', 'clients']

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

if USE_CLOUDINARY:
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
        'API_KEY': config('CLOUDINARY_API_KEY', default=''),
        'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
    }
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============ LOGOWANIE ============
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'exercise_list'
LOGOUT_REDIRECT_URL = 'login'

# ============ MONITOROWANIE MIEJSCA (Neon / storage dashboard) ============
# Limit darmowego planu Neon dla calej bazy Postgres (w MB). Zmien jesli
# masz inny plan / inny limit. UWAGA: ten limit dotyczy TYLKO bazy danych,
# NIE dotyczy zdjec (pliki media sa na dysku serwera, np. Render, albo
# w Cloudinary jesli USE_CLOUDINARY=True - to OSOBNE limity).
NEON_DB_LIMIT_MB = 1024
