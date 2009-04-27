from _common import *
from django.utils.translation import ugettext as _
from search import *

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
        (u'ANON', _(u'Anyone on the planet may access this site.')),
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
        return HttpResponseRedirect(reverse('my_courses'))
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

