#-----------------------------------------------------------------------------
# todo: break this up. It's getting long. I think we should have
# something like:
#
#   views/__init__.py                     # which imports:
#   views/course_site_handlers.py
#   views/search_stuff.py
#   views/add_edit_course.py
#   ...
#   views/common_imports.py              # imported by all.
#
# though these are just examples. Everything in views/* would include
# 'from common_imports import *' just to keep the imports
# tidy. Views/__init__ would import all the other bits: that ought to
# satisfy Django.

import warnings
from conifer.syrup import models
from datetime import datetime
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, SiteProfileNotAvailable
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils import simplejson
from generics import *
#from gettext import gettext as _ # fixme, is this the right function to import?
from django.utils.translation import ugettext as _
import conifer.genshi_support as g
import django.forms
import re
import sys
from django.forms.models import modelformset_factory
from conifer.custom import lib_integration

#-----------------------------------------------------------------------------
# Z39.50 Support
#
# This is experimental at this time, and requires some tricky Python
# imports as far as I can tell. For that reason, let's keep the Z39.50
# support optional for now. If you have Ply and PyZ3950, we'll load
# and use it; if not, no worries, everything else will workk.

try:
    # Graham needs this import hackery to get PyZ3950 working. Presumably
    # Art can 'import profile; import lex', so this hack won't run for
    # him.
    try:
        import profile
        import lex
        import yacc
    except ImportError:
        sys.modules['profile'] = sys # just get something called 'profile';
                                     # it's not actually used.
        import ply.lex              
        import ply.yacc             # pyz3950 thinks these are toplevel modules.
        sys.modules['lex'] = ply.lex
        sys.modules['yacc'] = ply.yacc

    # for Z39.50 support, not sure whether this is the way to go yet but
    # as generic as it gets
    from PyZ3950 import zoom, zmarc
except:
    warnings.warn('Could not load Z39.50 support.')

#-----------------------------------------------------------------------------
# poor-man's logging. Not sure we need more yet.

def log(level, msg):
    print >> sys.stderr, '[%s] %s: %s' % (datetime.now(), level.upper(), msg)

#-----------------------------------------------------------------------------
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
                return HttpResponseRedirect(request.POST.get('next', '/syrup/'))
    elif path == 'logout':
        logout(request)
        return HttpResponseRedirect('/syrup/')
    else:
        return HttpResponse('auth_handler: ' + path)

#-----------------------------------------------------------------------------
# Authorization

def _fast_user_membership_query(user_id, course_id, where=None):
    # I use a raw SQL query here because I want the lookup to be as
    # fast as possible. Caching would help too, but let's try this
    # first. (todo, review later.)
    query = ('select count(*) from syrup_member '
             'where user_id=%s and course_id=%s ')
    if where:
        query += (' and ' + where)
    cursor = django.db.connection.cursor()
    cursor.execute(query, [user_id, int(course_id)])
    res = cursor.fetchall()
    cursor.close()
    allowed = bool(res[0][0])
    return allowed
    
def _access_denied(request, message):
    if request.user.is_anonymous():
        # then take them to login screen....
        dest = '/accounts/login/?next=' + request.environ['PATH_INFO']
        return HttpResponseRedirect(dest)
    else:
        return g.render('simplemessage.xhtml',
                        title=_(_('Access denied.')), 
                        content=message,
                        _django_type=HttpResponseForbidden)

# todo, these decorators could be refactored.

# decorator
def instructors_only(handler):
    def hdlr(request, course_id, *args, **kwargs):
        allowed = request.user.is_superuser
        if not allowed:
            allowed = _fast_user_membership_query(
                request.user.id, course_id, "role in ('INSTR','PROXY')")
        if allowed:
            return handler(request, course_id, *args, **kwargs)
        else:
            return _access_denied(request, _('Only instructors are allowed here.'))
    return hdlr

