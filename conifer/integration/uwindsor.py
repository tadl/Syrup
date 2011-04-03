# See conifer/syrup/integration.py for documentation.

from conifer.libsystems import ezproxy
from conifer.libsystems import marcxml as M
from conifer.libsystems.evergreen import item_status as I
from conifer.libsystems.evergreen.support import initialize, E1
from conifer.libsystems.z3950 import pyz3950_search as PZ
from datetime import date
from django.conf import settings
from memoization import memoize
from xml.etree import ElementTree as ET
import csv
import datetime
import time
import os
import re
import traceback
import subprocess
import uwindsor_campus_info
import uwindsor_fuzzy_lookup

# USE_Z3950: if True, use Z39.50 for catalogue search; if False, use OpenSRF.
# Don't set this value directly here: rather, if there is a valid Z3950_CONFIG
# settings in local_settings.py, then Z39.50 will be used.
USE_Z3950 = getattr(settings, 'Z3950_CONFIG', None) is not None

def department_course_catalogue():
    """
    Return a list of rows representing all known, active courses and
    the departments to which they belong. Each row should be a tuple
    in the form: ('Department name', 'course-code', 'Course name').
    """
    url = 'http://cleo.uwindsor.ca/graham/courses.txt.gz'
    p = subprocess.Popen('curl -s %s | gunzip -c' % url, 
                         shell=True, stdout=subprocess.PIPE)
    reader = csv.reader(p.stdout)
    catalogue = list(reader)
    p.stdout.close()
    return catalogue

def term_catalogue():
    """
    Return a list of rows representing all known terms. Each row
    should be a tuple in the form: ('term-code', 'term-name',
    'start-date', 'end-date'), where the dates are instances of the
    datetime.date class.
    """
    # TODO: make this algorithmic.
    return [
        ('2011S', '2011 Summer', date(2011,5,1), date(2011,9,1)),
        ('2011F', '2011 Fall', date(2011,9,1), date(2011,12,31)),
        ]


#--------------------------------------------------
# ILS integration

EG_BASE = 'http://%s/' % settings.EVERGREEN_GATEWAY_SERVER
initialize(EG_BASE)


# Item status stuff

STATUS_DECODE = [(str(x['id']), x['name']) 
                 for x in E1('open-ils.search.config.copy_status.retrieve.all')]
AVAILABLE = [id for id, name in STATUS_DECODE if name == 'Available'][0]
RESHELVING = [id for id, name in STATUS_DECODE if name == 'Reshelving'][0]

def item_status(item):
    """
    Given an Item object, return three numbers: (library, desk,
    avail). Library is the total number of copies in the library
    system; Desk is the number of copies at the designated reserves
    desk; and Avail is the number of copies available for checkout at
    the given moment. Note that 'library' includes 'desk' which
    includes 'avail'. You may also return None if the item is
    nonsensical (e.g. it is not a physical object, or it has no bib
    ID).
    
    Note, 'item.bib_id' is the item's bib_id, or None;
    'item.item_type' will equal 'PHYS' for physical items;
    'item.site.service_desk' is the ServiceDesk object associated with
    the item. The ServiceDesk object has an 'external_id' attribute
    which should represent the desk in the ILS.
    """
    return _item_status(item.bib_id)

CACHE_TIME = 300

