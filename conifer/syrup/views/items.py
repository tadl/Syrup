from _common                     import *
from conifer.plumbing.hooksystem import *
from conifer.syrup               import integration
from xml.etree                   import ElementTree as ET
from collections                 import defaultdict

@members_only
def item_detail(request, site_id, item_id):
    """Display an item (however that makes sense).""" 
    # really, displaying an item will vary based on what type of item
    # it is -- e.g. a URL item would redirect to the target URL. I'd
    # like this URL to be the generic dispatcher, but for now let's
    # just display some metadata about the item.
    item = get_object_or_404(models.Item, pk=item_id, site__id=site_id)
    if item.url:
        return _heading_url(request, item)
    else:
        return item_metadata(request, site_id, item_id)

@members_only
def item_metadata(request, site_id, item_id):
    """Display a metadata page for the item."""
    item = get_object_or_404(models.Item, pk=item_id, site__id=site_id)
    if item.item_type == 'HEADING':
        return _heading_detail(request, item)
    else:
        item_declaration_required = item.needs_declaration_from(request.user)
        custom_declaration = callhook('download_declaration')
        return g.render('item/item_metadata.xhtml', site=item.site,
                        item_declaration_required=item_declaration_required,
                        custom_declaration=custom_declaration,
                        item=item)

@members_only
def item_declaration(request, site_id, item_id):
    assert request.method == 'POST'
    item = get_object_or_404(models.Item, pk=item_id, site__id=site_id)
    if item.item_type != 'ELEC':
        return HttpResponseNotFound('Items of this type are not downloadable.')
    else:
        # we don't actually need the declaration object for anything; we just
        # need to ensure one exists.
        models.Declaration.objects.get_or_create(item=item, user=request.user)
        return HttpResponse('OK')

def _heading_url(request, item):
    return HttpResponseRedirect(item.url)

def _heading_detail(request, item):
    """Display a heading. Show the subitems for this heading."""
    return g.render('item/item_heading_detail.xhtml', item=item)


@instructors_only
def item_add(request, site_id, item_id):
    # The parent_item_id is the id for the parent-heading item. Zero
    # represents 'top-level', i.e. the new item should have no
    # heading. 
    #For any other number, we must check that the parent
    # item is of the Heading type.
    parent_item_id = item_id
    if parent_item_id=='0':
        parent_item = None
        site = get_object_or_404(models.Site, pk=site_id)
        siblings = site.item_set.filter(parent_heading=None)
    else:
        parent_item = get_object_or_404(models.Item, pk=parent_item_id, site__id=site_id)
        assert parent_item.item_type == 'HEADING', _('You can only add items to headings!')
        site = parent_item.site
        siblings = site.item_set.filter(parent_heading=parent_item)

    try:
        next_order = 1 + max(i.sort_order for i in siblings)
    except:
        next_order = 0
    if not site.can_edit(request.user):
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
        item.item_type = item_type
        return g.render('item/item_add_%s.xhtml' % item_type.lower(),
                        **locals())
    else:
        # fixme, this will need refactoring. But not yet.
        author = request.user.get_full_name() or request.user.username
        item = models.Item()    # dummy object
        POST = request.POST.copy()
        def clean(key):
            return POST.get(key, '').strip()

        # Just for fun and experimentation: a basic Refworks/RIS importer. If
        # 'ris' appears in the POST, parse it as an RIS citation and expand
        # its components into the POST object.

        if clean('ris'):
            # use RIS (refworks) to populate fields
            pat = re.compile('^([A-Z][A-Z0-9])  - (.*)$')
            tmp = [x.groups() for x in 
                   [pat.match(line.strip()) for line in POST['ris'].split('\r\n')]
                   if x is not None]
            ris = defaultdict(list)
            for k, v in tmp:
                ris[k].append(v)
            def update(field, risfield, xlate=lambda x: x):
                if risfield in ris:
                    replacement = '; '.join(ris[risfield])
                    POST[field] = xlate(replacement)
            def space_comments(names):
                # RIS doesn't put spaces after commas in names
                return re.sub(',(?=[^ ])', ', ', names)

            update('title', 'TI') # first try TI, then T1
            update('title', 'T1')
            update('source_title', 'JO') # first try JO, then JF
            update('source_title', 'JF')
            update('author', 'A1', space_comments)
            update('url', 'UR')
            update('volume', 'VL')
            update('issue', 'IS')
            if 'SP' in ris and 'EP' in ris:
                POST['pages'] = ris['SP'][0] + '-' + ris['EP'][0]
            update('published', 'PY', lambda v: v.split('/')[0])


        if item_type == 'HEADING':
            title = clean('title')
            if not title:
                # fixme, better error handling.
                return HttpResponseRedirect(request.get_full_path())
            else:
                item = models.Item(
                    site=site,
                    item_type='HEADING',
                    parent_heading=parent_item,
                    title=title,
                    )
                item.save()
        elif item_type == 'URL':
            title = clean('title')
            url = clean('url')
            author = clean('author')
            publisher = clean('publisher')
            published = clean('published')
            if not (title and url):
                raise Exception(locals())
                # fixme, better error handling.
                return HttpResponseRedirect(request.get_full_path())
            else:
                item = models.Item(
                    site=site,
                    item_type='URL',
                    parent_heading=parent_item,
                    title=title,
                    url = url,
                    author = author,
                    publisher = publisher,
                    published = published,
                    source_title=clean('source_title'),
                    volume=clean('volume'),
                    issue=clean('issue'),
                    pages=clean('pages'),
                    isbn=clean('isbn'),
                    )
                item.save()
        elif item_type == 'ELEC':
            title = clean('title')
            upload = request.FILES.get('file')
            if not (title and upload):
                # fixme, better error handling.
                return HttpResponseRedirect(request.get_full_path())

            data = dict((k.encode('ascii'), v.strip()) for k, v in POST.items())
            if data['author2']:
                data['author'] = '%s; %s' % (data['author1'], data['author2'])
            else:
                data['author'] = data['author1']
            del data['author1']; del data['author2']

            item = models.Item(
                site=site,
                item_type='ELEC',
                parent_heading=parent_item,
                fileobj_mimetype = upload.content_type,
                **data)
            item.fileobj.save(upload.name, upload)
            item.save()
        else:
            raise NotImplementedError

        return HttpResponseRedirect(item.parent_url())

