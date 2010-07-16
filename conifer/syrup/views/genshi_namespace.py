# genshi_namespace: toplevel definitions in this module will be
# available when rendering a Genshi template. In addition, the Genshi
# template will have access to:

# request: the current request object
# user:    the current user
# ROOT:    the SCRIPT_NAME of the root directory of this application.
# errors:  either None, or a list of errors related to the current page.

import django.forms
import itertools
import urllib

from conifer.plumbing.hooksystem import gethook, callhook
from conifer.syrup               import models
from django.utils                import translation

_ = translation.ugettext
