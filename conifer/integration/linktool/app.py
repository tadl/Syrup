from conifer.here                    import HERE
from conifer.plumbing.genshi_support import TemplateSet
from datetime                        import date, timedelta
from django.http                     import (HttpResponse, HttpResponseRedirect,
                                             HttpResponseNotFound,
                                             HttpResponseForbidden)
from django.contrib.auth             import authenticate, login
from conifer.syrup import models
from django.utils.translation    import ugettext as _
from conifer.plumbing.hooksystem import gethook, callhook

g = TemplateSet([HERE('integration/linktool/templates'),
                 HERE('templates')], 
                {'models': models, '_': _})


def linktool_welcome(request):
    user = authenticate(request=request)
    if user is None:
        return HttpResponseForbidden('You are not allowed here.')
    else:
        login(request, user)
        _role   = request.GET['role']
        extrole = request.session['clew-role'] = callhook('decode_role', _role) or _role
        extsite = request.session['clew-site'] = request.GET['site']

        related_sites = list(models.Site.objects.filter(group__external_id=extsite))
        if len(related_sites) == 1:
            site_url = related_sites[0].site_url()
            html     = ("<html><head/><body onload=\"top.location='%s';\">"
                        "Redirecting..."
                        "</body></html>") % site_url
            return HttpResponse(html)
        elif len(related_sites):
            return g.render('whichsite.xhtml', **locals())
        elif extrole == 'INSTR':
            # TODO: This reminds me that it should be a warning to
            # edit an old site (one in a past Term). Otherwise, profs
            # will add items to old sites, and think they are actually
            # ordering stuff.
            today     = date.today()
            possibles = list(models.Site.taught_by(user))
            current   = [s for s in possibles if s.term.midpoint() >= today]
            ancient   = [s for s in possibles if s.term.midpoint() < today]
            extsite   = ExternalSiteInfo(request)
            return g.render('associate.xhtml', **locals())
        else:
            # TODO: implement me
            return g.render('choose_dest.xhtml', **locals())

class ExternalSiteInfo(object):
    def __init__(self, request):
        extsite   = request.session['clew-site']
        extgroups = callhook('external_memberships', request.user.username)
        extsite   = [d for d in extgroups if d['group'] == extsite][0]
        self.__dict__.update(extsite)
        self.termcode   = self.terms and self.terms[0] or None
        self.coursecode = extsite['course']
        try:
            course = models.Course.objects.get(code=self.coursecode)
        except models.Course.DoesNotExist:
            course = None
            course = models.Course.objects.all()[0]
        try:
            term = models.Term.objects.get(code=self.termcode)
        except models.Term.DoesNotExist:
            term = None
            term = models.Term.objects.order_by('-start')[0]
        self.course_obj = course
        self.term_obj = term

    def is_currentish(self):
        today = date.today()
        return self.course_obj is not None and \
            self.term_obj and self.term_obj.midpoint() >= today

def linktool_new_site(request):
    extrole = request.session['clew-role']
    assert extrole == 'INSTR'
    assert request.user.can_create_sites(), \
        'Sorry, but you are not allowed to create sites.'
    extsite = ExternalSiteInfo(request)
    extgroups  = callhook('external_memberships', request.user.username)
    site = models.Site.objects.create(
        course = extsite.course_obj,
        term   = extsite.term_obj,
        owner  = request.user,
        service_desk = models.ServiceDesk.default())
    group = models.Group.objects.create(
        site        = site,
        external_id = extsite.group)
    models.Membership.objects.create(
        group = group, 
        user  = request.user, 
        role  = 'INSTR')
    return HttpResponseRedirect(site.site_url())

def linktool_associate(request):
    site = models.Site.objects.get(pk=request.GET['site'])
    assert site in request.user.sites(role='INSTR'), \
        'Not an instructor on this site! Cannot copy.'
    assert request.user.can_create_sites(), \
        'Sorry, but you are not allowed to create sites.'
    today = date.today()
    assert site.term.midpoint() >= today, \
        'Sorry, but you cannot associate to such an old site.'

    extsite = request.session['clew-site']
    extrole = request.session['clew-role']
    assert extrole == 'INSTR', \
        'Sorry, you are not an instructor on this Sakai site.'
    group = models.Group.objects.create(
        site        = site,
        external_id = extsite)
    models.Membership.objects.create(
        group = group, 
        user  = request.user, 
        role  = 'INSTR')
    return HttpResponseRedirect(site.site_url())

def linktool_copy_old(request):
    oldsite = models.Site.objects.get(pk=request.GET['site'])
    assert oldsite in request.user.sites(role='INSTR'), \
        'Not an instructor on this site! Cannot copy.'
    assert request.user.can_create_sites(), \
        'Sorry, but you are not allowed to create sites.'

    extsite = request.session['clew-site']
    extrole = request.session['clew-role']
    assert extrole == 'INSTR', \
        'Sorry, you are not an instructor on this Sakai site.'

    extgroups  = callhook('external_memberships', request.user.username)
    extsite    = [d for d in extgroups if d['group'] == extsite][0]
    coursecode = extsite['course']
    termcode   = extsite['terms'][0]

    course = oldsite.course     # fixme, this isn't right.
    try:
        #course = models.Course.objects.get(code=coursecode)
        term   = models.Term.objects.get(code=termcode)
    except:
        # note, this doesn't have to be an exception. I could provide
        # them with a form to specify the correct course and term
        # codes. But for now, we bail.
        return g.render('new_site_cannot.xhtml', **locals())
    site = models.Site.objects.create(
        course = course,
        term   = term,
        owner  = request.user,
        service_desk = models.ServiceDesk.default())
    group = models.Group.objects.create(
        site        = site,
        external_id = extsite)
    models.Membership.objects.create(
        group = group, 
        user  = request.user, 
        role  = 'INSTR')
    site.copy_resources_from(oldsite)
    return HttpResponseRedirect(site.site_url())
