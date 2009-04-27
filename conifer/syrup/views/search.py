from _common import *
from django.utils.translation import ugettext as _

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

        # Next, we filter based on user permissions.
        flt = user_filters(request.user)
        user_filter_for_items, user_filter_for_courses = flt['items'], flt['courses'] 
        # Note, we haven't user-filtered anything yet; we've just set
        # up the filters.

        # numeric search: If the query-string is a single number, then
        # we do a short-number search, or a barcode search.

        if re.match(r'\d+', query_string):
            # Search by short ID.
            results_list = models.Item.with_smallint(query_string)
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
            # For an in-course search, we know the user has
            # permissions to view the course; no need for
            # user_filter_for_items.
            results_list = results_list.filter(course=in_course)
        else:
            results_list = results_list.filter(user_filter_for_items)

        results_list = results_list.distinct().order_by('title')
        results_len = len(results_list)
        paginator = Paginator(results_list, count)

        #course search
        if in_course:
            # then no course search is necessary.
            course_list = []; course_len = 0
        else:
            course_query = get_query(query_string, ['title', 'department__name'])
            # apply the search-filter and the user-filter
            course_results = models.Course.objects.filter(course_query).filter(user_filter_for_courses)
            course_list = course_results.order_by('title')
            course_len = len(course_results)

        #instructor search
        if in_course:
            instructor_list = []; instr_len = 0
        else:
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


