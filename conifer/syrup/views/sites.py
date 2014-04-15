from _common import *
from search  import *
from conifer.libsystems.evergreen.support import initialize, E1
from conifer.plumbing.hooksystem          import *
from django.conf                          import settings
if hasattr(settings, 'OPENSRF_STAFF_USERID'): # TODO: we need an explicit 'we do updates' flag
    from conifer.libsystems.evergreen import opensrf


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

def _add_or_edit_site(request, instance=None, basis=None):
    is_add = (instance is None)
    
    # Are we looking up owners, or selecting them from a fixed list?
    owner_mode = 'lookup' if gethook('fuzzy_person_lookup') else 'select'

    if is_add:
        instance = models.Site()
        if basis:
            dct = dict((k,v) for k,v in basis.__dict__.items() 
                       if not k.startswith('_')
                       and not k in ['start_term_id', 'end_term_id'])
            del dct['id']
            instance.__dict__.update(dct)

    if request.method != 'POST':
        form = NewSiteForm(instance=instance)
        return g.render('edit_site.xhtml', **locals())
    else:
        POST = request.POST.copy() # because we may mutate it.
        if owner_mode == 'lookup':
            # then the owner may be a username instead of an ID, and
            # the user may not exist in the local database.
            userid = POST.get('owner', '').strip()
            is_barcode = re.search('\d{14}', userid)
            if userid and (not userid.isdigit() or is_barcode):
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

            if 'basis' in POST:
                # We are duplicating a site. Copy all the items over into the new site.
                source_site = models.Site.objects.get(pk=POST['basis'])
                _copy_contents(request, source_site, site)
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
    timeframe = request.session.get('timeframe', 0)
    time_query = models.Term.timeframe_query(timeframe)
    return g.render('my_sites.xhtml', **locals())

def my_tests(request):
    return g.render('my_test.xhtml', **locals())

#add occurence value to sites
def add_to_sites(sites):
    term_sites = []
    i = 0
    for site in sites:
        term_sites.append([i,site])
        i = i + 1

    return term_sites

#get specified terms if provided
def get_sel_terms(request):
    start_term = None
    end_term = None

    if request.method == 'POST':
       sel_start = int(request.POST['site_start_term'])
       sel_end = int(request.POST['site_end_term'])
       if sel_start > 0 and sel_end > 0:
           start_term = models.Term.objects.get(pk=sel_start)
           end_term = models.Term.objects.get(pk=sel_end)

    return start_term, end_term

#get ids for selected sites
def get_sel_sites(request):
    selected = []
    if request.method == 'POST':
       sites_count = int(request.POST['sites_count'])
       if sites_count > 0:
           for i in range(sites_count):
              site_bx = 'site_%d' % i
              if site_bx in request.POST:
                 site_sel = request.POST[site_bx]
                 selected.append(int(site_sel))
    return selected

#copy sites to new terms
def duplicate_sites(request,sel_sites,new_start_term,new_end_term):
    duplicated = []
    if len(sel_sites) > 0 and new_start_term is not None and new_end_term is not None:
        for sel in sel_sites:
            sel_site = models.Site.objects.get(pk=sel)
            course_site = models.Site.objects.create(
               course = sel_site.course,
               start_term = new_start_term,
               end_term = new_end_term,
               owner = sel_site.owner,
               service_desk = sel_site.service_desk)

            _copy_contents(request, sel_site, course_site)
            duplicated.append(course_site.pk)
    return duplicated
 

#set up query for browse display
def setup_site_list(browse_option, time_query, dup_list):
    sites = None
    blocks = None
    if browse_option == 'Instructor':
        if len(dup_list) == 0:
           sites = list(models.Site.objects.order_by('owner__last_name', 'course__department__name', 'course__code').
                    select_related().filter(time_query))
        else:
           sites = list(models.Site.objects.order_by('owner__last_name', 'course__department__name', 'course__code').
                    select_related().filter(id__in=dup_list))
        sites = add_to_sites(sites)
        blocks = itertools.groupby(sites, lambda s: s[1].owner.last_name)
    elif browse_option == 'Course':
        if len(dup_list) == 0:
           sites = list(models.Site.objects.order_by('course__code', 'owner__last_name', 'course__department__name').
                    select_related().filter(time_query))
        else:
           sites = list(models.Site.objects.order_by('course__code', 'owner__last_name', 'course__department__name').
                    select_related().filter(id__in=dup_list))
        sites = add_to_sites(sites)
        blocks = itertools.groupby(sites, lambda s: s[1].course.code)
    else:
        if len(dup_list) == 0:
            sites = list(models.Site.objects.order_by('course__department__name', 'course__code', 'owner__last_name').
                    select_related().filter(time_query))
        else:
            sites = list(models.Site.objects.order_by('course__department__name', 'course__code', 'owner__last_name').
                    select_related().filter(id__in=dup_list))
        sites = add_to_sites(sites)
        blocks = itertools.groupby(sites, lambda s: s[1].course.department)

    return sites, blocks

