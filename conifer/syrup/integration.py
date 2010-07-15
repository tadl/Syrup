# this is a placeholder module, for the definitions in the
# INTEGRATION_MODULE defined in local_settings.py. 

# Please do not define anything in this file. It will be automatically
# populated once confier.syrup.models has been evaluated.

def disable(func):
    return None


@disable
def can_create_sites(user):
    """
    Return True if this User object represents a person who should be
    allowed to create new course-reserve sites. Note that users marked
    as 'staff' are always allowed to create new sites.
    """
    pass


@disable
def department_course_catalogue():
    """
    Return a list of rows representing all known, active courses and
    the departments to which they belong. Each row should be a tuple
    in the form: ('Department name', 'course-code', 'Course name').
    """
    pass


@disable
def term_catalogue():
    """
    Return a list of rows representing all known terms. Each row
    should be a tuple in the form: ('term-code', 'term-name',
    'start-date', 'end-date'), where the dates are instances of the
    datetime.date class.
    """
    pass


@disable
def cat_search(query, start=1, limit=10):
    """
    Given a query, and optional start/limit values, return a tuple
    (results, numhits). Results is a list of
    xml.etree.ElementTree.Element instances. Each instance is a
    MARCXML '<{http://www.loc.gov/MARC21/slim}record>'
    element. Numhits is the total number of hits found against the
    search, not simply the size of the results lists.
    """


@disable
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