# decorator
def members_only(handler):
    def hdlr(request, course_id, *args, **kwargs):
        user = request.user
        allowed = user.is_superuser
        if not allowed:
            course = models.Course.objects.get(pk=course_id)
            allowed = ((user.is_anonymous() and course.access=='ANON') or \
                       (user.is_authenticated() and course.access=='LOGIN'))
        if not allowed:
            allowed = _fast_user_membership_query(user.id, course_id)
        if allowed:
            return handler(request, course_id, *args, **kwargs)
        else:
            if course.access=='LOGIN':
                msg = _('Please log in, so that you can enter this site.')
            else:
                msg = _('Only course members are allowed here.')
            return _access_denied(request, msg)
    return hdlr

# decorator
def admin_only(handler):
    # fixme, 'admin' is vaguely defined for now as anyone who is
    # 'staff', i.e. who has access to the Django admin interface.
    def hdlr(request, *args, **kwargs):
        allowed = request.user.is_staff
        if allowed:
            return handler(request, *args, **kwargs)
        else:
            return _access_denied(request, _('Only administrators are allowed here.'))
    return hdlr

#decorator
def public(handler):
    # A no-op! Just here to be used to explicitly decorate methods
    # that are supposed to be public.
    return handler
#-----------------------------------------------------------------------------

def welcome(request):
    return g.render('welcome.xhtml')

# MARK: propose we get rid of this. We already have a 'Courses' browser.
def open_courses(request):
    page_num = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 5))
    paginator = Paginator(models.Course.objects.all(), count) # fixme, what filter?
    return g.render('open_courses.xhtml', paginator=paginator,
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
        paginator = Paginator(models.Course.objects.all(), count) # fixme, what filter?
    else:
        paginator = Paginator(models.Course.objects.all(), count) # fixme, what filter?
        
    return g.render('instructors.xhtml', paginator=paginator,
                    page_num=page_num,
                    count=count)

# MARK: propose we get rid of this. We have browse.
def departments(request):
    raise NotImplementedError


def user_prefs(request):
    if request.method != 'POST':
        return g.render('prefs.xhtml')
    else:
        profile = request.user.get_profile()
        profile.wants_email_notices = bool(request.POST.get('wants_email_notices'))
        profile.save()
        return HttpResponseRedirect('../')

def z3950_test(request):
    #testing JZKitZ3950 - it seems to work, but i have a character set problem
    #with the returned marc
    #nope - the problem is weak mapping with the limited solr test set
    #i think this can be sorted out

    #conn = zoom.Connection ('z3950.loc.gov', 7090)
    #conn = zoom.Connection ('webvoy.uwindsor.ca', 9000)
    #solr index with JZKitZ3950 wrapping
    conn = zoom.Connection ('127.0.0.1', 2100)
    # conn = zoom.Connection ('127.0.0.1', 2100)
    print("connecting...")
    conn.databaseName = 'Test'
    # conn.preferredRecordSyntax = 'XML'
    conn.preferredRecordSyntax = 'USMARC'
    query = zoom.Query ('CCL', 'ti="agar"')
    res = conn.search (query)
    collector = []
    # if we wanted to get into funkiness
    m = zmarc.MARC8_to_Unicode ()
    for r in res:
        print(type(r.data))
        print(type(m.translate(r.data)))
        rec = zmarc.MARC (r.data, strict=0)
        # rec = zmarc.MARC (rec, strict=0)
        collector.append(str(rec))

    conn.close ()
    res_str = "" . join(collector)
    return g.render('z3950_test.xhtml', res_str=res_str)

def graham_z3950_test(request):
    query = request.GET.get('query', '@and "Denis" "Gravel"')
    from conifer.libsystems.z3950 import yaz_search
    from conifer.libsystems.evergreen.item_status import lookup_availability
    host, db, query = ('dwarf.cs.uoguelph.ca:2210', 'conifer', query)
    #host, db, query = ('z3950.loc.gov:7090', 'VOYAGER', '@attr 1=4 @attr 4=1 "dylan"')
    results = yaz_search.search(host, db, query)
    for result in results:
        bibid = result.get('901c')
        if bibid:
            # it would be better to do these asynchronously.
            avail = lookup_availability(bibid) 
            if avail:
                result['avail'] = avail
    return g.render('graham_z3950_test.xhtml', results=results, query=query)

def browse(request, browse_option=''):
    #the defaults should be moved into a config file or something...
    page_num = int(request.GET.get('page', 1))
    count    = int(request.GET.get('count', 5))

    if browse_option == '':
        queryset = None
        template = 'browse_index.xhtml'
    elif browse_option == 'instructors':
        queryset = models.User.active_instructors()
        template = 'instructors.xhtml'
    elif browse_option == 'departments':
        queryset = models.Department.objects.filter(active=True)
        template = 'departments.xhtml'
    elif browse_option == 'courses':
        # fixme, course filter should not be (active=True) but based on user identity.
        queryset = models.Course.objects.all()
        template = 'courses.xhtml'

    paginator = queryset and Paginator(queryset, count) or None # index has no queryset.
    return g.render(template, paginator=paginator,
                    page_num=page_num,
                    count=count)

@login_required
def my_courses(request):
    return g.render('my_courses.xhtml')

def instructor_detail(request, instructor_id):
    page_num = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 5))
    '''
    i am not sure this is the best way to go from instructor
    to course
    '''
    courses = models.Course.objects.filter(member__user=instructor_id,
                                           member__role='INSTR')
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
    paginator = Paginator(models.Course.objects.
        filter(department__id=department_id).
        filter(active=True).order_by('title'), count)

    return g.render('courses.xhtml', paginator=paginator,
            page_num=page_num,
            count=count)