@memoize(timeout=CACHE_TIME)
def _item_status(bib_id):
    """
	At this point, status information does not require the opensrf 
	bindings, I am not sure there is a use case where an evergreen
	site would not have access to these but will leave for now
	since there are no hardcoded references
    """
            
    if bib_id:
        try:
            counts = E1(settings.OPENSRF_COPY_COUNTS, bib_id, 1, 0)

            lib = desk = avail = vol = 0
	    dueinfo = ''
            callno = ''
            circmod = ''
            alldues = []

            for org, callnum, loc, stats in counts:
		callprefix = ''
		callsuffix = ''
		if len(callno) == 0:
			callno = callnum
                avail_here = stats.get(AVAILABLE, 0)
                avail_here += stats.get(RESHELVING, 0)
                anystatus_here = sum(stats.values())

		"""
		volume check - based on v.1, etc. in call number
		"""
    		voltest = re.search(r'\w*v\.\s?(\d+)', callnum)

		"""
		attachment test 
		"""
		attachtest = re.search(settings.ATTACHMENT, callnum)

                if loc == settings.RESERVES_DESK_NAME:
		    desk += anystatus_here
                    avail += avail_here
		    dueinfo = ''
                    		
                    if (voltest and vol > 0 ): 
			if (int(voltest.group(1)) > vol):
				callsuffix = "/" + callnum
			else:
				callprefix = callnum + "/" 
                    elif attachtest and callno.find(attachtest.group(0)) == -1:
			if len(callno) > 0:
				callsuffix = "/" + callnum
			else:
				callprefix = callnum
                    else:
			callno = callnum
                
                    lib += anystatus_here
                    copyids = E1(settings.OPENSRF_CN_CALL, bib_id, callnum, org)
		
                    """
                    we want to return the resource that will be returned first if
                    already checked out
                    """
                    for copyid in copyids:
			circinfo = E1(settings.OPENSRF_FLESHED2_CALL, copyid)

			thisloc = circinfo.get("location")
			if thisloc:
				thisloc = thisloc.get("name")
		
			if thisloc == settings.RESERVES_DESK_NAME: 
				bringfw = attachtest

				# multiple volumes
				if voltest and callno.find(voltest.group(0)) == -1:
					bringfw = True
	
				if len(circmod) == 0:
					circmod = circinfo.get("circ_modifier")
				circs = circinfo.get("circulations")

				if circs and isinstance(circs, list):
					circ = circs[0]
					rawdate = circ.get("due_date")
					#remove offset info, %z is flakey for some reason
					rawdate = rawdate[:-5]
					duetime = time.strptime(rawdate, settings.TIME_FORMAT)

				if avail == 0 or bringfw:
					if circs and len(circs) > 0:
						if len(dueinfo) == 0 or bringfw: 
							earliestdue = duetime
							if voltest:
								if (int(voltest.group(1)) > vol):
									if len(dueinfo) > 0:
										dueinfo = dueinfo + "/"
									dueinfo = dueinfo + voltest.group(0) + ': ' + time.strftime(settings.DUE_FORMAT,earliestdue)
								else:
									tmpinfo = dueinfo
									dueinfo = voltest.group(0) + ': ' + time.strftime(settings.DUE_FORMAT,earliestdue) 
									if len(tmpinfo) > 0:
										dueinfo = dueinfo + "/" + tmpinfo
								callprefix = callsuffix = ''
							elif attachtest:
								tmpinfo = dueinfo
								dueinfo = attachtest.group(0) + ': ' + time.strftime(settings.DUE_FORMAT,earliestdue)
								if len(callno) > 0:
									callno = callno + '/' + callnum 
									callprefix = callsuffix = ''
								else:
									callno = callnum
								if len(tmpinfo) > 0:
									dueinfo = dueinfo + "/" + tmpinfo
								
							if not bringfw:
								dueinfo = time.strftime(settings.DUE_FORMAT,earliestdue)
								callno = callnum

						# way too wacky to sort out vols for this
						if duetime < earliestdue and not bringfw:
							earliestdue = duetime
							dueinfo = time.strftime(settings.DUE_FORMAT,earliestdue)
							callno = callnum

				alldisplay = callnum + ' (Available)'
					
				if circs and isinstance(circs, list):
					alldisplay = '%s (DUE: %s)' % (callnum, time.strftime(settings.DUE_FORMAT,duetime))

				alldues.append(alldisplay)
			
			if voltest or attachtest:
				if callno.find(callprefix) == -1:
					callno = callprefix + callno 
				if callno.find(callsuffix) == -1:
					callno = callno + callsuffix
			if voltest:
				vol = int(voltest.group(1))
            return (lib, desk, avail, callno, dueinfo, circmod, alldues)
	except:
	    print "due date/call problem: ", bib_id
            print "*** print_exc:"
            traceback.print_exc()
            pass          # fail silently in production if there's an opensrf or time related error.
    return None

