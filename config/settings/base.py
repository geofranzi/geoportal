"""
Base settings to build other settings files upon.
"""
import os
from pathlib import Path

import environ

ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
# planthub/
APPS_DIR = ROOT_DIR / "framework"
env = environ.Env()

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=True)  # True -> read .env file
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(ROOT_DIR / ".env"))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "UTC"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"  # old de-De todo change back to de-De?
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [str(ROOT_DIR / "locale")]

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

# leave this line unchanged and add your local database credentials to the local.py
DATABASES = {"default": env.db("DATABASES", default="postgres://postgres:PASSWORD@:5432/climate_services_gateway")}
# DATABASES = {"default": env.db("DATABASES", default="postgres://postgres:admin@:5432/geoportal_inspire_test")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "webgis.urls"  # todo move to config?
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    'webgis.apps.SuitConfig',
    'webgis.apps.MyAdminConfig',
    # 'django.contrib.admin',
    'django_assets',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    # 'django_messages'
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.gis',
]
THIRD_PARTY_APPS = [
    'allauth',
    'allauth.account',
    'authapi',
    'cronjobs',
    'djgeojson',
    'dj_rest_auth',
    'dj_rest_auth.registration',
    'rest_framework',
    'rest_framework.authtoken',
    # "allauth.socialaccount",
    # "corsheaders",
    # "knox"
]

LOCAL_APPS = [
    'inspire',
    'mapviewer',
    'layers',
    'map',
    'geospatial',
    'content',
    'csw',
    'swos',
    'phaenopt',
    # Your stuff: custom apps go here
]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
# MIGRATION_MODULES = {"sites": "planthub.contrib.sites.migrations"}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
# AUTHENTICATION_BACKENDS = [
# "django.contrib.auth.backends.ModelBackend",
# "allauth.account.auth_backends.AuthenticationBackend",
# ]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
# AUTH_USER_MODEL = "users.User"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
# LOGIN_REDIRECT_URL = "users:redirect"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
# LOGIN_URL = "account_login"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
# PASSWORD_HASHERS = [
# https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
# "django.contrib.auth.hashers.Argon2PasswordHasher",
# "django.contrib.auth.hashers.PBKDF2PasswordHasher",
# "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
# "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
# ]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    # 'authapi.disable.disableCSRF',
]

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
# STATIC_ROOT = os.path.join(BASE_DIR, "static")
SUBDIR = ''

# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"
# STATIC_URL = SUBDIR+'/static/'
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = (
    os.path.join(ROOT_DIR, "static"),
    os.path.join(os.path.dirname(ROOT_DIR), 'node_modules'),
)
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "django_assets.finders.AssetsFinder"
]
# from old config
ASSETS_LOAD_PATH = [
    os.path.join(os.path.dirname(ROOT_DIR), 'node_modules'),
    STATICFILES_DIRS[0]
]
ASSETS_ROOT = STATICFILES_DIRS[0]

NPM_ROOT_PATH = os.path.join(os.path.dirname(ROOT_DIR))

UGLIFYJS_BIN = os.path.join(os.path.dirname(ROOT_DIR), 'node_modules/.bin/uglifyjs')
UGLIFYJS_EXTRA_ARGS = (
    '--mangle "reserved=[$,angular]"',
    '--compress',
)

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(APPS_DIR / "media")
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = SUBDIR + '/media/'

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates

TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        "DIRS": [str(APPS_DIR / "templates")],
        "APP_DIRS": True,  # from old config todo needed?
        "OPTIONS": {
            'debug': DEBUG,  # from old config todo needed?
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
            # https://docs.djangoproject.com/en/dev/ref/templates/api/#loader-types
            # "loaders": [
            # "django.template.loaders.filesystem.Loader",
            # "django.template.loaders.app_directories.Loader",
            # ],
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                # "planthub.utils.context_processors.settings_context",
            ],
        },
    }
]

# https://docs.djangoproject.com/en/dev/ref/settings/#form-renderer
# FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
# CRISPY_TEMPLATE_PACK = "bootstrap4"

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(APPS_DIR / "fixtures"),)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-browser-xss-filter
SECURE_BROWSER_XSS_FILTER = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "SAMEORIGIN"

# Old
# CSRF_COOKIE_DOMAIN='localhost'
# CSRF_COOKIE_DOMAIN='phaenopt.ssv-hosting.de'
# SESSION_COOKIE_DOMAIN=CSRF_COOKIE_DOMAIN
# USE_X_FORWARDED_HOST=True
# SESSION_COOKIE_SECURE=True
# CSRF_COOKIE_SECURE=True

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5

# old email and auth config
# django-allauth
# SITE_ID = 1
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = SUBDIR + '/'
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
LOGIN_ON_EMAIL_CONFIRMATION = False
CONFIRM_EMAIL_ON_GET = True
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"  # problems with "mandatory" when logging in...
LOGIN_REDIRECT_URL = '/'

