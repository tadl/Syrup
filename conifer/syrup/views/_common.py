import warnings
from conifer.syrup import models
from datetime import datetime
import django.conf
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, SiteProfileNotAvailable
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils import simplejson
from generics import *
#from gettext import gettext as _ # fixme, is this the right function to import?
from django.utils.translation import ugettext as _
import conifer.genshi_support as g
import django.forms
import re
import sys
from django.forms.models import modelformset_factory
from conifer.custom import lib_integration
from conifer.libsystems.z3950.marcxml import (marcxml_to_dictionary,
                                              marcxml_dictionary_to_dc)
from conifer.syrup.fuzzy_match import rank_pending_items
from django.core.urlresolvers import reverse
from conifer.here import HERE
import pdb

#-----------------------------------------------------------------------------
# Z39.50 Support
#
# This is experimental at this time, and requires some tricky Python
# imports as far as I can tell. For that reason, let's keep the Z39.50
# support optional for now. If you have Ply and PyZ3950, we'll load
# and use it; if not, no worries, everything else will workk.

try:
    # Graham needs this import hackery to get PyZ3950 working. Presumably
    # Art can 'import profile; import lex', so this hack won't run for
    # him.
    try:
        import profile
        import lex
        import yacc
    except ImportError:
        sys.modules['profile'] = sys # just get something called 'profile';
                                     # it's not actually used.
        import ply.lex
        import ply.yacc             # pyz3950 thinks these are toplevel modules.
        sys.modules['lex'] = ply.lex
        sys.modules['yacc'] = ply.yacc

    # for Z39.50 support, not sure whether this is the way to go yet but
    # as generic as it gets
    from PyZ3950 import zoom, zmarc
except:
    warnings.warn('Could not load Z39.50 support.')

#-----------------------------------------------------------------------------
# poor-man's logging. Not sure we need more yet.

def log(level, msg):
    print >> sys.stderr, '[%s] %s: %s' % (datetime.now(), level.upper(), msg)

#-----------------------------------------------------------------------------
# Authentication

def auth_handler(request, path):
    default_url = request.META['SCRIPT_NAME'] + '/'
    if path == 'login/':
        if request.method == 'GET':
            next=request.GET.get('next', default_url)
            if request.user.is_authenticated():
                return HttpResponseRedirect(next)
            else:
                return g.render('auth/login.xhtml',
                                next=request.GET.get('next'))
        else:
            userid, password = request.POST['userid'], request.POST['password']
            next = request.POST['next']
            user = authenticate(username=userid, password=password)
            def _error_page(msg):
                return g.render('auth/login.xhtml', err=msg, next=next)
            if user is None:
                return _error_page(
                    _('Invalid username or password. Please try again.'))
            elif not user.is_active:
                return _error_age(
                    _('Sorry, this account has been disabled.'))
            else:
                login(request, user)
                # initialize the profile if it doesn't exist.
                try:
                    user.get_profile()
                except models.UserProfile.DoesNotExist:
                    profile = models.UserProfile.objects.create(user=user)
                    profile.save()
                return HttpResponseRedirect(
                    request.POST.get('next', default_url))
    elif path == 'logout':
        logout(request)
        return HttpResponseRedirect(default_url)
    else:
        return HttpResponse('auth_handler: ' + path)

#-----------------------------------------------------------------------------
# Authorization

# TODO: this _fast_user_membership_query is broken.

def _fast_user_membership_query(user_id, site_id, where=None):
    # I use a raw SQL query here because I want the lookup to be as
    # fast as possible. Caching would help too, but let's try this
    # first. (todo, review later.)
    query = ('select count(*) from syrup_member '
             'where user_id=%s and site_id=%s ')
    if where:
        query += (' and ' + where)
    cursor = django.db.connection.cursor()
    cursor.execute(query, [user_id, int(site_id)])
    res = cursor.fetchall()
    cursor.close()
    allowed = bool(res[0][0])
    return allowed

def _access_denied(request, message):
    if request.user.is_anonymous():
        # then take them to login screen....
        dest = (request.META['SCRIPT_NAME'] + \
                    '/accounts/login/?next=' + request.META['PATH_INFO'])
        return HttpResponseRedirect(dest)
    else:
        return simple_message(_('Access denied.'), message,
                              _django_type=HttpResponseForbidden)

# todo, these decorators could be refactored.

# decorator
def instructors_only(handler):
    def hdlr(request, site_id, *args, **kwargs):
        allowed = request.user.is_superuser
        if not allowed:
            allowed = _fast_user_membership_query(
                request.user.id, site_id, "role in ('INSTR','ASSIST')")
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
        allowed = user.is_superuser
        if not allowed:
            site = models.Site.objects.get(pk=site_id)
            allowed = site.access=='ANON' or \
                (user.is_authenticated() and site.access=='LOGIN')
        if not allowed:
            allowed = _fast_user_membership_query(user.id, site_id)
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

#-----------------------------------------------------------

def user_filters(user):
    """Returns a dict of filters for Item, Site, etc. querysets,
    based on the given user's permissions."""
    # TODO, figure out a way of EXPLAIN'ing these queries! I have no
    # idea of their complexity.
    if user.is_anonymous():
        # then only anonymous-access sites are available.
        filters = {'items': Q(site__access='ANON'),
                   'sites': Q(access='ANON'),
                   'instructors': Q(), # TODO: do we really need a filter here?
                   }
    else:
        # logged-in users have access to sites which are of the
        # LOGIN class ('all logged-in users') or in which they
        # have explicit Member-ship.
        filters = {
            'items': (Q(site__access__in=('LOGIN','ANON')) \
                          | Q(site__member__user=user)),
            'sites': (Q(access__in=('LOGIN','ANON')) | Q(member__user=user)),
            'instructors': Q(), # TODO: do we really need a filter here?
            }
    return filters

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
