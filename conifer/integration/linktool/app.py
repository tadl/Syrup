from conifer.syrup.views._common import *
from django.contrib.auth         import authenticate, login
from conifer.syrup               import models
from conifer.syrup.views         import genshi_namespace
from conifer.plumbing.genshi_support import TemplateSet

g = TemplateSet([HERE('integration/linktool/templates'),
                 HERE('templates')], 
                genshi_namespace)


def linktool_welcome(request, command=u''):
    #return g.render('index.xhtml')
    user = authenticate(request=request)
    if user is None:
        return HttpResponseForbidden('You are not allowed here.')
    else:
        login(request, user)
        extsite = request.session['clew-site'] = request.GET['site']
        extrole = request.session['clew-role'] = request.GET['role']

        
        return HttpResponse("""<html><head/><body onload="top.location='%s';">"""
                            """Redirecting to the library reserves system...</body></html>""" % (
                request.META['SCRIPT_NAME'] or '/'))