#-----------------------------------------------------------------------------
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

# if we have course-code lookup, hack lookup support into the new-course form.

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

#--------------------
    
@login_required
def add_new_course(request):
    if not request.user.has_perm('add_course'):
        return _access_denied(_('You are not allowed to create course sites.'))
    return _add_or_edit_course(request)

@instructors_only
def edit_course(request, course_id):
    instance = get_object_or_404(models.Course, pk=course_id)
    return _add_or_edit_course(request, instance=instance)
    
def _add_or_edit_course(request, instance=None):
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

# no access-control needed to protect title lookup.
def add_new_course_ajax_title(request):
    course_code = request.GET['course_code']
    title = models.course_codes.course_code_lookup_title(course_code)
    return HttpResponse(simplejson.dumps({'title':title}))

@instructors_only
def edit_course_permissions(request, course_id):
    course = get_object_or_404(models.Course, pk=course_id)
    # choices: make the access-choice labels more personalized than
    # the ones in 'models'.
    choices = [
        # note: I'm leaving ANON out for now, until we discuss it further.
        (u'CLOSE', _(u'No students: this site is closed.')),
        (u'STUDT', _(u'Students in my course -- I will provide section numbers')),
        (u'INVIT', _(u'Students in my course -- I will share an Invitation Code with them')),
        (u'LOGIN', _(u'All Reserves patrons'))]
    if models.course_sections.sections_tuple_delimiter is None:
        # no course-sections support? Then STUDT cannot be an option.
        del choices[1]
    choose_access = django.forms.Select(choices=choices)
        
    if request.method != 'POST':
        return g.render('edit_course_permissions.xhtml', **locals())
    else:
        POST = request.POST

        if 'action_change_code' in POST:
            # update invitation code -------------------------------------
            course.generate_new_passkey()
            course.access = u'INVIT'
            course.save()
            return HttpResponseRedirect('.#student_access')

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
            # drop all provided users. fixme, this could be optimized to do add/drops.
            models.Member.objects.filter(course=course, provided=True).delete()
            if course.access == u'STUDT':
                initial_sections = course.sections()
                # add the 'new section' if any
                new_sec = request.POST.get('add_section')
                new_sec = models.section_decode_safe(new_sec)
                if new_sec:
                    course.add_sections(new_sec)
                # remove the sections to be dropped
                to_remove = [models.section_decode_safe(name.rsplit('_',1)[1]) \
                                 for name in POST \
                                 if name.startswith('remove_section_')]
                course.drop_sections(*to_remove)
                student_names = models.course_sections.students_in(*course.sections())
                for name in student_names:
                    user = models.maybe_initialize_user(name)
                    if user:
                        if not models.Member.objects.filter(course=course, user=user):
                            mbr = models.Member.objects.create(
                                course=course, user=user, 
                                role='STUDT', provided=True)
                            mbr.save()
            else:
                pass
            course.save()
            return HttpResponseRedirect('.#student_access')

