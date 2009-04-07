# Django settings for conifer project.

# make sure you have a local_settings.py file! Copy from
# local_settings.py.in and customize that file.

import os

BASE_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
HERE = lambda s: os.path.join(BASE_DIRECTORY, s)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3' # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = HERE('syrup.sqlite') # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Detroit'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en_US'

# Please only include languages here for which we have a locale in our
# locale/ directory.
LANGUAGES = [("en-us", "English"),
             ("fr-ca", "Canadian French"),
             ]

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = HERE('static')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/syrup/djmedia/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'j$dnxqbi3iih+(@il3m@vv(tuvt2+yu2r-$dxs$s7=iqjz_s!&'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'conifer.middleware.genshi_locals.ThreadLocals',
    'django.middleware.locale.LocaleMiddleware',
    'babeldjango.middleware.LocaleMiddleware',
    # TransactionMiddleware should be last...
    'django.middleware.transaction.TransactionMiddleware',
)

ROOT_URLCONF = 'conifer.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'conifer.syrup',
)

AUTH_PROFILE_MODULE = 'syrup.UserProfile'


AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)


# more on this later.
LIBRARY_INTEGRATION = {
    'patron_info': 'SIP',
    'item_status': 'SIP',
    'item_info'  : 'OpenSRF',
    'catalogue'  : 'Z39.50',
}

EVERGREEN_XMLRPC_SERVER = None # evergreen host, for auth, e.g. '192.168.1.10'

if EVERGREEN_XMLRPC_SERVER:
    AUTHENTICATION_BACKENDS.append(
        'conifer.custom.auth_evergreen.EvergreenAuthBackend')

# stuff that I really ought not check into svn...
#SIP_HOST = ('hostname', 9999)
#SIP_CREDENTIALS = ('userid', 'password', 'location')

try:
    # Graham has this right now; it's not official Syrup. Nothing to see here.
    from private_local_settings import SIP_HOST, SIP_CREDENTIALS
except:
    pass

#CACHE_BACKEND = 'memcached://127.0.0.1:11211/'
#CACHE_BACKEND = 'db://test_cache_table'
#CACHE_BACKEND = 'locmem:///'
