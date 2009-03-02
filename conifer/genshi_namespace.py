# genshi_namespace

# Toplevel definitions in this module will be available in when
# rendering a Genshi template.

from itertools import cycle
from conifer.syrup import models

# this probably ought to be a method on User, or another model class.
def instructor_url(instructor, suffix=''):
    return '/syrup/instructor/%d/%s' % (instructor.id, suffix)


def call_or_value(obj, dflt=None):
    # This is used by the generics templates.
    if callable(obj):
        return obj() or dflt
    else:
        return obj or dflt