@instructors_only
def delete_course(request, course_id):
    course = get_object_or_404(models.Course, pk=course_id)
    if request.POST.get('confirm_delete'):
        course.delete()
        return HttpResponseRedirect('/syrup/course/')
    else:
        return HttpResponseRedirect('../')

#-----------------------------------------------------------------------------
# Course Invitation Code handler

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
            log('WARN', 'Invitation failure, user %r gave code %r' % \
                (datetime.now(), request.user.username, code))
            error = _('The code you provided is not valid.')
            return g.render('course_invitation.xhtml', **locals())

        # the passkey is good; add the user if not already a member.
        if not models.Member.objects.filter(user=request.user, course=crs):
            mbr = models.Member.objects.create(user=request.user, course=crs, 
                                               role='STUDT')
            mbr.save()
        return HttpResponseRedirect(crs.course_url())

#-----------------------------------------------------------------------------
# Course-instance handlers

@members_only
def course_detail(request, course_id):
    course = get_object_or_404(models.Course, pk=course_id)
    return g.render('course_detail.xhtml', course=course)

@members_only
def course_search(request, course_id):
    course = get_object_or_404(models.Course, pk=course_id)
    return search(request, in_course=course)

@members_only
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

@members_only
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
        assert parent_item.item_type == 'HEADING', _('You can only add items to headings!')
        course = parent_item.course

    if not course.can_edit(request.user):
        return _access_denied(_('You are not an editor.'))

    item_type = request.GET.get('item_type')
    assert item_type, _('No item_type parameter was provided.')

    # for the moment, only HEADINGs, URLs and ELECs can be added. fixme.
    assert item_type in ('HEADING', 'URL', 'ELEC', 'PHYS'), \
        _('Sorry, only HEADINGs, URLs and ELECs can be added right now.')

    if request.method != 'POST' and item_type == 'PHYS':
        # special handling: send to catalogue search
        return HttpResponseRedirect('cat_search/')

    if request.method != 'POST':
        item = models.Item()    # dummy object
        metadata_formset = metadata_formset_class(queryset=item.metadata_set.all())
        return g.render('item_add_%s.xhtml' % item_type.lower(),
                        **locals())
    else:
        # fixme, this will need refactoring. But not yet.
        author = request.user.get_full_name() or request.user.username
        item = models.Item()    # dummy object
        metadata_formset = metadata_formset_class(request.POST, queryset=item.metadata_set.all())
        assert metadata_formset.is_valid()
        def do_metadata(item):
            for obj in [obj for obj in metadata_formset.cleaned_data if obj]: # ignore empty dicts
                if not obj.get('DELETE'):
                    item.metadata_set.create(name=obj['name'], value=obj['value'])
            
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
                    )
                item.save()
                do_metadata(item)
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
                    url = url)
                item.save()
                do_metadata(item)
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
                fileobj_mimetype = upload.content_type,
                )
            item.fileobj.save(upload.name, upload)
            item.save()
            do_metadata(item)
            item.save()
        else:
            raise NotImplementedError

        if parent_item:
            return HttpResponseRedirect(parent_item.item_url('meta'))
        else:
            return HttpResponseRedirect(course.course_url())

@instructors_only
def item_add_cat_search(request, course_id, item_id):
    if request.method != 'POST':
        return g.render('item_add_cat_search.xhtml', results=[], query='@and dylan thomas')
    query = request.POST.get('query','').strip()
    _pickitem = request.POST.get('pickitem', '').strip()
    if not _pickitem:
        assert query, 'must provide a query.'
        from conifer.libsystems.z3950 import yaz_search
        host, db, query = ('dwarf.cs.uoguelph.ca:2210', 'conifer', query)
        #host, db = ('z3950.loc.gov:7090', 'VOYAGER')
        results = yaz_search.search(host, db, query)
        return g.render('item_add_cat_search.xhtml', results=results, query=query)
    else:
        #fixme, this block copied from item_add. refactor.
        parent_item_id = item_id
        if parent_item_id=='0':
            parent_item = None
            course = get_object_or_404(models.Course, pk=course_id)
        else:
            parent_item = get_object_or_404(models.Item, pk=parent_item_id, course__id=course_id)
            assert parent_item.item_type == 'HEADING', _('You can only add items to headings!')
            course = parent_item.course
        if not course.can_edit(request.user):
            return _access_denied(_('You are not an editor.'))

        pickitem = eval(_pickitem) # fixme, dangerous. cache result server-side instead, or encrypt it.
        item = course.item_set.create(parent_heading=parent_item,
                                      title=pickitem.get('245a', 'Untitled'),
                                      item_type='PHYS')
        item.save()
        # these are a temporary hack, must replace
        meta = [('245a', 'dc:title'), ('100a', 'dc:creator'), ('260b', 'dc:publisher'),
                ('260c', 'dc:date'), ('700a', 'dc:contributor')]
        for marc, dc in meta:
            value = pickitem.get(marc)
            if value:
                md = item.metadata_set.create(item=item, name=dc, value=value)
        item.metadata_set.create(item=item, name='syrup:marc', value=simplejson.dumps(pickitem))
        item.save()
        return HttpResponseRedirect('../../../%d/' % item.id)