CAT_SEARCH_ORG_UNIT = 106

def cat_search(query, start=1, limit=10):
    barcode = 0
    bibid   = 0
    is_barcode = re.search('\d{14}', query)

    if query.startswith(EG_BASE):
        # query is an Evergreen URL
	# snag the bibid at this point
    	params = dict([x.split("=") for x in query.split("&")])
    	for key in params.keys():
		if key.find('?r') != -1:
			bibid = params[key]
        results = M.marcxml_to_records(I.url_to_marcxml(query))
        numhits = len(results)
    elif is_barcode:
	results = []
	numhits = 0
	barcode = query.strip()
        bib = E1('open-ils.search.bib_id.by_barcode', barcode)
	if bib:
		bibid = bib
		copy = E1('open-ils.supercat.record.object.retrieve', bib)
		marc = copy[0]['marc']
                # In some institutions' installations, 'marc' is a string; in
                # others it's unicode. Convert to unicode if necessary.
                if not isinstance(marc, unicode):
                    marc = unicode(marc, 'utf-8')
                tree = M.marcxml_to_records(marc)[0]
                results.append(tree)
		numhits = 1
    else:
        # query is an actual query
        if USE_Z3950:
            cat_host, cat_port, cat_db = settings.Z3950_CONFIG
            results, numhits = PZ.search(cat_host, cat_port, cat_db, query, start, limit)
        else:                   # use opensrf
            superpage = E1('open-ils.search.biblio.multiclass.query',
                           {'org_unit': CAT_SEARCH_ORG_UNIT,
                            'depth': 1, 'limit': limit, 'offset': start-1,
                            'visibility_limit': 3000,
                            'default_class': 'keyword'},
                           query, 1)
            ids = [id for (id,) in superpage['ids']]
            results = []
            for rec in E1('open-ils.supercat.record.object.retrieve', ids):
                marc = rec['marc']
                # In some institutions' installations, 'marc' is a string; in
                # others it's unicode. Convert to unicode if necessary.
                if not isinstance(marc, unicode):
                    marc = unicode(marc, 'utf-8')
                tree = M.marcxml_to_records(marc)[0]
                results.append(tree)
            numhits = int(superpage['count'])
    return results, numhits, bibid, barcode

def bib_id_to_marcxml(bib_id):
    """
    Given a bib_id, return a MARC record in MARCXML format. Return
    None if the bib_id does not exist.
    """
    try:
        xml = I.bib_id_to_marcxml(bib_id)
        return ET.fromstring(xml)
    except:
        return None

def marc_to_bib_id(marc_string):
    """
    Given a MARC record, return either a bib ID or None, if no bib ID can be
    found.
    """
    dct = M.marcxml_to_dictionary(marc_string)
    bib_id = dct.get('901c')
    return bib_id

def bib_id_to_url(bib_id):
    """
    Given a bib ID, return either a URL for examining the bib record, or None.
    """
    # TODO: move this to local_settings
    if bib_id:
        return ('%sopac/en-CA'
                '/skin/uwin/xml/rdetail.xml?r=%s&l=1&d=0' % (EG_BASE, bib_id))

if USE_Z3950:
    # only if we are using Z39.50 for catalogue search. Against our Conifer
    # Z39.50 server, results including accented characters are often seriously
    # messed up. (Try searching for "montreal").
    def get_better_copy_of_marc(marc_string):
        """
        This function takes a MARCXML record and returns either the same
        record, or another instance of the same record from a different
        source. 

        This is a hack. There is currently at least one Z39.50 server that
        returns a MARCXML record with broken character encoding. This
        function declares a point at which we can work around that server.
        """

        print marc_string
        bib_id = marc_to_bib_id(marc_string)
        better = bib_id_to_marcxml(bib_id)
        # don't return the "better" record if there's no 901c in it...
        if better and ('901c' in M.marcxml_to_dictionary(better)):
            return better
        return ET.fromstring(marc_string)

