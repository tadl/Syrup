from django.http import HttpResponse, HttpResponseRedirect
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
import conifer.genshi_support as g
from conifer.syrup import models
from django.contrib.auth.models import User

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
    page_num = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 5))
    paginator = Paginator(models.Course.objects.filter(moderated=False), count)
    return g.render('open_courses.xhtml', paginator=paginator,
                    page_num=page_num,
                    count=count)

#
#
def instructors(request):
    page_num = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 5))
    action = request.GET.get('action', 'browse')
    if action == 'join':
        paginator = Paginator(models.UserProfile.active_instructors(), count)
    elif action == 'drop':
        paginator = Paginator(models.Course.objects.filter(moderated=False), count)
    else:
        paginator = Paginator(models.Course.objects.filter(moderated=False), count)
        
    return g.render('instructors.xhtml', paginator=paginator,
                    page_num=page_num,
                    count=count)

def join_course(request):
    return g.render('join_course.xhtml')

@login_required
def my_courses(request):
    return g.render('my_courses.xhtml')

def course_detail(request, course_id):
    course = get_object_or_404(models.Course, pk=course_id)
    if course.moderated and request.user.is_anonymous():
        #fixme, don't stop access just if anonymous, but rather if not
        #allowed to access. We need to set up a permissions model.
        return login_required(lambda *args: None)(request)
    return g.render('course_detail.xhtml', course=course)

def item_detail(request, course_id, item_id):
    """Display an item (however that makes sense).""" 
    # really, displaying an item will vary based on what type of item
    # it is -- e.g. a URL item would redirect to the target URL. I'd
    # like this URL to be the generic dispatcher, but for now let's
    # just display some metadata about the item.
    return item_metadata(request, course_id, item_id)

def item_metadata(request, course_id, item_id):
    """Display a metadata page for the item."""
    course = get_object_or_404(models.Course, pk=course_id)
    item = get_object_or_404(models.Item, pk=item_id)
    assert item.course == course, 'Item not in course'
    return g.render('item_metadata.xhtml', course=course,
                    item=item)
    