metadata_formset_class = modelformset_factory(models.Metadata, 
                                              fields=['name','value'], 
                                              extra=3, can_delete=True)


@instructors_only
def item_edit(request, course_id, item_id):
    course = get_object_or_404(models.Course, pk=course_id)
    item = get_object_or_404(models.Item, pk=item_id, course__id=course_id)
    item_type = item.item_type
    template = 'item_add_%s.xhtml' % item_type.lower()
    parent_item = item.parent_heading

    if request.method != 'POST':
        metadata_formset = metadata_formset_class(queryset=item.metadata_set.all())
        return g.render(template, **locals())
    else:
        metadata_formset = metadata_formset_class(request.POST, queryset=item.metadata_set.all())
        assert metadata_formset.is_valid()
        if 'file' in request.FILES:
            # this is a 'replace-current-file' action.
            upload = request.FILES.get('file')
            item.fileobj.save(upload.name, upload)
            item.fileobj_mimetype = upload.content_type
        else:
            # generally update the item.
            [setattr(item, k, v) for (k,v) in request.POST.items()]
            # generally update the metadata
            item.metadata_set.all().delete()
            for obj in [obj for obj in metadata_formset.cleaned_data if obj]: # ignore empty dicts
                if not obj.get('DELETE'):
                    item.metadata_set.create(name=obj['name'], value=obj['value'])
                    
        item.save()
        return HttpResponseRedirect(item.parent_url())
        
    
@members_only
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


#-----------------------------------------------------------------------------
# Search and search support

def search(request, in_course=None):
    ''' Need to work on this, the basic idea is
        - put an entry point for instructor and course listings
        - page through item entries
        If in_course is provided, then limit search to the contents of the specified course.
    '''
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
        # we start with an empty results_list, as a default
        results_list = models.Item.objects.filter(pk=-1)

        # numeric search: If the query-string is a single number, then
        # we do an item-ID search, or a barcode search.  fixme:
        # item-ID is not a good short-id, since the physical item may
        # be represented in multiple Item records. We need a
        # short-number for barcodes.

        if re.match(r'\d+', query_string):
            # Search by short ID.
            results_list = models.Item.objects.filter(pk=query_string,
                                                      item_type='PHYS')
            if not results_list:
                # Search by barcode.
                results_list = models.Item.objects.filter(
                    item_type='PHYS',
                    metadata__name='syrup:barcode', 
                    metadata__value=query_string)
        else:
            # Textual (non-numeric) queries.
            item_query = get_query(query_string, ['title', 'metadata__value'])
                #need to think about sort order here, probably better by author (will make sortable at display level)
            results_list = models.Item.objects.filter(item_query)

        if in_course:
            results_list = results_list.filter(course=in_course)
        results_list = results_list.order_by('title')
        results_len = len(results_list)
        paginator = Paginator(results_list, count)

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

#-----------------------------------------------------------------------------
# Z39.50 support