def marcxml_to_url(marc_string):
    """
    Given a MARC record, return either a URL (representing the
    electronic resource) or None.

    Typically this will be the 856$u value; but in Conifer, 856$9 and
    856$u form an associative array, where $9 holds the institution
    codes and $u holds the URLs.
    """
    # TODO: move this to local_settings
    LIBCODE = 'OWA'             # Leddy
    try:
        dct   = M.marcxml_to_dictionary(marc_string)
        words = lambda string: re.findall(r'\S+', string)
        keys  = words(dct.get('8569'))
        urls  = words(dct.get('856u'))
        print 'KEYS:', keys
        print 'URLS:', urls
        return urls[keys.index(LIBCODE)]
    except:
        return None

    
def external_person_lookup(userid):
    """
    Given a userid, return either None (if the user cannot be found),
    or a dictionary representing the user. The dictionary must contain
    the keys ('given_name', 'surname') and should contain 'email' if
    an email address is known, and 'patron_id' if a library-system ID
    is known.
    """
    return uwindsor_campus_info.call('person_lookup', userid)


def external_memberships(userid):
    """
    Given a userid, return a list of dicts, representing the user's
    memberships in known external groups. Each dict must include the
    following key/value pairs:
    'group': a group-code, externally defined;
    'role':  the user's role in that group, one of (INSTR, ASSIST, STUDT).
    """
    memberships = uwindsor_campus_info.call('membership_ids', userid)
    for m in memberships:
        m['role'] = decode_role(m['role'])
    return memberships

def decode_role(role):
    if role == 'Instructor':
        return 'INSTR'
    else:
        return 'STUDT'

def fuzzy_person_lookup(query, include_students=False):
    """
    Given a query, return a list of users who probably match the
    query. The result is a list of (userid, display), where userid
    is the campus userid of the person, and display is a string
    suitable for display in a results-list. Include_students
    indicates that students, and not just faculty/staff, should be
    included in the results.
    """
    # Note, our 'include_students' option only matches students on exact
    # userids. That is, fuzzy matching only works for staff, faculty, and
    # other non-student roles.

    filter  = uwindsor_fuzzy_lookup.build_filter(query, include_students)
    results = uwindsor_fuzzy_lookup.search(filter)

    out = []
    for res in results:
        if not 'employeeType' in res:
            res['employeeType'] = 'Student' # a 99% truth!
        display = ('%(givenName)s %(sn)s. %(employeeType)s, '
                   '%(uwinDepartment)s. <%(mail)s>. [%(uid)s]') % res
        out.append((res['uid'], display))
    return out


def derive_group_code_from_section(site, section):
    """
    This function is used to simplify common-case permission setting
    on course sites. It takes a site and a section number/code, and
    returns the most likely external group code. (This function will
    probably check the site's term and course codes, and merge those
    with the section code, to derive the group code.) Return None if a
    valid, unambiguous group code cannot be generated.
    """
    try:
        section = int(section)
    except:
        return None

    return '%s-%s-%s' % (site.course.code.replace('-', ''),
                         section, 
                         site.start_term.code)
                         
#--------------------------------------------------
# proxy server integration

ezproxy_service = ezproxy.EZProxyService(
    settings.UWINDSOR_EZPROXY_HOST,
    settings.UWINDSOR_EZPROXY_PASSWORD)

def proxify_url(url):
    """
    Given a URL, determine whether the URL needs to be passed through
    a reverse-proxy, and if so, return a modified URL that includes
    the proxy. If not, return None.
    """
    return ezproxy_service.proxify(url)


def download_declaration():
    """
    Returns a string. The declaration to which students must agree when
    downloading electronic documents. If not customized, a generic message
    will be used.
    """
    # as per Joan Dalton, 2010-12-21.
    # TODO: move this to local_settings
    return ("I warrant that I am a student of the University of Windsor "
            "enrolled in a course of instruction. By pressing the "
            "'Request' button below, I am requesting a digital copy of a "
            "reserve reading for research, private study, review or criticism "
            "and that I will not use the copy for any other purpose, nor "
            "will I transmit the copy to any third party.")
