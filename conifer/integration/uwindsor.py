# See conifer/syrup/integration.py for documentation.

from datetime import date
from django.conf import settings
from conifer.libsystems.evergreen.support import initialize, E1
from conifer.libsystems import marcxml as M
from conifer.libsystems.evergreen import item_status as I
from conifer.libsystems.z3950 import pyz3950_search as PZ
from xml.etree import ElementTree as ET
import re
import uwindsor_campus_info

def department_course_catalogue():
    """
    Return a list of rows representing all known, active courses and
    the departments to which they belong. Each row should be a tuple
    in the form: ('Department name', 'course-code', 'Course name').
    """
    return [
        ('Arts','01-01-209','Ethics in the Professions'),
        ('Social Work','02-47-204','Issues & Perspectives in Social Welfare'),
        ('Social Work','02-47-211','Prof Comm in Gen. Social Work Practice'),
        ('Social Work','02-47-336','Theory and Practice Social Work I'),
        ('Social Work','02-47-361','Field Practice I - A'),
        ('Social Work','02-47-362','Field Practice I - B'),
        ('Social Work','02-47-370','Mothering and Motherhood'),
        ('Social Work','02-47-456','Social Work and Health'),
        ]

def term_catalogue():
    """
    Return a list of rows representing all known terms. Each row
    should be a tuple in the form: ('term-code', 'term-name',
    'start-date', 'end-date'), where the dates are instances of the
    datetime.date class.
    """
    return [
        ('2011S', '2011 Summer', date(2011,5,1), date(2011,9,1)),
        ('2011F', '2011 Fall', date(2011,9,1), date(2011,12,31)),
        ]


#--------------------------------------------------
# ILS integration

EG_BASE = 'http://%s/' % settings.EVERGREEN_GATEWAY_SERVER
initialize(EG_BASE)


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
    if item.bib_id and item.bib_id[-1] in '02468':
        return (8, 4, 2)
    else:
        return (2, 0, 0)


def cat_search(query, start=1, limit=10):
    if query.startswith(EG_BASE):
        # query is an Evergreen URL
        results = M.marcxml_to_records(I.url_to_marcxml(query))
        numhits = len(results)
    else:
        # query is an actual Z39.50 query
        cat_host, cat_port, cat_db = settings.Z3950_CONFIG
        results, numhits = PZ.search(cat_host, cat_port, cat_db, query, start, limit)
    return results, numhits

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
    if bib_id:
        return ('http://windsor.concat.ca/opac/en-US'
                '/skin/default/xml/rdetail.xml?r=%s&l=1&d=0' % bib_id)

def get_better_copy_of_marc(marc_string):
    """
    This function takes a MARCXML record and returns either the same
    record, or another instance of the same record from a different
    source. 

    This is a hack. There is currently at least one Z39.50 server that
    returns a MARCXML record with broken character encoding. This
    function declares a point at which we can work around that server.
    """
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

def decode_role(role):
    if role == 'Instructor':
        return 'INSTR'
    else:
        return 'STUDT'

def external_memberships(userid, include_titles=False):
    memberships = uwindsor_campus_info.call('membership_ids', userid)
    for m in memberships:
        m['role'] = decode_role(m['role'])
    return memberships