def browse(request, browse_option='Department'):
    #the defaults should be moved into a config file or something...
    page_num = int(request.GET.get('page', 1))
    count    = int(request.GET.get('count', 5))

    sel_sites = get_sel_sites(request)
    start_term, end_term = get_sel_terms(request)
    timeframe = request.session.get('timeframe', 0)
    time_query = models.Term.timeframe_query(timeframe)

    term_sites = []
    show_terms = 0
    queryset = None
    if request.method == 'POST':
        term_sites = duplicate_sites(request,sel_sites,start_term,end_term)
        
    sites, blocks = setup_site_list(browse_option, time_query, term_sites)

    if not request.user.is_anonymous():
        if request.user.can_create_sites() and request.method == 'GET':
            show_terms = int(request.GET.get('termdup', 0))
            if show_terms > 0:
                instance = models.Site()
                form = NewSiteForm(instance=instance)
    return g.render('browse_index.xhtml', **locals())


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
    level = request.REQUEST.get('level').strip()
    include_students = (request.REQUEST.get('includeStudents') == 'true')
    results = callhook('fuzzy_person_lookup', query, include_students, level) or []
    limit = 10
    resp = {'results': results[:limit], 
            'notshown': max(0, len(results) - limit)}
    return HttpResponse(simplejson.dumps(resp),
                        content_type='application/json')


def _revert_parms(request, source_site):
    cnt = 0
    def revert_item(parent, (item, subitems)):
        update_status = False
        if hasattr(settings, 'OPENSRF_STAFF_USERID'): 
            update_status = True
            dct = dict((k,v) for k,v in item.__dict__.items() if not k.startswith('_'))
            dct['parent_heading_id'] = parent.id if parent else None
            barcode = dct['barcode']
            orig_prefix = dct['orig_prefix']
            orig_call = dct['orig_callno']
            orig_suffix = dct['orig_suffix']
            orig_desk = dct['circ_desk']
            orig_modifier = dct['circ_modifier']

            if barcode and orig_call and orig_desk and orig_modifier:
                update_status = opensrf.ils_item_update(barcode, orig_prefix, orig_call,
                                    orig_suffix, orig_modifier, orig_desk)
                #print "update_status", update_status
        if update_status:
            for sub in subitems:
                revert_item(parent, sub)
        else:
            return simple_message(_('Unable to update'),
                _('Sorry, unable to finish updates, %d processed' % cnt))

    for branch in source_site.item_tree():
        revert_item(None, branch)

def site_revert_parms(request, site_id):
    site = get_object_or_404(models.Site, pk=site_id)
    if request.method != 'POST':
        return g.render('revert_confirm.xhtml', **locals())
    _revert_parms(request, site)
    return HttpResponseRedirect('../')

def site_clipboard_copy_from(request, site_id):
    site = get_object_or_404(models.Site, pk=site_id)
    request.session['copy_source'] = site_id
    return simple_message(_('Ready to copy.'),
                          _('This site has been marked as the copying source. Visit the new site, '
                            'and click "Paste to Here," to copy this site\'s materials into the new site.'))


def _copy_contents(request, source_site, dest_site):
    item_map = {}

    def process_item(parent, (item, subitems,extra1,extra2)):
        dct = dict((k,v) for k,v in item.__dict__.items() if not k.startswith('_'))
        old_id = dct['id']
        del dct['id']
        dct['parent_heading_id'] = parent.id if parent else None
        newitem = models.Item.objects.create(**dct)
        newitem.site = dest_site
        newitem.save()
        item_map[old_id] = newitem.id
        for sub in subitems:
            process_item(newitem, sub)

    for branch in source_site.item_tree():
        process_item(None, branch)
    request.session['last_paste'] = (source_site.id, dest_site.id, item_map.values())

def site_clipboard_paste_to(request, site_id):
    source_id = request.session['copy_source']
    source_site = get_object_or_404(models.Site, pk=source_id)
    site = get_object_or_404(models.Site, pk=site_id)
    if request.method != 'POST':
        return g.render('site_confirm_paste.xhtml', **locals())
    _copy_contents(request, source_site, site)
    return HttpResponseRedirect('../')

def site_clipboard_paste_undo(request, site_id):
    site = get_object_or_404(models.Site, pk=site_id)
    source_id, _site_id, item_list = request.session.get('last_paste', (0,0,0))
    if _site_id != site.id:     # should never happen
        return HttpResponseRedirect('../')
    source_site = get_object_or_404(models.Site, pk=source_id)
    if request.method != 'POST':
        return g.render('site_confirm_paste_undo.xhtml', **locals())
    for item_id in item_list:
        try:
            site.item_set.get(pk=item_id).delete()
        except:
            pass
    del request.session['last_paste']
    return HttpResponseRedirect('../')


def site_clipboard_copy_whole(request, site_id):
    site = get_object_or_404(models.Site, pk=site_id)
    return _add_or_edit_site(request, basis=site)
