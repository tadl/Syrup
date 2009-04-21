from _common import *
from django.utils.translation import ugettext as _

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
        return g.render('item/item_metadata.xhtml', course=item.course,
                        item=item)

def _heading_url(request, item):
    return HttpResponseRedirect(item.url)

def _heading_detail(request, item):
    """Display a heading. Show the subitems for this heading."""
    return g.render('item/item_heading_detail.xhtml', item=item)


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
        siblings = course.item_set.filter(parent_heading=None)
    else:
        parent_item = get_object_or_404(models.Item, pk=parent_item_id, course__id=course_id)
        assert parent_item.item_type == 'HEADING', _('You can only add items to headings!')
        course = parent_item.course
        siblings = course.item_set.filter(parent_heading=parent_item)

    try:
        next_order = 1 + max(i.sort_order for i in siblings)
    except:
        next_order = 0
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
        return g.render('item/item_add_%s.xhtml' % item_type.lower(),
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
                    sort_order = next_order,
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
                    sort_order = next_order,
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
                sort_order = next_order,
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
    # this chunk stolen from item_add(). Refactor.
    parent_item_id = item_id
    if parent_item_id=='0':
        parent_item = None
        course = get_object_or_404(models.Course, pk=course_id)
        siblings = course.item_set.filter(parent_heading=None)
    else:
        parent_item = get_object_or_404(models.Item, pk=parent_item_id, course__id=course_id)
        assert parent_item.item_type == 'HEADING', _('You can only add items to headings!')
        course = parent_item.course
        siblings = course.item_set.filter(parent_heading=parent_item)

    try:
        next_order = 1 + max(i.sort_order for i in siblings)
    except:
        next_order = 0

    #----------

    if request.method != 'POST':
        return g.render('item/item_add_cat_search.xhtml', results=[], query='', 
                        course=course, parent_item=parent_item)

    # POST handler
    query     = request.POST.get('query','').strip()
    raw_pickitem = request.POST.get('pickitem', '').strip()
    if not raw_pickitem:
        # process the query.
        assert query, 'must provide a query.'
        results = lib_integration.cat_search(query)
        return g.render('item/item_add_cat_search.xhtml', 
                        results=results, query=query, 
                        course=course, parent_item=parent_item)
    else:
        # User has selected an item; add it to course site.
        #fixme, this block copied from item_add. refactor.
        parent_item_id = item_id
        if parent_item_id == '0': 
            # no heading (toplevel)
            parent_item = None
            course = get_object_or_404(models.Course, pk=course_id)
        else:
            parent_item = get_object_or_404(models.Item, pk=parent_item_id, course__id=course_id)
            assert parent_item.item_type == 'HEADING', _('You can only add items to headings!')
            course = parent_item.course
        if not course.can_edit(request.user):
            return _access_denied(_('You are not an editor.'))

        pickitem = simplejson.loads(raw_pickitem)
        dublin = marcxml_dictionary_to_dc(pickitem)

        item = course.item_set.create(parent_heading=parent_item,
                                      sort_order=next_order,
                                      title=dublin.get('dc:title','Untitled'),
                                      item_type='PHYS')
        item.save()

        for dc, value in dublin.items():
            md = item.metadata_set.create(item=item, name=dc, value=value)
        # store the whole darn MARC-dict as well (JSON)
        item.metadata_set.create(item=item, name='syrup:marc', value=raw_pickitem)
        item.save()
        return HttpResponseRedirect('../../../%d/' % item.id)

#------------------------------------------------------------

#this is used in item_edit.
metadata_formset_class = modelformset_factory(models.Metadata, 
                                              fields=['name','value'], 
                                              extra=3, can_delete=True)

@instructors_only
def item_edit(request, course_id, item_id):
    course = get_object_or_404(models.Course, pk=course_id)
    item = get_object_or_404(models.Item, pk=item_id, course__id=course_id)
    item_type = item.item_type
    template = 'item/item_add_%s.xhtml' % item_type.lower()
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
        
@instructors_only
def item_delete(request, course_id, item_id):
    course = get_object_or_404(models.Course, pk=course_id)
    item = get_object_or_404(models.Item, pk=item_id, course__id=course_id)
    if request.method != 'POST':
        return g.render('item/item_delete_confirm.xhtml', **locals())
    else:
        if 'yes' in request.POST:
            # I think Django's ON DELETE CASCADE-like behaviour will
            # take care of the sub-items.
            if item.parent_heading:
                redir = HttpResponseRedirect(item.parent_heading.item_url('meta'))
            else:
                redir = HttpResponseRedirect(course.course_url())
            item.delete()
            return redir
        else:
            return HttpResponseRedirect('../meta')
    
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
        return g.render('item/item_relocate.xhtml', **locals())
    else:
        newheading = int(request.POST['heading'])
        if newheading == 0:
            new_parent = None
        else:
            new_parent = course.item_set.get(pk=newheading)
            if item in new_parent.hierarchy():
                # then we would create a cycle. Bail out.
                return simple_message(_('Impossible item-move!'), 
                                      _('You cannot make an item a descendant of itself!'))
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
        # dispatch based on what 'step' we are at.
        step = post('step')     
        func = {'1': _phys_checkout_get_patron,
                '2':_phys_checkout_do_checkout,
                '3':_phys_checkout_do_another,
                }[step]
        return func(request)

def _phys_checkout_get_patron(request):
    post           = lambda k: request.POST.get(k, '').strip()
    patron, item   = post('patron'), post('item')
    msg            = lib_integration.patron_info(patron)
    if not msg['success']:
        return simple_message(_('Invalid patron barcode'),
                              _('No such patron could be found.'))
    else:
        patron_descrip = '%s (%s) &mdash; %s' % (
            msg['personal'], msg['home_library'], msg['screenmsg'])
        return g.render('phys/checkout.xhtml', step=2, 
                        patron=patron, patron_descrip=patron_descrip)

def _phys_checkout_do_checkout(request):
    post           = lambda k: request.POST.get(k, '').strip()
    patron, item   = post('patron'), post('item')
    patron_descrip = post('patron_descrip')

    # make sure the barcode actually matches with a known barcode in
    # Syrup. We only checkout what we know about.
    matches = models.Item.with_barcode(item)
    if not matches:
        is_successful = False
        item_descrip  = None
    else:
        msg_status   = lib_integration.item_status(item)
        msg_checkout = lib_integration.checkout(patron, item)
        is_successful = msg_checkout['success']
        item_descrip = '%s &mdash; %s' % (
            msg_status['title'], msg_status['status'])

    # log the checkout attempt.
    log_entry = models.CheckInOut.objects.create(
        is_checkout = True,
        is_successful = is_successful,
        staff = request.user,
        patron = patron,
        patron_descrip = patron_descrip,
        item = item,
        item_descrip = item_descrip)
    log_entry.save()

    if not matches:
        return simple_message(
            _('Item not found in Reserves'),
            _('This item does not exist in the Reserves database! '
              'Cannot check it out.'))
    else:
        return g.render('phys/checkout.xhtml', step=3, 
                        patron=patron, item=item,
                        patron_descrip=patron_descrip,
                        checkout_result=msg_checkout,
                        item_descrip=item_descrip)

def _phys_checkout_do_another(request):
    post           = lambda k: request.POST.get(k, '').strip()
    patron         = post('patron')
    patron_descrip = post('patron_descrip')
    return g.render('phys/checkout.xhtml', step=2, 
                    patron=patron,
                    patron_descrip=patron_descrip)

#------------------------------------------------------------

@admin_only        
def phys_mark_arrived(request):
    if request.method != 'POST':
        return g.render('phys/mark_arrived.xhtml')
    else:
        barcode = request.POST.get('item', '').strip()
        already = models.PhysicalObject.by_barcode(barcode)
        if already:
            msg = _('This item has already been marked as received. Date received: %s')
            msg = msg % str(already.received)
            return simple_message(_('Item already marked as received'), msg)
        bib_id  = lib_integration.barcode_to_bib_id(barcode)
        if not bib_id:
            return simple_message(_('Item not found'), 
                                  _('No item matching this barcode could be found.'))

        marcxml = lib_integration.bib_id_to_marcxml(bib_id)
        dct     = marcxml_to_dictionary(marcxml)
        dublin  = marcxml_dictionary_to_dc(dct)
        # merge them
        dct.update(dublin)
        ranked = rank_pending_items(dct)
        return g.render('phys/mark_arrived_choose.xhtml', 
                        barcode=barcode,
                        bib_id=bib_id,
                        ranked=ranked,
                        metadata=dct)

@admin_only        
def phys_mark_arrived_match(request):
    choices = [int(k.split('_')[1]) for k in request.POST if k.startswith('choose_')]
    if not choices:
        return simple_message(_('No matching items selected!'),
                              _('You must select one or more matching items from the list.'))
    else:
        barcode = request.POST.get('barcode', '').strip()
        assert barcode
        smallint = request.POST.get('smallint', '').strip() or None
        try:
            phys = models.PhysicalObject(barcode=barcode,
                                         receiver = request.user,
                                         smallint = smallint)
            phys.save()
        except Exception, e:
            return simple_message(_('Error'), repr(e), go_back=True)

        for c in choices:
            item = models.Item.objects.get(pk=c)
            current_bc = item.barcode()
            if current_bc:
                item.metadata_set.filter(name='syrup:barcode').delete()
            item.metadata_set.create(name='syrup:barcode', value=barcode)
            item.save()
    return g.render('phys/mark_arrived_outcome.xhtml')
