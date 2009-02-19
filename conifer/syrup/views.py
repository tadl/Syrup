from django.http import HttpResponse, HttpResponseRedirect
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
import conifer.genshi_support as g
import re
from conifer.syrup import models
from django.contrib.auth.models import User
from django.db.models import Q
from datetime import datetime

#------------------------------------------------------------
# Authentication

def auth_handler(request, path):
    if path == 'login/':
        if request.method == 'GET':
            next=request.GET.get('next', '/syrup/')
            if request.user.is_authenticated():
                return HttpResponseRedirect(next)
            else:
                return g.render('auth/login.xhtml', 
                                next=request.GET.get('next'),
                                err=None # fixme, this shouldn't be
                                         # necessary. Genshi should treat
                                         # missing names as None, but something
                                         # is wrong.
                                )
        else:
            userid, password = request.POST['userid'], request.POST['password']
            next = request.POST['next']
            user = authenticate(username=userid, password=password)
            if user is None:
                return g.render('auth/login.xhtml', err='Invalid username or password. Please try again.', next=next)
            elif not user.is_active:
                return g.render('auth/login.xhtml', err='Sorry, this account has been disabled.', next=next)
            else:
                login(request, user)
                return HttpResponseRedirect(request.POST.get('next', '/syrup/'))
    elif path == 'logout':
        logout(request)
        return HttpResponseRedirect('/syrup/')
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

def user_prefs(request):
    return g.render('simplemessage.xhtml',
                    title='Sorry...', 
                    content='The Preferences page isn\'t ready yet.')

def browse_courses(request, browse_option=''):
    #the defaults should be moved into a config file or something...
    page_num = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 5))

    if browse_option == 'instructors':
        paginator = Paginator(models.UserProfile.active_instructors().
            order_by('user__last_name'), count)

        return g.render('instructors.xhtml', paginator=paginator,
            page_num=page_num,
            count=count)

    elif browse_option == 'departments':
        paginator = Paginator(models.Department.objects.filter(active=True), count)

        return g.render('departments.xhtml', paginator=paginator,
            page_num=page_num,
            count=count)
    elif browse_option == 'courses':
        paginator = Paginator(models.Course.objects.filter(active=True), count)

        return g.render('courses.xhtml', paginator=paginator,
            page_num=page_num,
            count=count)

    return g.render('browse_courses.xhtml')

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

def course_search(request, course_id):
    course = get_object_or_404(models.Course, pk=course_id)
    return search(request, in_course=course)

def instructor_detail(request, instructor_id):
    page_num = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 5))
    paginator = Paginator(models.Course.objects.
        filter(member__id=instructor_id).
        filter(active=True).order_by('title'), count)

    return g.render('courses.xhtml', paginator=paginator,
            page_num=page_num,
            count=count)

def department_detail(request, department_id):
    page_num = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 5))
    paginator = Paginator(models.Course.objects.
        filter(department__id=department_id).
        filter(active=True).order_by('title'), count)

    return g.render('courses.xhtml', paginator=paginator,
            page_num=page_num,
            count=count)

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

def _heading_url(request, item):
    return HttpResponseRedirect(item.url)

def _heading_detail(request, item):
    """Display a heading. Show the subitems for this heading."""
    return g.render('item_heading_detail.xhtml', item=item)


