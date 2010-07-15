# Django settings for conifer project.

# Don't edit this file; edit local_settings.py instead.

import sys
from here import HERE
sys.path.append(HERE('..'))

DEBUG = False

ADMINS = []

DATABASE_ENGINE = '' # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = ''   # Or path to database file if using sqlite3.
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
SECRET_KEY = 'replace this yourself --- j$dnxqbi3iih+(@il3m@vv(tuvt2+yu2r-$dxs$s7=iqjz_s!&'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'conifer.plumbing.genshi_support.GenshiMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'babeldjango.middleware.LocaleMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
)

ROOT_URLCONF = 'conifer.urls'

TEMPLATE_DIRS = []

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'south',
    'conifer.syrup',
)

AUTH_PROFILE_MODULE = 'syrup.UserProfile'


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend'
]

#---------------------------------------------------------------------------
# local_settings.py

try:
    from local_settings import *
except ImportError:
    raise Exception('You must create a local_settings.py file, and use it! '
                    'As a starting point, see local_settings.py.example.')
except:
    import sys
    raise Exception('There is an error in your local_settings.py! '
                    'Please investigate and repair.', sys.exc_value)


#---------------------------------------------------------------------------
# Further settings that depend upon local_settings.

TEMPLATE_DEBUG = DEBUG
MANAGERS       = ADMINS

#----------

if EVERGREEN_AUTHENTICATION:
    AUTHENTICATION_BACKENDS.append(
        'conifer.integration.auth_evergreen.django.EvergreenAuthBackend')

#----------

