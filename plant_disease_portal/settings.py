import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'development-only-change-me-plant-disease-portal')
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() in {'1', 'true', 'yes', 'on'}
ALLOWED_HOSTS = [
    host.strip() for host in os.getenv(
        'DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost'
    ).split(',') if host.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'diagnosis.apps.DiagnosisConfig',
]

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

ROOT_URLCONF = 'plant_disease_portal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'plant_disease_portal.wsgi.application'

try:
    import dj_database_url
except ImportError:
    dj_database_url = None

if os.getenv('DATABASE_URL') and dj_database_url:
    DATABASES = {
        'default': dj_database_url.config(
            default=os.getenv('DATABASE_URL'), conn_max_age=600, ssl_require=False
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage'
            if DEBUG else
            'whitenoise.storage.CompressedManifestStaticFilesStorage'
        )
    },
}
WHITENOISE_AUTOREFRESH = DEBUG

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'home'

MODEL_PATH = Path(os.getenv('PLANT_MODEL_PATH', BASE_DIR / 'ml_models' / 'plant_disease_model.keras'))
CLASS_NAMES_PATH = Path(os.getenv('PLANT_CLASS_NAMES_PATH', BASE_DIR / 'ml_models' / 'class_names.json'))
LOW_CONFIDENCE_THRESHOLD = float(os.getenv('LOW_CONFIDENCE_THRESHOLD', '60'))

# Upload limits are environment-configurable. Folder upload sends every file as
# an individual multipart upload, so DATA_UPLOAD_MAX_NUMBER_FILES must be above
# MAX_UPLOAD_FILES.
MAX_UPLOAD_FILES = int(os.getenv('MAX_UPLOAD_FILES', '500'))
MAX_UPLOAD_SIZE_MB = int(os.getenv('MAX_UPLOAD_SIZE_MB', '100'))
MAX_EXTRACTED_IMAGES_PER_FILE = int(os.getenv('MAX_EXTRACTED_IMAGES_PER_FILE', '200'))
MAX_TOTAL_EXTRACTED_IMAGES = int(os.getenv('MAX_TOTAL_EXTRACTED_IMAGES', '500'))
MAX_ZIP_MEMBERS = int(os.getenv('MAX_ZIP_MEMBERS', '500'))
MAX_ZIP_UNCOMPRESSED_MB = int(os.getenv('MAX_ZIP_UNCOMPRESSED_MB', '500'))
DATA_UPLOAD_MAX_NUMBER_FILES = int(os.getenv('DATA_UPLOAD_MAX_NUMBER_FILES', '1000'))
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('DATA_UPLOAD_MAX_MEMORY_SIZE_MB', '120')) * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('FILE_UPLOAD_MAX_MEMORY_SIZE_MB', '10')) * 1024 * 1024

csrf_origins = [
    origin.strip() for origin in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]
if csrf_origins:
    CSRF_TRUSTED_ORIGINS = csrf_origins

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
