from _common import *
from PyZ3950 import zoom, zmarc


# ENABLE_USER_FILTERS: if True, then search results will not contain
# anything that the logged-in user would not be permitted to view. For
# example, if the user is not logged in, only "anonymous" site
# contents would be included in any search results.

ENABLE_USER_FILTERS = True


#----------------------------------------------------------------------
# Some combinators for building up Q() queries

def OR(clauses_list):
    return reduce(lambda a, b: a | b, clauses_list, Q())

def AND(clauses_list):
    return reduce(lambda a, b: a & b, clauses_list, Q())


#----------------------------------------------------------------------

def normalize_query(query_string,
                    findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                    normspace=re.compile(r'\s{2,}').sub):
    ''' Splits the query string in invidual keywords, getting rid of
        unecessary spaces and grouping quoted words together.
        Example:

        >>> normalize_query(
             '  some random  words "with   quotes  " and   spaces')
        ['some', 'random', 'words', 'with quotes', 'and', 'spaces']

    '''
    norm = [normspace(' ', (t[0] or t[1]).strip())
            for t in findterms(query_string)]
    return norm



def build_query(query_string, search_fields):
    """
    Returns a Q() query filter for searching for keywords within a
    model by testing the given search fields.

    For example, the query "foot wash" with search_fields ['title',
    'author'] will return a Q() object representing the filter:

    (AND: (OR: ('title__icontains', u'foot'),
               ('author__icontains', u'foot')),
          (OR: ('title__icontains', u'wash'),
               ('author__icontains', u'wash')))
    """

    def clause(field_name, expression):
        return Q(**{"%s__icontains" % field_name: expression})

    terms   = normalize_query(query_string)

    clauses = [ [ clause(field_name, term) for field_name in search_fields ]
                for term in terms ]

    query   = AND([OR(inner) for inner in clauses])

    return query



def _search(query_string, for_site=None, for_owner=None, user=None):
    """
    Given a query_string, return two lists (Items and Sites) of
    results that match the query. For_site, for_owner and user may be
    used to limit the results to a given site, a given site owner, or
    based on a given user's permissions (but see ENABLE_USER_FILTERS).
    """

    #--------------------------------------------------
    # ITEMS

    # Build up four clauses: one based on search terms, one based on
    # the current user's permissions, one based on site-owner
    # restrictions, and one based on site restrictions. Then we join
    # them all up.

    term_filter = build_query(query_string, ['title', 'author',
                                             'publisher', 'marcxml'])
    if ENABLE_USER_FILTERS and user:
        user_filter = models.Item.filter_for_user(user)
    else:
        user_filter = Q()

    owner_filter = Q(site__owner=for_owner) if for_owner else Q()
    site_filter  = Q(site=for_site)         if for_site  else Q()

    _items       = models.Item.objects.select_related()
    print (term_filter & user_filter &
                                 site_filter & owner_filter)
    items        = _items.filter(term_filter & user_filter &
                                 site_filter & owner_filter)

    #--------------------------------------------------
    # SITES

    if for_site:
        # if we're searching within a site, we don't want to return
        # any sites as results.
        sites = models.Site.objects.none()
    else:
        term_filter = build_query(query_string, ['course__name',
                                                 'course__department__name',
                                                 'owner__last_name',
                                                 'owner__first_name'])
        if ENABLE_USER_FILTERS and user:
            user_filter  = models.Site.filter_for_user(user)
        else:
            user_filter = Q()

        owner_filter = Q(owner=for_owner) if for_owner else Q()

        _sites       = models.Site.objects.select_related()
        sites        = _sites.filter(term_filter & user_filter &
                                     owner_filter)

    #--------------------------------------------------

    results = (list(items), list(sites))
    return results



#-----------------------------------------------------------------------------

def search(request, in_site=None, for_owner=None):
    ''' Search within the reserves system. If in_site is provided,
        then limit search to the contents of the specified site.  If
        for_owner is provided, then limit search to sites owned by
        this instructor.
    '''

    print("in_site is %s" % in_site)
    print("for_owner is %s" % for_owner)

    query_string = request.GET.get('q', '').strip()

    if not query_string:        # empty query?
        if in_site:
            return HttpResponseRedirect(reverse('site_detail', in_site))
        else:
            return HttpResponseRedirect(reverse('browse'))
    else:
        _items, _sites = _search(query_string, in_site, for_owner, request.user)
        results        = _sites + _items
        page_num       = int(request.GET.get('page', 1))
        count          = int(request.GET.get('count', 5))
        paginator      = Paginator(results, count)
        norm_query     = normalize_query(query_string)

        return g.render('search_results.xhtml', **locals())







#-----------------------------------------------------------------------------
# Z39.50 support (for testing)

def zsearch(request):
    '''
    '''

    page_num = int(request.GET.get('page', 1))
    count = int(request.POST.get('count', 5))

    if request.GET.get('page')==None and request.method == 'GET':
        targets_list = models.Z3950Target.objects.filter(active=True) \
            .order_by('name')
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
        search_target= models.Z3950Target.objects.get(name=target)
        conn = zoom.Connection (search_target.host, search_target.port)
        conn.databaseName = search_target.database
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
                collector.insert (idx,(None, 'Unsupported syntax: ' + r.syntax,
                                       None))
            else:
                raw = r.data

                # Convert to MARC
                marcdata = zmarc.MARC(raw, strict=False)
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
                # collector.insert(idx,(bibid, unicode(title,'ascii','ignore')))
                collector.insert(idx,(bibid, unicode(title, 'utf-8', 'ignore')))
            idx+=1

        conn.close ()
        paginator = Paginator(collector, count)

    print("returning...")
    #return g.render('zsearch_results.xhtml', **locals())
    return g.render('zsearch_results.xhtml', paginator=paginator,
                    page_num=page_num,
                    count=count, target=target, tquery=tquery)
