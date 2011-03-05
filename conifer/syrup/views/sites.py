from _common import *
from search  import *

#-----------------------------------------------------------------------------
# Creating a new site

class NewSiteForm(ModelForm):
    class Meta:
        model = models.Site
        exclude = ('access',)

    def clean_end_term(self):
        cd = self.cleaned_data
        if cd['start_term'].start > cd['end_term'].start:
            raise ValidationError(
                'The end-term precedes the start-term.')
        return cd['end_term']

    def __init__(self, *args, **kwargs):
        owner = self.base_fields['owner']
        owner.label_from_instance = lambda u: '%s (%s)' % (
            u.get_list_name(), u.username)
        owner.queryset = User.objects.order_by('last_name', 'first_name',
                                               'username')

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
    
    # Are we looking up owners, or selecting them from a fixed list?
    owner_mode = 'lookup' if gethook('fuzzy_person_lookup') else 'select'

    if is_add:
        instance = models.Site()
    if request.method != 'POST':
        form = NewSiteForm(instance=instance)
        return g.render('edit_site.xhtml', **locals())
    else:
        POST = request.POST.copy() # because we may mutate it.
        if owner_mode == 'lookup':
            # then the owner may be a username instead of an ID, and
            # the user may not exist in the local database.
            userid = POST.get('owner', '').strip()
            if userid and not userid.isdigit():
                try:
                    user = User.objects.get(username=userid)
                except User.DoesNotExist:
                    user = User.objects.create(username=userid)
                    user.save()
                    user.maybe_decorate()
                    user.save()
                POST['owner'] = user.id

        form = NewSiteForm(POST, instance=instance)
        if not form.is_valid():
            return g.render('edit_site.xhtml', **locals())
        else:
            form.save()
            site = form.instance
            assert site.id

            if is_add:
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
        (u'LOGIN', _(u'Login required.')),
        (u'RESTR', _(u'Login required; only members can access electronic documents.')),
        (u'MEMBR', _(u'Members only.')),
        (u'CLOSE', _(u'Instructors only: this site is closed.')),
        ]

    choose_access = django.forms.RadioSelect(choices=choices)

    show_add_section_panel = gethook('derive_group_code_from_section')

    if request.method != 'POST':
        return g.render('edit_site_permissions.xhtml', **locals())
    else:
        POST = request.POST
        message = 'Changes saved.' # default
        message_iserror = False

        if 'action_access_level' in POST:
            access = POST.get('access')
            site.access = access
            message = 'Security level changed: "%s"' % dict(choices)[access]

        elif 'action_add_member' in POST:
            userid = request.POST.get('userid')
            role = request.POST.get('role')
            try:
                user = User.objects.get(username=userid)
            except User.DoesNotExist:
                user = User.objects.create(username=userid)
                user.save()
                user.maybe_decorate()
                user.save()
            group = models.Group.objects.get(site=site, external_id=None)
            mbr, created = models.Membership.objects.get_or_create(
                group=group, user=user, defaults=dict(role=role))
            if created:
                message = '%s has been added as a member (role: %s).' % (
                    user.get_full_name() or user.username, mbr.get_role_display())
            else:
                mbr.role = role
                mbr.save()
                message = '%s: role changed to %s.' % (
                    user.get_full_name() or user.username, 
                    mbr.get_role_display())
            
        elif 'action_add_group' in POST:
            section = POST.get('section', '').strip()
            groupcode = None
            if section:
                groupcode = callhook('derive_group_code_from_section', 
                                     site, section)
            if not groupcode:
                groupcode = POST.get('groupcode','').strip()
            
            if not groupcode:
                message = 'No group code or section number provided.'
                message_iserror = True
            else:
                group, created = models.Group.objects.get_or_create(
                    site=site, external_id=groupcode)
                message = 'Group %s added.' % groupcode
        site.save()
        return g.render('edit_site_permissions.xhtml', **locals())

@instructors_only
def edit_site_permissions_delete_group(request, site_id):
    site = get_object_or_404(models.Site, pk=site_id)
    groupId = request.REQUEST.get('id')
    group = get_object_or_404(models.Group, site=site, pk=groupId)
    group.delete()
    return HttpResponse('')

@instructors_only
def delete_site(request, site_id):
    site = get_object_or_404(models.Site, pk=site_id)
    if request.POST.get('confirm_delete'):
        site.delete()
        return HttpResponseRedirect(reverse(my_sites))
    else:
        return HttpResponseRedirect('../')


@login_required
def my_sites(request):
    return g.render('my_sites.xhtml')

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
                              _('Sorry, but you cannot join this site '
                                'at this time.'))
    elif request.method != 'POST':
        return g.render('site_join.xhtml', site=site)
    else:
        group = models.Group.objects.get(site=site, external_id=None)
        mbr = models.Membership.objects.create(user=request.user,
                                               group=group, role='STUDT')
        mbr.save()
        return HttpResponseRedirect(site.site_url())


@admin_only
def site_fuzzy_user_lookup(request):
    query = request.REQUEST.get('q').lower().strip()
    include_students = (request.REQUEST.get('includeStudents') == 'true')
    results = callhook('fuzzy_person_lookup', query, include_students) or []
    limit = 10
    resp = {'results': results[:limit], 
            'notshown': max(0, len(results) - limit)}
    return HttpResponse(simplejson.dumps(resp),
                        content_type='application/json')

