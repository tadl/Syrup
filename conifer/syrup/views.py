from django.http import HttpResponse, HttpResponseRedirect
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
import conifer.genshi_support as g
import re
from conifer.syrup import models
from django.contrib.auth.models import User
from django.db.models import Q


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
    item = get_object_or_404(models.Item, pk=item_id, course__id=course_id)
    if item.url:
        return _heading_url(request, item)
    else:
        return item_metadata(request, course_id, item_id)

def item_metadata(request, course_id, item_id):
    """Display a metadata page for the item."""
    item = get_object_or_404(models.Item, pk=item_id, course__id=course_id)
    if item.item_type == 'HEADING':
        return _heading_detail(request, item)
    else:
        return g.render('item_metadata.xhtml', course=item.course,
                        item=item)

def item_edit(request, course_id, item_id):
    """Edit an item."""
    # For now, just pop to the Admin interface.
    admin_url = '/admin/syrup/item/%s/' % item_id
    return HttpResponseRedirect(admin_url)
    
def _heading_url(request, item):
    return HttpResponseRedirect(item.url)

def _heading_detail(request, item):
    """Display a heading. Show the subitems for this heading."""
    return g.render('item_heading_detail.xhtml', item=item)
    

def normalize_query(query_string,
                    findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                    normspace=re.compile(r'\s{2,}').sub):
    ''' Splits the query string in invidual keywords, getting rid of unecessary spaces
        and grouping quoted words together.
        Example:
        
        >>> normalize_query('  some random  words "with   quotes  " and   spaces')
        ['some', 'random', 'words', 'with quotes', 'and', 'spaces']
    
    '''
    return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)] 

def get_query(query_string, search_fields):
    ''' Returns a query, that is a combination of Q objects. That combination
        aims to search keywords within a model by testing the given search fields.
    
    '''
    query = None # Query to search for every search term        
    terms = normalize_query(query_string)
    for term in terms:
        or_query = None # Query to search for a given term in each field
        for field_name in search_fields:
            q = Q(**{"%s__icontains" % field_name: term})
            if or_query is None:
                or_query = q
            else:
                or_query = or_query | q
        if query is None:
            query = or_query
        else:
            query = query & or_query
    return query

#------------------------------------------------------------

def search(request):
    ''' Need to work on this, the basic idea is
        - put an entry point for instructor and course listings
        - page through item entries
    '''
    query_string = ''
    found_entries = None
    page_num = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 5))
    norm_query = ''
    query_string = ''
    

    #TODO: need to block or do something useful with blank query (seems dumb to do entire list)
    #if ('q' in request.GET) and request.GET['q']:
        
    if ('q' in request.GET):
        query_string = request.GET['q'].strip()

    if len(query_string) > 0:
        norm_query = normalize_query(query_string)

        #item search - this will be expanded
        item_query = get_query(query_string, ['title', 'author'])
        #need to think about sort order here, probably better by author (will make sortable at display level)
        results_list = models.Item.objects.filter(item_query).order_by('-date_created')
        results_len = len(results_list)
        paginator = Paginator( results_list,
            count)

        #course search
        course_query = get_query(query_string, ['title', 'department__name'])
        course_results = models.Course.objects.filter(course_query).filter(active=True)
        # course_list = models.Course.objects.filter(course_query).filter(active=True).order_by('title')[0:5]
        course_list = course_results.order_by('title')[0:5]
        #there might be a better way of doing this, though instr and course tables should not be expensive to query
        #len directly on course_list will reflect limit
        course_len = len(course_results)

        #instructor search
        instr_query = get_query(query_string, ['user__last_name'])
        instructor_results = models.Member.objects.filter(instr_query).filter(role='INSTR')
        instructor_list = instructor_results.order_by('user__last_name')[0:5]
        instr_len = len(instructor_results)
    else:
        results_list = models.Item.objects.order_by('-date_created')
        results_len = len(results_list)
        paginator = Paginator( results_list,
            count)
        course_results = models.Course.objects.filter(active=True)
        course_list = course_results.order_by('title')[0:5]
        course_len = len(course_results)
        instructor_results = models.Member.objects.filter(role='INSTR')
        instructor_list = instructor_results.order_by('user__last_name')[0:5]
        instr_len = len(instructor_results)

    #info for debugging
    '''
        print get_query(query_string, ['user__last_name'])
        print instructor_list
        print(norm_query)
        for term in norm_query:
            print term
    '''

    return g.render('search_results.xhtml', paginator=paginator,
                    page_num=page_num,
                    count=count, query_string=query_string, 
                    course_list=course_list,
                    instructor_list=instructor_list,
                    norm_query=norm_query, 
                    results_len=results_len,
                    course_len=course_len,
                    instr_len=instr_len)

