from _common import *
from search  import *

#-----------------------------------------------------------------------------
# Creating a new site

class NewSiteForm(ModelForm):
    class Meta:
        model = models.Site
        exclude = ('access',)

    def clean_code(self):
        v = (self.cleaned_data.get('code') or '').strip()
        is_valid_func = gethook('course_code_is_valid')
        if (not is_valid_func) or is_valid_func(v):
            return v
        else:
            raise ValidationError, _('invalid course code')

    def __init__(self, *args, **kwargs):
        owner = self.base_fields['owner']
        owner.label_from_instance = lambda u: u.get_list_name()
        owner.queryset = User.objects.order_by('last_name', 'first_name', 'username')

        super(NewSiteForm, self).__init__(*args, **kwargs)


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
            assert site.id

            if is_add or (current_access_level != site.access):
                # we need to configure permissions.
                return HttpResponseRedirect(site.site_url('edit/permission/'))
            else:
                return HttpResponseRedirect('../') # back to main view.

@instructors_only
def edit_site_permissions(request, site_id):
    site = get_object_or_404(models.Site, pk=site_id)
    # choices: make the access-choice labels more personalized than
    # the ones in 'models'.
    choices = [
        (u'ANON',  _(u'Everyone: no login required.')),
        (u'LOGIN', _(u'Members and non-members: login required.')),
        (u'MEMBR', _(u'Members only.')),
        (u'CLOSE', _(u'Instructors only: this site is closed.')),
        ]

    choose_access = django.forms.RadioSelect(choices=choices)
        
    if request.method != 'POST':
        return g.render('edit_site_permissions.xhtml', **locals())
    else:
        POST = request.POST

        if 'action_save_instructor' in POST:
            # update instructor details ----------------------------------
            iname = POST.get('new_instructor_name','').strip()
            irole = POST.get('new_instructor_role')

            def get_record_for(username):
                instr = models.maybe_initialize_user(iname)
                if instr:
                    try:
                        return models.Membership.objects.get(user=instr, site=site)
                    except models.Membership.DoesNotExist:
                        return models.Membership.objects.create(user=instr, site=site)

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
                    instr = models.Membership.objects.get(pk=instr_id, site=site)
                    instr.role = newrole
                    instr.save()
            for instr_id in to_remove:
                # todo, should warn if deleting yourself!
                instr = models.Membership.objects.get(pk=instr_id, site=site)
                instr.delete()
            # todo, should have some error-reporting.
            return HttpResponseRedirect('.')

        elif 'action_save_student' in POST:
            # update student details ------------------------------------
            access = POST.get('access')
            site.access = access
            # drop all provided users. fixme, this could be optimized to do add/drops.
            #models.Membership.objects.filter(site=site, provided=True).delete()
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
                        if not models.Membership.objects.filter(site=site, user=user):
                            mbr = models.Membership.objects.create(
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
    raise NotImplementedError

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
        mbr = models.Membership.objects.create(user=request.user, site=site, role='STUDT')
        mbr.save()
        return HttpResponseRedirect(site.site_url())

       
