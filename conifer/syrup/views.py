from django.http import HttpResponse, HttpResponseRedirect
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
import conifer.genshi_support as g
from conifer.syrup import models

#------------------------------------------------------------

def auth_handler(request, path):
    if path == 'login/':
        if request.method == 'GET':
            return g.render('auth/login.xhtml')
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

#------------------------------------------------------------

def welcome(request):
    return g.render('welcome.xhtml')

def open_courses(request):
    pgstart = request.GET.get('start')
    if not pgstart:
        pgstart = 1
    paginator = Paginator(models.Course.objects.filter(moderated=False), 5)
    return g.render('open_courses.xhtml', paginator=paginator, pgstart=pgstart)

@login_required
def my_courses(request):
    return g.render('my_courses.xhtml')

@login_required
def course_detail(request, course_id):
    course = get_object_or_404(models.Course, pk=course_id)
    return g.render('course_detail.xhtml', course=course)
