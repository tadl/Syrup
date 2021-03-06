import os
from _common import *
from search  import *

#-----------------------------------------------------------------------------

def welcome(request):
    user = request.user
    if user.is_authenticated() and user.sites():
        return HttpResponseRedirect('site/') # My Sites
    else:
        return HttpResponseRedirect('browse/')

# MARK: propose we get rid of this. We already have a 'Sites' browser.
def open_sites(request):
    page_num = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 5))
    paginator = Paginator(models.Site.objects.all(), count) # fixme, what filter?
    return g.render('open_sites.xhtml', paginator=paginator,
                    page_num=page_num,
                    count=count)
# MARK: propose we drop this too. We have a browse.
def instructors(request):
    page_num = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 5))
    action = request.GET.get('action', 'browse')
    if action == 'join':
        paginator = Paginator(models.User.active_instructors(), count)
    elif action == 'drop':
        paginator = Paginator(models.Site.objects.all(), count) # fixme, what filter?
    else:
        paginator = Paginator(models.Site.objects.all(), count) # fixme, what filter?
        
    return g.render('instructors.xhtml', paginator=paginator,
                    page_num=page_num,
                    count=count)

def instructor_search(request, instructor):
    return search(request, with_instructor=instructor)

def user_prefs(request):
    if request.method != 'POST':
        return g.render('prefs.xhtml')
    else:
        profile = request.user.get_profile()
        profile.wants_email_notices = bool(request.POST.get('wants_email_notices'))
        profile.save()
        return HttpResponseRedirect('../')

def timeframe(request):
    tf = int(request.REQUEST.get('timeframe', '0'))
    request.session['timeframe'] = tf
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '../'))

def instructor_detail(request, instructor_id):
    page_num = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 5))
    '''
    i am not sure this is the best way to go from instructor
    to site
    '''
    sites = models.Site.objects.filter(member__user=instructor_id,
                                           member__role='INSTR')
    # TODO: fixme, user_filters is no more.
    filters = user_filters(request.user)
    courses = courses.filter(filters['courses'])
    paginator = Paginator(courses.order_by('title'), count)

    '''
    no concept of active right now, maybe suppressed is a better
    description anyway?
    '''
        # filter(active=True).order_by('title'), count)
    instructor = models.User.objects.get(pk=instructor_id)
    return g.render('courses.xhtml', 
                    custom_title=_('Courses taught by %s') % instructor.get_full_name(),
                    paginator=paginator,
                    page_num=page_num,
                    count=count)

def department_detail(request, department_id):
    page_num = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 5))

    paginator = Paginator(models.Site.objects.
        filter(department__id=department_id).
        order_by('title'), count)

    department = models.Department.objects.get(pk=department_id)

    return g.render('courses.xhtml', 
            custom_title=_('Courses with Materials in %s') % department.name,
            paginator=paginator,
            page_num=page_num,
            count=count)

