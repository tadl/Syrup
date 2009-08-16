from _common import *
from django.utils.translation import ugettext as _
from search import *
from lxml import etree
import libxml2
import libxslt
import os


BASE_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
HERE = lambda s: os.path.join(BASE_DIRECTORY, s)


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

def instructor_search(request, instructor):
    return search(request, with_instructor=instructor)

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
    styledoc = libxml2.parseFile('/conifer/syrupsvn/trunk/conifer/static/xslt/test.xsl')
    styledoc = libxml2.parseFile(HERE('../../static/xslt/test.xsl'))
    test = libxslt.parseStylesheetDoc(styledoc)
    #return g.render('z3950_test.xhtml', res_str="")

    #testing JZKitZ3950 - it seems to work, but i have a character set problem
    #with the returned marc
    #nope - the problem is weak mapping with the limited solr test set
    #i think this can be sorted out

    #conn = zoom.Connection ('z3950.loc.gov', 7090)
    #conn = zoom.Connection ('webvoy.uwindsor.ca', 9000)
    #solr index with JZKitZ3950 wrapping
    conn = zoom.Connection ('zed.concat.ca', 210)
    # conn = zoom.Connection ('127.0.0.1', 2100)
    print("connecting...")
    conn.databaseName = 'OWA'
    conn.preferredRecordSyntax = 'XML'
    # conn.preferredRecordSyntax = 'USMARC'
    query = zoom.Query ('CCL', 'ti="agar"')
    res = conn.search (query)
    collector = []
    # if we wanted to get into funkiness
    m = zmarc.MARC8_to_Unicode ()
    for r in res:
        print(type(r.data))
        print(type(m.translate(r.data)))
        #rec = zmarc.MARC (r.data, strict=0)
        # rec = zmarc.MARC (rec, strict=0)
        #collector.append(str(rec))
	#collector.append((m.translate(r.data)))
	# print("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
	zhit = str("<?xml version=\"1.0\"?>") + (m.translate(r.data))
	#zhit = m.translate(r.data)
	#doc = etree.fromstring(zhit)
	#doc = libxml2.xmlNode(zhit)
	doc = libxml2.parseDoc(zhit)
	#print(str("<?xml version=\"1.0\" encoding=\"UTF-8\"?>") + (m.translate(r.data)))
	#print(zhit)
	print(test.applyStylesheet(doc, None))

    conn.close ()
    res_str = "" . join(collector)
    return g.render('z3950_test.xhtml', res_str=res_str)

def browse(request, browse_option=''):
    #the defaults should be moved into a config file or something...
    page_num = int(request.GET.get('page', 1))
    count    = int(request.GET.get('count', 5))

    if browse_option == '':
        queryset = None
        template = 'browse_index.xhtml'
    elif browse_option == 'instructors':
        queryset = models.User.active_instructors()
        queryset = queryset.filter(user_filters(request.user)['instructors'])
        template = 'instructors.xhtml'
    elif browse_option == 'departments':
        queryset = models.Department.objects.filter(active=True)
        template = 'departments.xhtml'
    elif browse_option == 'courses':
        # fixme, course filter should not be (active=True) but based on user identity.
        for_courses = user_filters(request.user)['courses']
        queryset = models.Course.objects.filter(for_courses)
        template = 'courses.xhtml'

    queryset = queryset and queryset.distinct()
    paginator = Paginator(queryset, count)
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
    filters = user_filters(request.user)
    courses = courses.filter(filters['courses'])
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

