from conifer.here                    import HERE
from conifer.plumbing.genshi_support import TemplateSet
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


def linktool_welcome(request, command=u''):
    user = authenticate(request=request)
    if user is None:
        return HttpResponseForbidden('You are not allowed here.')
    else:
        login(request, user)
        extsite = request.session['clew-site'] = request.GET['site']
        extrole = request.session['clew-role'] = request.GET['role']
        related_sites = list(models.Site.objects.filter(group__external_id=extsite))
        if len(related_sites) == 1:
            return HttpResponse("<html><head/><body onload=\"top.location='%ssite/%s/';\">"
                                "Redirecting..."
                                "</body></html>" % (
                    request.META['SCRIPT_NAME'] or '/',
                    related_sites[0].id))
        elif len(related_sites):
            return g.render('whichsite.xhtml', **locals())
        elif extrole == 'Instructor':
            # This isn't quite right yet. I want to give the instructor a
            # chance to associate with an existing unassociated site in the
            # same term as the Sakai site. I don't want them to associate with
            # a site that's in an older Term, but should give them the change
            # to copy/reuse an old site. Or, they can make a brand-new Site if
            # they want. 

            # This reminds me that it should be a warning to edit an old site
            # (one in a past Term). Otherwise, profs will add items to old
            # sites, and think they are actually ordering stuff.

            possibles = models.Site.taught_by(user)
            if possibles:
                return g.render('associate.xhtml', **locals())
            else:
                return g.render('create_new.xhtml', **locals())
        else:
            return g.render('choose_dest.xhtml', **locals())