# fixme, not just login required! Must be in right course.
@login_required
def item_add(request, course_id, item_id):
    # The parent_item_id is the id for the parent-heading item. Zero
    # represents 'top-level', i.e. the new item should have no
    # heading. 
    #For any other number, we must check that the parent
    # item is of the Heading type.
    parent_item_id = item_id
    if parent_item_id=='0':
        parent_item = None
        course = get_object_or_404(models.Course, pk=course_id)
    else:
        parent_item = get_object_or_404(models.Item, pk=parent_item_id, course__id=course_id)
        assert parent_item.item_type == 'HEADING', 'Can only add items to headings!'
        course = parent_item.course

    if not course.can_edit(request.user):
        return HttpResponseForbidden('not an editor') # fixme, prettier msg?

    item_type = request.GET.get('item_type')
    assert item_type, 'No item_type parameter was provided.'

    # for the moment, only HEADINGs, URLs and ELECs can be added.
    assert item_type in ('HEADING', 'URL', 'ELEC'), \
        'Sorry, only HEADINGs, URLs and ELECs can be added right now.'

    if request.method == 'GET':
        item = models.Item()    # dummy object
        return g.render('item_add_%s.xhtml' % item_type.lower(),
                        **locals())
    else:
        # fixme, this will need refactoring. But not yet.
        author = request.user.get_full_name() or request.user.username
        if item_type == 'HEADING':
            title = request.POST.get('title', '').strip()
            if not title:
                # fixme, better error handling.
                return HttpResponseRedirect(request.get_full_path())
            else:
                item = models.Item(
                    course=course,
                    item_type='HEADING',
                    parent_heading=parent_item,
                    title=title,
                    author=author,
                    activation_date=datetime.now(),
                    last_modified=datetime.now())
                item.save()
        elif item_type == 'URL':
            title = request.POST.get('title', '').strip()
            url = request.POST.get('url', '').strip()
            if not (title and url):
                # fixme, better error handling.
                return HttpResponseRedirect(request.get_full_path())
            else:
                item = models.Item(
                    course=course,
                    item_type='URL',
                    parent_heading=parent_item,
                    title=title,
                    author=author,
                    activation_date=datetime.now(),
                    last_modified=datetime.now(),
                    url = url)
                item.save()
        elif item_type == 'ELEC':
            title = request.POST.get('title', '').strip()
            upload = request.FILES.get('file')
            if not (title and upload):
                # fixme, better error handling.
                return HttpResponseRedirect(request.get_full_path())
            item = models.Item(
                course=course,
                item_type='ELEC',
                parent_heading=parent_item,
                title=title,
                author=author,
                activation_date=datetime.now(),
                last_modified=datetime.now(),
                fileobj_mimetype = upload.content_type,
                )
            item.fileobj.save(upload.name, upload)
            item.save()
        else:
            raise NotImplementedError

        if parent_item:
            return HttpResponseRedirect(parent_item.item_url('meta'))
        else:
            return HttpResponseRedirect(course.course_url())

# fixme, not just login required! Must be in right course.
@login_required
def item_edit(request, course_id, item_id):
    course = get_object_or_404(models.Course, pk=course_id)
    item = get_object_or_404(models.Item, pk=item_id, course__id=course_id)
    template = 'item_add_%s.xhtml' % item.item_type.lower()
    if request.method == 'GET':
        return g.render(template, **locals())
    else:
        if 'file' in request.FILES:
            # this is a 'replace-current-file' action.
            upload = request.FILES.get('file')
            item.fileobj.save(upload.name, upload)
            item.fileobj_mimetype = upload.content_type
        else:
            # generally update the item.
            [setattr(item, k, v) for (k,v) in request.POST.items()]
        item.save()
        return HttpResponseRedirect(item.parent_url())
        
    
def item_download(request, course_id, item_id, filename):
    course = get_object_or_404(models.Course, pk=course_id)
    item = get_object_or_404(models.Item, pk=item_id, course__id=course_id)
    assert item.item_type == 'ELEC', 'Can only download ELEC documents!'
    fileiter = item.fileobj.chunks()
    resp = HttpResponse(fileiter)
    resp['Content-Type'] = item.fileobj_mimetype or 'application/octet-stream'
    #resp['Content-Disposition'] = 'attachment; filename=%s' % name
    return resp
    
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

def search(request, in_course=None):
    ''' Need to work on this, the basic idea is
        - put an entry point for instructor and course listings
        - page through item entries
        If in_course is provided, then limit search to the contents of the specified course.
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
        results_list = models.Item.objects.filter(item_query).order_by('title')
        if in_course:
            results_list = results_list.filter(course=in_course)
        results_len = len(results_list)
        paginator = Paginator( results_list,
            count)

        #course search
        if in_course:
            # then no course search is necessary.
            course_list = []; course_len = 0
        else:
            course_query = get_query(query_string, ['title', 'department__name'])
            print 'course_query'
            print course_query
            course_results = models.Course.objects.filter(course_query).filter(active=True)
            # course_list = models.Course.objects.filter(course_query).filter(active=True).order_by('title')[0:5]
            course_list = course_results.order_by('title')[0:5]
            #there might be a better way of doing this, though instr and course tables should not be expensive to query
            #len directly on course_list will reflect limit
            course_len = len(course_results)

        #instructor search
        instr_query = get_query(query_string, ['user__last_name'])
        instructor_results = models.Member.objects.filter(instr_query).filter(role='INSTR')
        if in_course:
            instructor_results = instructor_results.filter(course=in_course)
        instructor_list = instructor_results.order_by('user__last_name')[0:5]
        instr_len = len(instructor_results)
    elif in_course:
        # we are in a course, but have no query? Return to the course-home page.
        return HttpResponseRedirect('../')
    else:
        results_list = models.Item.objects.order_by('title')
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

    return g.render('search_results.xhtml', **locals())