def zsearch(request):
    ''' 
    '''
        
    page_num = int(request.GET.get('page', 1))
    count = int(request.POST.get('count', 5))

    if request.GET.get('page')==None and request.method == 'GET':
        targets_list = models.Target.objects.filter(active=True).order_by('name')
        targets_len = len(targets_list)
        return g.render('zsearch.xhtml', **locals())
    else:
            
        target = request.GET.get('target')
        if request.method == 'POST':
            target = request.POST['target']
        print("target is %s" % target)
            
        tquery = request.GET.get('query')
        if request.method == 'POST':
            tquery = request.POST['ztitle']
        search_target= models.Target.objects.get(name=target)
        conn = zoom.Connection (search_target.host, search_target.port)
        conn.databaseName = search_target.db
        conn.preferredRecordSyntax = search_target.syntax
        query = zoom.Query ('CCL', '%s="%s"' % ('ti',tquery))
        res = conn.search (query)
        print("results are %d" % len(res))
        collector = [(None,None)] * len(res)

        start = (page_num - 1) * count
        end = (page_num * count) + 1

        idx = start; 
        for r in res[start : end]:
                
            print("-> %d" % idx)
            if r.syntax <> 'USMARC':
                collector.pop(idx)
                collector.insert (idx,(None, 'Unsupported syntax: ' + r.syntax, None))
            else:
                raw = r.data

                # Convert to MARC
                marcdata = zmarc.MARC(raw)
                #print marcdata

                # Convert to MARCXML
                # marcxml = marcdata.toMARCXML()
                # print marcxml

                # How to Remove non-ascii characters (in case this is a problem)
                #marcxmlascii = unicode(marcxml, 'ascii', 'ignore').encode('ascii')
                
                bibid = marcdata.fields[1][0]
                title = " ".join ([v[1] for v in marcdata.fields [245][0][2]])

                # Amara XML tools would allow using xpath
                '''
                title = ""
                doc = binderytools.bind_string(marcxml)
                t = doc.xml_xpath("//datafield[@tag='245']/subfield[@code='a']")
                if len(title)>0:
                    title = t[0].xml_text_content()
                '''
                
                # collector.append ((bibid, title))
                #this is not a good situation but will leave for now
                #collector.append ((bibid, unicode(title, 'ascii', 'ignore')))

                collector.pop(idx)
                # collector.insert (idx,(bibid, unicode(title, 'ascii', 'ignore')))
                collector.insert (idx,(bibid, unicode(title, 'utf-8', 'ignore')))
            idx+=1

        conn.close ()
        paginator = Paginator(collector, count) 

    print("returning...")
    #return g.render('zsearch_results.xhtml', **locals())
    return g.render('zsearch_results.xhtml', paginator=paginator,
                    page_num=page_num,
                    count=count, target=target, tquery=tquery)


#-----------------------------------------------------------------------------
# Administrative options

@admin_only
def admin_index(request):
    return g.render('admin/index.xhtml')


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

admin_terms = generic_handler(TermForm, decorator=admin_only)


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

admin_depts = generic_handler(DeptForm, decorator=admin_only)

###
# graham - zap this if it messes anything up :-)
###
class TargetForm(ModelForm):
    class Meta:
        model = models.Target

    class Index:
        title = _('Targets')
        all   = models.Target.objects.order_by('name').all
        cols  = ['name', 'host']
        links = [0,1]

    clean_name = strip_and_nonblank('name')
    clean_host = strip_and_nonblank('host')

admin_targets = generic_handler(TargetForm, decorator=admin_only)
###


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

admin_news = generic_handler(NewsForm, decorator=admin_only)



#-----------------------------------------------------------------------------
# Course feeds

@public                         # and proud of it!
def course_feeds(request, course_id, feed_type):
    course = get_object_or_404(models.Course, pk=course_id)
    if feed_type == '':
        return g.render('feeds/course_feed_index.xhtml', 
                        course=course)
    else:
        items = course.items()
        def render_title(item):
            return item.title
        if feed_type == 'top-level':
            items = items.filter(parent_heading=None).order_by('-sort_order')
        elif feed_type == 'recent-changes':
            items = items.order_by('-last_modified')
        elif feed_type == 'tree':
            def flatten(nodes, acc):
                for node in nodes:
                    item, kids = node
                    acc.append(item)
                    flatten(kids, acc)
                return acc
            items = flatten(course.item_tree(), [])
            def render_title(item):
                if item.parent_heading:
                    return '%s :: %s' % (item.parent_heading.title, item.title)
                else:
                    return item.title
        lastmod = items and max(i.last_modified for i in items) or datetime.now()
        resp = g.render('feeds/course_atom.xml',
                        course=course,
                        feed_type=feed_type,
                        lastmod=lastmod,
                        render_title=render_title,
                        items=items,
                        root='http://%s' % request.get_host(),
                        _serialization='xml')
        resp['Content-Type'] = 'application/atom+xml'
        return resp



