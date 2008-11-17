from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
import conifer.genshi_support as g
from conifer.syrup import models

@login_required
def index(request):
    return g.render('test.xhtml')

@login_required
def course_index(request, course_id):
    course = get_object_or_404(models.Course, pk=course_id)
    return g.render('course.xhtml', course=course)

def auth_handler(request, path):
    if path == 'login/':
        if request.method == 'GET':
            return g.render('login.xhtml')
        else:
            userid, password = request.POST['userid'], request.POST['password']
            user = authenticate(username=userid, password=password)
            if user is None:
                return HttpResponse('invalid login.')
            elif not user.is_active:
                return HttpResponse('disabled account.')
            else:
                login(request, user)
                return HttpResponseRedirect(request.POST['next'])
    elif path == 'logout':
        logout(request)
        return HttpResponse('Logged out. Thanks for coming!')
    else:
        return HttpResponse('auth_handler: ' + path)
