from _common import *
from django.utils.translation import ugettext as _
from search import *

#-----------------------------------------------------------------------------
# Creating a new site

class NewSiteForm(ModelForm):
    class Meta:
        model = models.Site
        exclude = ('passkey','access')

    def clean_code(self):
        v = (self.cleaned_data.get('code') or '').strip()
        is_valid_func = models.campus.course_code_is_valid
        if (not is_valid_func) or is_valid_func(v):
            return v
        else:
            raise ValidationError, _('invalid course code')

# if we have course-code lookup, hack lookup support into the new-course form.

COURSE_CODE_LIST = bool(models.campus.course_code_list)
COURSE_CODE_LOOKUP_TITLE = bool(models.campus.course_code_lookup_title)

if COURSE_CODE_LIST:
    from django.forms import Select
    course_list = models.campus.course_code_list()
    choices = [(a,a) for a in course_list]
    choices.sort()
    empty_label = u'---------'
    choices.insert(0, ('', empty_label))
    NewSiteForm.base_fields['code'].widget = Select(
        choices = choices)
    NewSiteForm.base_fields['code'].empty_label = empty_label

#--------------------
    
@login_required
def add_new_site(request):
    if not request.user.can_create_sites():
        return _access_denied(_('You are not allowed to create sites.'))
    return _add_or_edit_site(request)

@instructors_only
def edit_site(request, site_id):
    instance = get_object_or_404(models.Site, pk=site_id)
    return _add_or_edit_site(request, instance=instance)
    
def _add_or_edit_site(request, instance=None):
    is_add = (instance is None)
    if is_add:
        instance = models.Site()
    current_access_level = not is_add and instance.access or None
    example = models.campus.course_code_example
    if request.method != 'POST':
        form = NewSiteForm(instance=instance)
        return g.render('edit_site.xhtml', **locals())
    else:
        form = NewSiteForm(request.POST, instance=instance)
        if not form.is_valid():
            return g.render('edit_site.xhtml', **locals())
        else:
            form.save()
            site = form.instance
            if site.access == u'INVIT' and not site.passkey:
                site.generate_new_passkey()
                site.save()
            assert site.id
            user_in_site = models.Member.objects.filter(user=request.user,site=site)
            if not user_in_site: # for edits, might already be!
                mbr = site.member_set.create(user=request.user, role='INSTR')
                mbr.save()
            
            if is_add or (current_access_level != site.access):
                # we need to configure permissions.
                return HttpResponseRedirect(site.site_url('edit/permission/'))
            else:
                return HttpResponseRedirect('../') # back to main view.

# no access-control needed to protect title lookup.
def add_new_site_ajax_title(request):
    course_code = request.GET['course_code']
    title = models.campus.course_code_lookup_title(course_code)
    return HttpResponse(simplejson.dumps({'title':title}))

