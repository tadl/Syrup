from django.contrib.auth import authenticate, login
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden


def linktool_welcome(request):
    user = authenticate(request=request)
    if user is None:
        return HttpResponseForbidden('You are not allowed here.')
    else:
        login(request, user)
        request.session['clew-site'] = request.GET['site']
        return HttpResponse("""<html><head/><body onload="top.location='/%s';">"""
                            """Redirecting to the library system...</body></html>""" % (
                request.META['SCRIPT_NAME']))