#------------------------------------------------------------
# resequencing items

def _reseq(request, course, parent_heading):
    new_order = request.POST['new_order'].split(',')
    # new_order is now a list like this: ['item_3', 'item_8', 'item_1', ...].
    # get at the ints.
    new_order = [int(n.split('_')[1]) for n in new_order]
    print >> sys.stderr, new_order
    the_items = list(course.item_set.filter(parent_heading=parent_heading).order_by('sort_order'))
    # sort the items by position in new_order
    the_items.sort(key=lambda item: new_order.index(item.id))
    for newnum, item in enumerate(the_items):
        item.sort_order = newnum
        item.save()
    return HttpResponse("'ok'");

@instructors_only
def course_reseq(request, course_id):
    course = get_object_or_404(models.Course, pk=course_id)
    parent_heading = None
    return _reseq(request, course, parent_heading)

@instructors_only
def item_heading_reseq(request, course_id, item_id):
    course = get_object_or_404(models.Course, pk=course_id)
    item = get_object_or_404(models.Item, pk=item_id, course__id=course_id)
    parent_heading = item
    return _reseq(request, course, parent_heading)


@instructors_only
def item_relocate(request, course_id, item_id):
    """Move an item from its current subheading to another one."""
    course = get_object_or_404(models.Course, pk=course_id)
    item = get_object_or_404(models.Item, pk=item_id, course__id=course_id)
    if request.method != 'POST':
        return g.render('item_relocate.xhtml', **locals())
    else:
        newheading = int(request.POST['heading'])
        if newheading == 0:
            new_parent = None
        else:
            new_parent = course.item_set.get(pk=newheading)
            if item in new_parent.hierarchy():
                # then we would create a cycle. Bail out.
                return g.render('simplemessage.xhtml',
                                title=_(_('Impossible item-move!')), 
                                content=_('You cannot make an item a descendant of itself!'))
        item.parent_heading = new_parent
        item.save()
        if new_parent:
            return HttpResponseRedirect(new_parent.item_url('meta'))
        else:
            return HttpResponseRedirect(course.course_url())
        
        

#-----------------------------------------------------------------------------
# Physical item processing

@admin_only                     # fixme, is this the right permission?
def phys_index(request):
    return g.render('phys/index.xhtml')

@admin_only                     # fixme, is this the right permission?
def phys_checkout(request):
    if request.method != 'POST':
        return g.render('phys/checkout.xhtml', step=1)
    else:
        post = lambda k: request.POST.get(k, '').strip()
        patron, item = post('patron'), post('item')
        if post('step') == '1':
            # patron entered, need item
            # first get patron data.
            msg = lib_integration.patron_info(patron)
            patron_descrip = '%s (%s) &mdash; %s' % (
                msg['personal'], msg['home_library'],
                msg['screenmsg'])
            return g.render('phys/checkout.xhtml', step=2, 
                            patron=patron, 
                            patron_descrip=patron_descrip)
        elif post('step') == '2':
            # patron + item. do SIP calls.
            # log the checkout in a local table.
            # also, make sure the barcode actually matches with a
            # known barcode in Syrup. We only checkout what we know
            # about.
            msg = lib_integration.item_status(item)
            item_descrip = '%s &mdash; %s' % (
                msg['title'], msg['status'])

            # do the checkout
            msg = lib_integration.checkout(patron, item)
            
            return g.render('phys/checkout.xhtml', step=3, 
                            patron=patron, item=item,
                            patron_descrip=post('patron_descrip'),
                            checkout_result=msg,
                            item_descrip=item_descrip)
        elif post('step') == '3':
            # continue after checkout. Go to 'checkout another item'.
            return g.render('phys/checkout.xhtml', step=2, 
                            patron=patron,
                            patron_descrip=post('patron_descrip'))
        
