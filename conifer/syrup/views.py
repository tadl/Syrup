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
import django.forms
from datetime import datetime
from generics import *
from gettext import gettext as _ # fixme, is this the right function to import?
from django.utils import simplejson
import sys

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
                                next=request.GET.get('next'))
        else:
            userid, password = request.POST['userid'], request.POST['password']
            next = request.POST['next']
            user = authenticate(username=userid, password=password)
            if user is None:
                return g.render('auth/login.xhtml', err=_('Invalid username or password. Please try again.'), next=next)
            elif not user.is_active:
                return g.render('auth/login.xhtml', err=_('Sorry, this account has been disabled.'), next=next)
            else:
                login(request, user)
                return HttpResponseRedirect(request.POST.get('next', '/syrup/'))
    elif path == 'logout':
        logout(request)
        return HttpResponseRedirect('/syrup/')
    else:
        return HttpResponse('auth_handler: ' + path)

#------------------------------------------------------------
# Authorization

def instructors_only(handler):
    def hdlr(request, course_id, *args, **kwargs):
        allowed = request.user.is_superuser
        if not allowed:
            cursor = django.db.connection.cursor()
            cursor.execute('select count(*) from syrup_member where user_id=%s and course_id=%s',                       
                           [request.user.id, int(course_id)])
            res = cursor.fetchall()
            cursor.close()
            allowed = res[0][0]
        if allowed:
            return handler(request, course_id, *args, **kwargs)
        else:
            return HttpResponseForbidden(_('Only instructors may edit courses.'))
    return hdlr

#------------------------------------------------------------

def welcome(request):
    return g.render('welcome.xhtml')

def open_courses(request):
    page_num = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 5))
    paginator = Paginator(models.Course.objects.all(), count) # fixme, what filter?
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
        paginator = Paginator(models.Course.objects.all(), count) # fixme, what filter?
    else:
        paginator = Paginator(models.Course.objects.all(), count) # fixme, what filter?
        
    return g.render('instructors.xhtml', paginator=paginator,
                    page_num=page_num,
                    count=count)

def user_prefs(request):
    return g.render('simplemessage.xhtml',
                    title=_('Sorry...'), 
                    content=_('The Preferences page isn\'t ready yet.'))

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
        # fixme, course filter should not be (active=True) but based on user identity.
        paginator = Paginator(models.Course.objects.all(), count)

        return g.render('courses.xhtml', paginator=paginator,
            page_num=page_num,
            count=count)

    return g.render('browse_courses.xhtml')

@login_required
def my_courses(request):
    return g.render('my_courses.xhtml')

def course_detail(request, course_id):
    course = get_object_or_404(models.Course, pk=course_id)
    if course.access != 'ANON' and request.user.is_anonymous():
        #fixme, don't stop access just if anonymous, but rather if not
        #allowed to access. We need to set up a permissions model.
        return login_required(lambda *args: None)(request)
    return g.render('course_detail.xhtml', course=course)

def course_search(request, course_id):
    course = get_object_or_404(models.Course, pk=course_id)
    return search(request, in_course=course)


#------------------------------------------------------------
# Creating a new course

class NewCourseForm(ModelForm):
    class Meta:
        model = models.Course
        exclude = ('passkey','access')

    def clean_code(self):
        v = (self.cleaned_data.get('code') or '').strip()
        is_valid_func = models.course_codes.course_code_is_valid
        if (not is_valid_func) or is_valid_func(v):
            return v
        else:
            raise ValidationError, _('invalid course code')


# hack the new-course form if we have course-code lookup
COURSE_CODE_LIST = bool(models.course_codes.course_code_list)
COURSE_CODE_LOOKUP_TITLE = bool(models.course_codes.course_code_lookup_title)

if COURSE_CODE_LIST:
    from django.forms import Select
    course_list = models.course_codes.course_code_list()
    choices = [(a,a) for a in course_list]
    choices.sort()
    empty_label = u'---------'
    choices.insert(0, ('', empty_label))
    NewCourseForm.base_fields['code'].widget = Select(
        choices = choices)
    NewCourseForm.base_fields['code'].empty_label = empty_label
    
