#----------------------------------------------------------------------
# Initialize the Genshi templating system. 'g' is the 'templating
# system object' used to render Genshi templates. 'genshi_namespace'
# is a module which acts as a global namespace when expanding a Genshi
# template.

from conifer.here                    import HERE
from conifer.plumbing.genshi_support import TemplateSet
from .                               import genshi_namespace

g = TemplateSet(HERE('templates'), genshi_namespace)

#----------------------------------------------------------------------
# Common imports shared by all view functions.

import django.conf
import django.forms
import re
import sys
import warnings
import pdb

from conifer.plumbing.hooksystem    import gethook, callhook, callhook_required
from conifer.syrup                  import models
from datetime                       import datetime
from django.contrib.auth            import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models     import User, SiteProfileNotAvailable
from django.core.paginator          import Paginator
from django.core.urlresolvers       import reverse
from django.db.models               import Q
from django.forms.models            import modelformset_factory
from django.http                    import (HttpResponse, HttpResponseRedirect,
                                            HttpResponseNotFound,
                                            HttpResponseForbidden)
from django.shortcuts               import get_object_or_404
from django.utils                   import simplejson
from django.utils.translation       import ugettext as _
from _generics                      import * # TODO: should not import-star

from conifer.libsystems.marcxml     import (marcxml_to_dictionary,
                                            marcxml_dictionary_to_dc)

from django.utils.translation       import ugettext as _

#-----------------------------------------------------------------------------
# Authorization

def _access_denied(request, message):
    if request.user.is_anonymous():
        # then take them to login screen....
        dest = (request.META['SCRIPT_NAME'] + \
                    '/accounts/login/?next=%s%s' % (
                request.META['SCRIPT_NAME'],
                request.META['PATH_INFO']))
        return HttpResponseRedirect(dest)
    else:
        return simple_message(_('Access denied.'), message,
                              _django_type=HttpResponseForbidden)

# todo, these decorators could be refactored.

# decorator
def instructors_only(handler):
    def hdlr(request, site_id, *args, **kwargs):
        site = get_object_or_404(models.Site, pk=site_id)
        allowed = site.can_edit(request.user)
        if allowed:
            return handler(request, site_id, *args, **kwargs)
        else:
            return _access_denied(request,
                                  _('Only instructors are allowed here.'))
    return hdlr

# decorator
def members_only(handler):
    def hdlr(request, site_id, *args, **kwargs):
        user = request.user
        site = get_object_or_404(models.Site, pk=site_id)
        allowed = site.is_open_to(request.user)
        if allowed:
            return handler(request, site_id, *args, **kwargs)
        else:
            if site.access=='LOGIN':
                msg = _('Please log in, so that you can enter this site.')
            else:
                msg = _('Only site members are allowed here.')
            return _access_denied(request, msg)
    return hdlr

# decorator
def admin_only(handler):
    # fixme, 'admin' is vaguely defined for now as anyone who is
    # 'staff', i.e. who has access to the Django admin interface.
    def hdlr(request, *args, **kwargs):
        allowed = request.user.is_staff
        if allowed:
            return handler(request, *args, **kwargs)
        else:
            return _access_denied(request, 
                                  _('Only administrators are allowed here.'))
    return hdlr

#decorator
def public(handler):
    # A no-op! Just here to be used to explicitly decorate methods
    # that are supposed to be public.
    return handler


#-----------------------------------------------------------------------------
# Simple Message: just a quick title-and-message web page.

def simple_message(title, content, go_back=True, **kwargs):
    kwargs.update(**locals())
    return g.render('simplemessage.xhtml', **kwargs)


#------------------------------------------------------------

def custom_500_handler(request):
    cls, inst, tb = sys.exc_info()
    msg = simple_message(_('Error: %s') % repr(inst),
                         repr((request.__dict__, inst)))
    return HttpResponse(msg._container, status=501)

def custom_400_handler(request):
    msg = simple_message(_('Not found'),
                          _('The page you requested could not be found'))
    return HttpResponse(msg._container, status=404)


#------------------------------------------------------------

# decorator
def postmortem(func):
    """Drop into a debugger if an error occurs in the decoratee."""
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception, e:
            print '!!!!!!', e
            pdb.post_mortem()
    if django.conf.settings.DEBUG:
        return inner
    else:
        return func
