# genshi_namespace

# Toplevel definitions in this module will be available in when
# rendering a Genshi template.

from conifer.integration._hooksystem import gethook, callhook
import itertools
from itertools import cycle
from conifer.syrup import models
import django.forms
from django.utils import translation

_ = translation.ugettext

# this probably ought to be a method on User, or another model class.
def instructor_url(instructor, suffix=''):
    return '/instructor/%d/%s' % (instructor.id, suffix)

# added to make department browse
def department_url(department, suffix=''):
    return '/department/%d/%s' % (department.id, suffix)


def call_or_value(obj, dflt=None):
    # This is used by the generics templates.
    if callable(obj):
        return obj() or dflt
    else:
        return obj or dflt


def instructs(user, site):
    try:
        mbr = models.Member.objects.get(user=user, site=site)
        return mbr.role in ('INSTR', 'PROXY')
    except:
        return False
    