@login_required
def add_new_course(request):
    if not request.user.has_perm('add_course'):
        return HttpResponseForbidden('You are not allowed to create course sites.') # fixme, prettier msg.
    return add_or_edit_course(request)

@instructors_only
def edit_course(request, course_id):
    instance = get_object_or_404(models.Course, pk=course_id)
    return add_or_edit_course(request, instance=instance)
    
def add_or_edit_course(request, instance=None):
    is_add = (instance is None)
    if is_add:
        instance = models.Course()
    current_access_level = not is_add and instance.access or None
    example = models.course_codes.course_code_example
    if request.method != 'POST':
        form = NewCourseForm(instance=instance)
        return g.render('edit_course.xhtml', **locals())
    else:
        form = NewCourseForm(request.POST, instance=instance)
        if not form.is_valid():
            return g.render('edit_course.xhtml', **locals())
        else:
            form.save()
            course = form.instance
            if course.access == u'INVIT' and not course.passkey:
                course.generate_new_passkey()
                course.save()
            assert course.id
            user_in_course = models.Member.objects.filter(user=request.user,course=course)
            if not user_in_course: # for edits, might already be!
                mbr = course.member_set.create(user=request.user, role='INSTR')
                mbr.save()
            
            if is_add or (current_access_level != course.access):
                # we need to configure permissions.
                return HttpResponseRedirect(course.course_url('edit/permission/'))
            else:
                return HttpResponseRedirect('../') # back to main view.

def add_new_course_ajax_title(request):
    course_code = request.GET['course_code']
    title = models.course_codes.course_code_lookup_title(course_code)
    return HttpResponse(simplejson.dumps({'title':title}))

def edit_course_permissions(request, course_id):
    course = get_object_or_404(models.Course, pk=course_id)
    choose_access = django.forms.Select(choices=[
        (u'CLOSE', _(u'No students: this site is closed.')),
        (u'STUDT', _(u'Students in my course -- I will provide section numbers')),
        (u'INVIT', _(u'Students in my course -- I will share an Invitation Code with them')),
        (u'LOGIN', _(u'All Reserves patrons'))])
    if request.method != 'POST':
        return g.render('edit_course_permissions.xhtml', **locals())
    else:
        POST = request.POST

        if 'action_change_code' in POST:
            # update invitation code -------------------------------------
            course.generate_new_passkey()
            course.access = u'INVIT'
            course.save()
            return HttpResponseRedirect('.')

        elif 'action_save_instructor' in POST:
            # update instructor details ----------------------------------
            iname = POST.get('new_instructor_name','').strip()
            irole = POST.get('new_instructor_role')

            def get_record_for(username):
                instr = models.maybe_initialize_user(iname)
                if instr:
                    try:
                        return models.Member.objects.get(user=instr, course=course)
                    except models.Member.DoesNotExist:
                        return models.Member.objects.create(user=instr, course=course)

            # add a new instructor
            if iname:
                instr = get_record_for(iname)
                if instr:       # else? should have an error.
                    instr.role = irole
                    instr.save()
                else:
                    instructor_error = 'No such user: %s' % iname
                    return g.render('edit_course_permissions.xhtml', **locals())


            # removing and changing roles of instructors
            to_change_role = [(int(name.rsplit('_', 1)[-1]), POST[name]) \
                                  for name in POST if name.startswith('instructor_role_')]
            to_remove = [int(name.rsplit('_', 1)[-1]) \
                             for name in POST if name.startswith('instructor_remove_')]
            for instr_id, newrole in to_change_role:
                if not instr_id in to_remove:
                    instr = models.Member.objects.get(pk=instr_id, course=course)
                    instr.role = newrole
                    instr.save()
            for instr_id in to_remove:
                # todo, should warn if deleting yourself!
                instr = models.Member.objects.get(pk=instr_id, course=course)
                instr.delete()
            # todo, should have some error-reporting.
            return HttpResponseRedirect('.')

        elif 'action_save_student' in POST:
            # update student details ------------------------------------
            access = POST.get('access')
            course.access = access
            course.save()
            if course.access == u'STUDT':
                raise NotImplementedError, 'No course sections yet! Coming soon.'
            return HttpResponseRedirect('.')

