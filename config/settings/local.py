# flake8: noqapytest
from .base import *  # noqa
from .base import env

env = environ.Env()
# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="hi9QXEFQEh0dzRTv7igcf63fBfmk0t97bB5NJcNWSxw1KCo0QLiNqpI6d979ZypS",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1", "10.149.0.38", "iknow.inf-bb.uni-jena.de", "leutra.geogr.uni-jena.de", "tippecc.github.io"]
X_FRAME_OPTIONS = 'allow-from http://127.0.0.1:5173/'

# Using postgresSQL change local db settings here (postgres://USERNAME:PASSWORD@HOST:PORT/DATABASENAME
DATABASES["default"] = env.db("DATABASES", default="postgis://postgres:PASSWORD@127.0.0.1:5432/climate_services_gateway")

# Using SQlite
# DATABASES["default"] = env.db("DATABASE_URL2", default="sqlite:////test_db.sqlite3")


# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    }
}

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = env("EMAIL_HOST", default="mailhog")
# https://docs.djangoproject.com/en/dev/ref/settings/#email-port
EMAIL_PORT = 1025

# WhiteNoise
# ------------------------------------------------------------------------------
# http://whitenoise.evans.io/en/latest/django.html#using-whitenoise-in-development
# INSTALLED_APPS = ["whitenoise.runserver_nostatic"] + INSTALLED_APPS  # noqa F405


# django-debug-toolbar
# ------------------------------------------------------------------------------
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#prerequisites
INSTALLED_APPS += ["debug_toolbar"]  # noqa F405
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#middleware
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa F405
# https://django-debug-toolbar.readthedocs.io/en/latest/configuration.html#debug-toolbar-config
DEBUG_TOOLBAR_CONFIG = {
    "DISABLE_PANELS": ["debug_toolbar.panels.redirects.RedirectsPanel"],
    "SHOW_TEMPLATE_CONTEXT": True,
}
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#internal-ips
INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]


# if env("USE_DOCKER") == "yes":
#    import socket
#
#    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
#    INTERNAL_IPS += [".".join(ip.split(".")[:-1] + ["1"]) for ip in ips]


# django-extensions
# ------------------------------------------------------------------------------
# https://django-extensions.readthedocs.io/en/latest/installation_instructions.html#configuration
INSTALLED_APPS += ["django_extensions"]  # noqa F405

# Your stuff...


# Windows fix for GDAL
if os.name == 'nt':
    GDAL_LIBRARY_PATH = "C:/Users/c1zafr/PycharmProjects/GEOPORTAL_INSPIRE/venv_3_10/Lib/site-packages/osgeo/gdal304.dll"
