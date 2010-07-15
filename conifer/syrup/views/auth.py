from _common import *

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