# EMAIL_HOST = 'smtprelaypool.ispgateway.de'
# EMAIL_PORT = 465
# EMAIL_USE_TLS = True
# EMAIL_USE_SSL = False

EMAIL_HOST = 'smtp.essi-blog.org'
EMAIL_PORT = 25
EMAIL_HOST_USER = 'dev@essi-blog.org'
EMAIL_HOST_PASSWORD = 'ANPASSEN'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# for testing mails we can use the console where the testserver was started
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# for testing mails we can use the filebackend, emails are stored as files in the foleder specified
EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
if not os.path.exists(os.path.join(APPS_DIR, "media", "email")):
    os.mkdir(os.path.join(APPS_DIR, "media", "email"))
EMAIL_FILE_PATH = os.path.join(APPS_DIR, "media", "email")  #

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL.
ADMIN_URL = "admin/"
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [("""Franziska Zander""", "")]  # "" -> email address
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s "
                      "%(process)d %(thread)d %(message)s"
        }
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

# django-allauth
# ------------------------------------------------------------------------------
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_AUTHENTICATION_METHOD = "username"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_EMAIL_REQUIRED = True
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
# ACCOUNT_ADAPTER = "planthub.users.adapters.AccountAdapter"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
# SOCIALACCOUNT_ADAPTER = "planthub.users.adapters.SocialAccountAdapter"

# django-rest-framework
# -------------------------------------------------------------------------------
# django-rest-framework - https://www.django-rest-framework.org/api-guide/settings/
REST_FRAMEWORK = {
    # "DEFAULT_AUTHENTICATION_CLASSES": ('knox.auth.TokenAuthentication',),
    # "DEFAULT_AUTHENTICATION_CLASSES": (
    # "rest_framework.authentication.SessionAuthentication",
    # "rest_framework.authentication.TokenAuthentication",
    # ),
    #  "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    )
}

# django-cors-headers - https://github.com/adamchainz/django-cors-headers#setup
CORS_URLS_REGEX = r"^/(api|users|datasets|viz|search|projects|iknow|viz_smon|planthub.kg_visualization)/.*$"

# Your stuff...
# ------------------------------------------------------------------------------
# Allow all or only a certain address
# CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = [
    'http://127.0.0.1:5173',
]
CORS_ALLOW_HEADERS = ('Authorization', 'Content-Type', 'Cache-Control', 'X-Requested-With')

# BLAZEGRAPH Settings
BLAZEGRAPH_URL = 'http://localhost:9999/'

# Static path on Server. Django settings parameter did not show the expected result.
STATIC_URL_PREFIX = ""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

##################################################
# satellite data discovery

EARTH_EXPLORER_USER = 'USERNAME'
EARTH_EXPLORER_PASSWORD = 'PASSWORD'

ESA_DATAHUB_USER = 'USERNAME'
ESA_DATAHUB_PASSWORD = 'PASSWORD'

ESA_SSO_USER = 'USERNAME'
ESA_SSO_PASSWORD = 'PASSWORD'

##################################################
# Publish (Insert/Delete) metadata with CSW-Transactional

CSW_T = False  # true: active , empty/false: deactivated
CSW_T_PATH = 'ANPASSEN'  # path to pycsw/csw.py; pycsw.cfg: transactions=true, allowed_ips=xxx

##################################################
# Elasticsearch

ELASTICSEARCH = False  # true: active , empty/false: deactivated
ELASTICSEARCH_HOSTS = ['https://localhost:9200']  # Anpassen (needs to be a list)

##################################################
# Data download

DATA_ROOT = 'ANPASSEN'

##################################################
# Base URL
BASE_URL = "https://inspire.hameln.de/"
DEFAULT_EXTENT_WEST = "9.25"
DEFAULT_EXTENT_EAST = "9.47"
DEFAULT_EXTENT_NORTH = "52.16"
DEFAULT_EXTENT_SOUTH = "52.05"
GML_PATH = "C:/Users/c1zafr/OneDrive/INSPIRE_HM/03_Umsetzung/Hale_Export"

if os.name == 'nt':
    VENV_BASE = os.environ['VIRTUAL_ENV']
    os.environ['PATH'] = os.path.join(VENV_BASE, 'Lib\\site-packages\\osgeo') + ';' + os.environ['PATH']
    os.environ['PROJ_LIB'] = os.path.join(VENV_BASE, 'Lib\\site-packages\\osgeo\\data\\proj') + ';' + os.environ['PATH']

# ???
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
# WARNING: disable ASSETS_DEBUG in production!
# True: deliver JavaScript and CSS files as usual (e.g. for development)
# False: deliver bundled/minified files (e.g. for live system)
ASSETS_DEBUG = True
# WARNING: disable ASSETS_AUTO_BUILD in production!
# True: automatically rebuild bundles if source files have changed
ASSETS_AUTO_BUILD = True