@instructors_only
def item_add_cat_search(request, site_id, item_id):
    # this chunk stolen from item_add(). Refactor.
    parent_item_id = item_id
    if parent_item_id=='0':
        parent_item = None
        site = get_object_or_404(models.Site, pk=site_id)
        siblings = site.item_set.filter(parent_heading=None)
    else:
        parent_item = get_object_or_404(models.Item, pk=parent_item_id, site__id=site_id)
        assert parent_item.item_type == 'HEADING', _('You can only add items to headings!')
        site = parent_item.site
        siblings = site.item_set.filter(parent_heading=parent_item)

    #----------

    if request.method != 'POST':
        if not 'query' in request.GET:
            return g.render('item/item_add_cat_search.xhtml', results=[], query='', 
                            site=site, parent_item=parent_item)
        query = request.GET.get('query','').strip()
        start, limit = (int(request.GET.get(k,v)) for k,v in (('start',1),('limit',10)))
        results, numhits = integration.cat_search(query, start, limit)
        return g.render('item/item_add_cat_search.xhtml', 
                        results=results, query=query, 
                        start=start, limit=limit, numhits=numhits,
                        site=site, parent_item=parent_item)
    else:
        # User has selected an item; add it to site.
        raw_pickitem = request.POST.get('pickitem', '').strip()
        #fixme, this block copied from item_add. refactor.
        parent_item_id = item_id
        if parent_item_id == '0': 
            # no heading (toplevel)
            parent_item = None
            site = get_object_or_404(models.Site, pk=site_id)
        else:
            parent_item = get_object_or_404(models.Item, pk=parent_item_id, site__id=site_id)
            assert parent_item.item_type == 'HEADING', _('You can only add items to headings!')
            site = parent_item.site
        if not site.can_edit(request.user):
            return _access_denied(_('You are not an editor.'))

        if gethook('get_better_copy_of_marc'):
            pickitem_xml = callhook('get_better_copy_of_marc', raw_pickitem)
            raw_pickitem = unicode(ET.tostring(pickitem_xml))
            pickitem = marcxml_to_dictionary(pickitem_xml)
        else:
            pickitem = marcxml_to_dictionary(raw_pickitem)
        dublin = marcxml_dictionary_to_dc(pickitem)
        assert dublin

        #TODO: this data munging does not belong here. 

        # one last thing. If this picked item has an 856$9 field, then
        # it's an electronic resource, not a physical item. In that
        # case, we add it as a URL, not a PHYS.
        url = callhook('marcxml_to_url', raw_pickitem)
        if url:
            dct = dict(item_type='URL', url=url)
        else:
            dct = dict(item_type='PHYS')
        
        try:
            pubdate = dublin.get('dc:date')
            m = re.search('([0-9]+)', pubdate)
            if m:
                pubdate = pubdate.group(1)
        except:
            pubdate = ''

        item = site.item_set.create(parent_heading=parent_item,
                                    title=dublin.get('dc:title','Untitled'),
                                    author=dublin.get('dc:creator'),
                                    publisher=dublin.get('dc:publisher',''),
                                    published=pubdate,
                                    marcxml=raw_pickitem,
                                    **dct)
        item.save()

        return HttpResponseRedirect(item.parent_url())