@instructors_only
def delete_course(request, course_id):
    course = get_object_or_404(models.Course, pk=course_id)
    if request.POST.get('confirm_delete'):
        course.delete()
        return HttpResponseRedirect('/syrup/course/')
    else:
        return HttpResponseRedirect('../')

#------------------------------------------------------------

@login_required                 # must be, to avoid/audit brute force attacks.
def course_invitation(request):
    if request.method != 'POST':
        return g.render('course_invitation.xhtml', code='', error='',
                        **locals())
    else:
        code = request.POST.get('code', '').strip()
        # todo, a pluggable passkey implementation would normalize the code here.
        if not code:
            return HttpResponseRedirect('.')
        try:
            # note, we only allow the passkey if access='INVIT'.
            crs = models.Course.objects.filter(access='INVIT').get(passkey=code)
        except models.Course.DoesNotExist:
            # todo, do we need a formal logging system? Or a table for
            # invitation failures? They should be captured somehow, I
            # think. Should we temporarily disable accounts after
            # multiple failures?
            print >> sys.stdout, '[%s] WARN: Invitation failure, user %r gave code %r' % \
                (datetime.now(), request.user.username, code)
            error = _('The code you provided is not valid.')
            return g.render('course_invitation.xhtml', **locals())

        # the passkey is good; add the user if not already a member.
        if not models.Member.objects.filter(user=request.user, course=crs):
            mbr = models.Member.objects.create(user=request.user, course=crs, 
                                               role='STUDT')
            mbr.save()
        return HttpResponseRedirect(crs.course_url())
        
#------------------------------------------------------------

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


@instructors_only
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
        return HttpResponseForbidden(_('not an editor')) # fixme, prettier msg?

    item_type = request.GET.get('item_type')
    assert item_type, _('No item_type parameter was provided.')

    # for the moment, only HEADINGs, URLs and ELECs can be added.
    assert item_type in ('HEADING', 'URL', 'ELEC'), \
        _('Sorry, only HEADINGs, URLs and ELECs can be added right now.')

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

@instructors_only
def item_edit(request, course_id, item_id):
    course = get_object_or_404(models.Course, pk=course_id)
    item = get_object_or_404(models.Item, pk=item_id, course__id=course_id)
    item_type = item.item_type
    template = 'item_add_%s.xhtml' % item_type.lower()
    parent_item = item.parent_heading
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
    assert item.item_type == 'ELEC', _('Can only download ELEC documents!')
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
            course_results = models.Course.objects.filter(course_query).all()
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


#------------------------------------------------------------
# administrative options

def admin_index(request):
    return g.render('admin/index.xhtml')

# fixme, no auth or permissions stuff yet.

class TermForm(ModelForm):
    class Meta:
        model = models.Term

    class Index:
        title = _('Terms')
        all   = models.Term.objects.order_by('start', 'code').all
        cols  = ['code', 'name', 'start', 'finish']
        links = [0,1]

    clean_name = strip_and_nonblank('name')
    clean_code = strip_and_nonblank('code')

    def clean(self):
        cd = self.cleaned_data
        s, f = cd.get('start'), cd.get('finish')
        if (s and f) and s >= f:
            raise ValidationError, _('start must precede finish')
        return cd

admin_terms = generic_handler(TermForm)

class DeptForm(ModelForm):
    class Meta:
        model = models.Department

    class Index:
        title = _('Departments')
        all   = models.Department.objects.order_by('abbreviation').all
        cols  = ['abbreviation', 'name']
        links = [0,1]

    clean_abbreviation = strip_and_nonblank('abbreviation')
    clean_name = strip_and_nonblank('name')

admin_depts = generic_handler(DeptForm)


class NewsForm(ModelForm):
    class Meta:
        model = models.NewsItem

    class Index:
        title = _('News Items')
        all   = models.NewsItem.objects.order_by('-id').all
        cols  = ['id', 'subject', 'published']
        links = [0, 1]

    clean_subject = strip_and_nonblank('subject')
    clean_body = strip_and_nonblank('body')

admin_news = generic_handler(NewsForm)