@instructors_only
def edit_site_permissions(request, site_id):
    site = get_object_or_404(models.Site, pk=site_id)
    # choices: make the access-choice labels more personalized than
    # the ones in 'models'.
    choices = [
        # note: I'm leaving ANON out for now, until we discuss it further.
        (u'ANON', _(u'Anyone on the planet may access this site.')),
        (u'CLOSE', _(u'No students: this site is closed.')),
        (u'STUDT', _(u'Students in my course -- I will provide section numbers')),
        (u'INVIT', _(u'Students in my course -- I will share an Invitation Code with them')),
        (u'LOGIN', _(u'All Reserves patrons'))]
    if models.campus.sections_tuple_delimiter is None:
        # no course-sections support? Then STUDT cannot be an option.
        del choices[1]
    choose_access = django.forms.Select(choices=choices)
        
    if request.method != 'POST':
        return g.render('edit_site_permissions.xhtml', **locals())
    else:
        POST = request.POST

        if 'action_change_code' in POST:
            # update invitation code -------------------------------------
            site.generate_new_passkey()
            site.access = u'INVIT'
            site.save()
            return HttpResponseRedirect('.#student_access')

        elif 'action_save_instructor' in POST:
            # update instructor details ----------------------------------
            iname = POST.get('new_instructor_name','').strip()
            irole = POST.get('new_instructor_role')

            def get_record_for(username):
                instr = models.maybe_initialize_user(iname)
                if instr:
                    try:
                        return models.Member.objects.get(user=instr, site=site)
                    except models.Member.DoesNotExist:
                        return models.Member.objects.create(user=instr, site=site)

            # add a new instructor
            if iname:
                instr = get_record_for(iname)
                if instr:       # else? should have an error.
                    instr.role = irole
                    instr.save()
                else:
                    instructor_error = 'No such user: %s' % iname
                    return g.render('edit_site_permissions.xhtml', **locals())


            # removing and changing roles of instructors
            to_change_role = [(int(name.rsplit('_', 1)[-1]), POST[name]) \
                                  for name in POST if name.startswith('instructor_role_')]
            to_remove = [int(name.rsplit('_', 1)[-1]) \
                             for name in POST if name.startswith('instructor_remove_')]
            for instr_id, newrole in to_change_role:
                if not instr_id in to_remove:
                    instr = models.Member.objects.get(pk=instr_id, site=site)
                    instr.role = newrole
                    instr.save()
            for instr_id in to_remove:
                # todo, should warn if deleting yourself!
                instr = models.Member.objects.get(pk=instr_id, site=site)
                instr.delete()
            # todo, should have some error-reporting.
            return HttpResponseRedirect('.')

        elif 'action_save_student' in POST:
            # update student details ------------------------------------
            access = POST.get('access')
            site.access = access
            # drop all provided users. fixme, this could be optimized to do add/drops.
            models.Member.objects.filter(site=site, provided=True).delete()
            if site.access == u'STUDT':
                initial_sections = site.sections()
                # add the 'new section' if any
                new_sec = request.POST.get('add_section')
                new_sec = models.section_decode_safe(new_sec)
                if new_sec:
                    site.add_sections(new_sec)
                # remove the sections to be dropped
                to_remove = [models.section_decode_safe(name.rsplit('_',1)[1]) \
                                 for name in POST \
                                 if name.startswith('remove_section_')]
                site.drop_sections(*to_remove)
                student_names = models.campus.students_in(*site.sections())
                for name in student_names:
                    user = models.maybe_initialize_user(name)
                    if user:
                        if not models.Member.objects.filter(site=site, user=user):
                            mbr = models.Member.objects.create(
                                site=site, user=user, 
                                role='STUDT', provided=True)
                            mbr.save()
            else:
                pass
            site.save()
            return HttpResponseRedirect('.#student_access')

@instructors_only
def delete_site(request, site_id):
    site = get_object_or_404(models.Site, pk=site_id)
    if request.POST.get('confirm_delete'):
        site.delete()
        return HttpResponseRedirect(reverse('my_sites'))
    else:
        return HttpResponseRedirect('../')

#-----------------------------------------------------------------------------
# Site Invitation Code handler

@login_required                 # must be, to avoid/audit brute force attacks.
def site_invitation(request):
    if request.method != 'POST':
        return g.render('site_invitation.xhtml', code='', error='',
                        **locals())
    else:
        code = request.POST.get('code', '').strip()
        # todo, a pluggable passkey implementation would normalize the code here.
        if not code:
            return HttpResponseRedirect('.')
        try:
            # note, we only allow the passkey if access='INVIT'.
            crs = models.Site.objects.filter(access='INVIT').get(passkey=code)
        except models.Site.DoesNotExist:
            # todo, do we need a formal logging system? Or a table for
            # invitation failures? They should be captured somehow, I
            # think. Should we temporarily disable accounts after
            # multiple failures?
            log('WARN', 'Invitation failure, user %r gave code %r' % \
                (request.user.username, code))
            error = _('The code you provided is not valid.')
            return g.render('site_invitation.xhtml', **locals())

        # the passkey is good; add the user if not already a member.
        if not models.Member.objects.filter(user=request.user, site=crs):
            mbr = models.Member.objects.create(user=request.user, site=crs, 
                                               role='STUDT')
            mbr.save()
        return HttpResponseRedirect(crs.site_url())

#-----------------------------------------------------------------------------
# Site-instance handlers

@members_only
def site_detail(request, site_id):
    site = get_object_or_404(models.Site, pk=site_id)
    return g.render('site_detail.xhtml', site=site)

@members_only
def site_search(request, site_id):
    site = get_object_or_404(models.Site, pk=site_id)
    return search(request, in_site=site)

@login_required
def site_join(request, site_id):
    """Self-register into an open-registration site."""
    site = get_object_or_404(models.Site, pk=site_id)
    if not site.is_joinable_by(request.user):
        # user should never see this.
        return simple_message(_('You cannot join this site.'), 
                              _('Sorry, but you cannot join this site at this time.'))
    elif request.method != 'POST':
        return g.render('site_join.xhtml', site=site)
    else:
        mbr = models.Member.objects.create(user=request.user, site=site, role='STUDT')
        mbr.save()
        return HttpResponseRedirect(site.site_url())

       