#------------------------------------------------------------

@instructors_only
def item_edit(request, site_id, item_id):
    site = get_object_or_404(models.Site, pk=site_id)
    item = get_object_or_404(models.Item, pk=item_id, site__id=site_id)
    item_type = item.item_type
    template = 'item/item_add_%s.xhtml' % item_type.lower()
    parent_item = item.parent_heading

    if request.method != 'POST':
        return g.render(template, **locals())
    else:
        if 'file' in request.FILES:
            # this is a 'replace-current-file' action.
            upload = request.FILES.get('file')
            item.fileobj.save(upload.name, upload)
            item.fileobj_mimetype = upload.content_type
        elif 'file' in request.POST:
            # an error: edit again...
            return HttpResponseRedirect(item.item_url('edit'))
        else:
            # generally update the item.
            data = dict((k.encode('ascii'), v.strip()) for k, v in request.POST.items())
            if data['author2']:
                data['author'] = '%s; %s' % (data['author1'], data['author2'])
            else:
                data['author'] = data['author1']
            del data['author1']; del data['author2']
            [setattr(item, k, v) for (k,v) in data.items()]
                    
        item.save()
        return HttpResponseRedirect(item.parent_url())
        
@instructors_only
def item_delete(request, site_id, item_id):
    site = get_object_or_404(models.Site, pk=site_id)
    item = get_object_or_404(models.Item, pk=item_id, site__id=site_id)
    if request.method != 'POST':
        return g.render('item/item_delete_confirm.xhtml', **locals())
    else:
        if 'yes' in request.POST:
            # I think Django's ON DELETE CASCADE-like behaviour will
            # take care of the sub-items.
            redir = item.parent_url('meta')
            item.delete()
            return HttpResponseRedirect(redir)
        else:
            return HttpResponseRedirect('../meta')
    
@members_only
def item_download(request, site_id, item_id, filename):
    site = get_object_or_404(models.Site, pk=site_id)
    item = get_object_or_404(models.Item, pk=item_id, site__id=site_id)
    assert item.item_type == 'ELEC', _('Can only download ELEC documents!')

    # don't allow download of items that need a declaration.
    item_declaration_required = item.needs_declaration_from(request.user)
    if item_declaration_required:
        return HttpResponseRedirect(item.item_url())

    # don't allow download of items that are not copyright-cleared.
    if not (item.copyright_status_ok() or site.can_edit(request.user)):
        return HttpResponseRedirect(item.item_url())

    fileiter = item.fileobj.chunks()
    resp = HttpResponse(fileiter)
    resp['Content-Type'] = item.fileobj_mimetype or 'application/octet-stream'
    #resp['Content-Disposition'] = 'attachment; filename=%s' % name
    return resp
    


#------------------------------------------------------------
# resequencing items

def _reseq(request, site, parent_heading):
    new_order = request.POST['new_order'].strip().split(' ')
    # new_order is now a list like this: ['item_3', 'item_8', 'item_1', ...].
    # get at the ints.
    new_order = [int(n.split('_')[1]) for n in new_order]
    print >> sys.stderr, new_order
    # TODO .orderBy, now there is no sort_order.
    the_items = list(site.item_set.filter(parent_heading=parent_heading))
    # sort the items by position in new_order
    the_items.sort(key=lambda item: new_order.index(item.id))
    for newnum, item in enumerate(the_items):
        item.sort_order = newnum
        item.save()
    return HttpResponse("'ok'");

@instructors_only
def site_reseq(request, site_id):
    site = get_object_or_404(models.Site, pk=site_id)
    parent_heading = None
    return _reseq(request, site, parent_heading)

@instructors_only
def item_heading_reseq(request, site_id, item_id):
    site = get_object_or_404(models.Site, pk=site_id)
    item = get_object_or_404(models.Item, pk=item_id, site__id=site_id)
    parent_heading = item
    return _reseq(request, site, parent_heading)


@instructors_only
def item_relocate(request, site_id, item_id):
    """Move an item from its current subheading to another one."""
    site = get_object_or_404(models.Site, pk=site_id)
    item = get_object_or_404(models.Item, pk=item_id, site__id=site_id)
    if request.method != 'POST':
        return g.render('item/item_relocate.xhtml', **locals())
    else:
        newheading = int(request.POST['heading'])
        if newheading == 0:
            new_parent = None
        else:
            new_parent = site.item_set.get(pk=newheading)
            if item in new_parent.hierarchy():
                # then we would create a cycle. Bail out.
                return simple_message(_('Impossible item-move!'), 
                                      _('You cannot make an item a descendant of itself!'))
        item.parent_heading = new_parent
        item.save()
        if new_parent:
            return HttpResponseRedirect(new_parent.item_url('meta'))
        else:
            return HttpResponseRedirect(site.site_url())
