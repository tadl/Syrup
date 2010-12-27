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


@disable
def department_course_catalogue():
    """
    Return a list of rows representing all known, active courses and
    the departments to which they belong. Each row should be a tuple
    in the form: ('Department name', 'course-code', 'Course name').
    """


@disable
def term_catalogue():
    """
    Return a list of rows representing all known terms. Each row
    should be a tuple in the form: ('term-code', 'term-name',
    'start-date', 'end-date'), where the dates are instances of the
    datetime.date class.
    """


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


@disable
def bib_id_to_marcxml(bib_id):
    """
    Given a bib_id, return a MARC record in MARCXML format. Return
    None if the bib_id does not exist.
    """

    
@disable
def get_better_copy_of_marc(marc_string):
    """
    This function takes a MARCXML record and returns either the same
    record, or another instance of the same record from a different
    source. 

    This is a hack. There is currently at least one Z39.50 server that
    returns a MARCXML record with broken character encoding. This
    function declares a point at which we can work around that server.
    """


@disable
def marcxml_to_url(marc_string):
    """
    Given a MARC record, return either a URL (representing the
    electronic resource) or None.

    Typically this will be the 856$u value; but in Conifer, 856$9 and
    856$u form an associative array, where $9 holds the institution
    codes and $u holds the URLs.
    """

@disable
def external_person_lookup(userid):
    """
    Given a userid, return either None (if the user cannot be found),
    or a dictionary representing the user. The dictionary must contain
    the keys ('given_name', 'surname') and should contain 'email' if
    an email address is known.
    """

@disable
def external_memberships(userid):
    """
    Given a userid, return a list of dicts,
    representing the user's memberships in known external groups.
    Each dict must include the following key/value pairs:
    'group': a group-code, externally defined;
    'role':  the user's role in that group, one of (INSTR, ASSIST, STUDT).
    """

@disable
def user_needs_decoration(user_obj):
    """
    User objects are sometimes created automatically, with only a
    username. This function determines whether it would be fruitful to
    "decorate" the User object with, e.g., a given name, surname, and
    email address. It doesn't perform the decoration, it simply tests
    whether the current user object is "incomplete." Another hook
    'external_person_lookup,' is used by Syrup to fetch the personal
    information when needed.
    """

@disable
def proxify_url(url):
    """
    Given a URL, determine whether the URL needs to be passed through
    a reverse-proxy, and if so, return a modified URL that includes
    the proxy. If not, return None.
    """

@disable
def download_declaration():
    """
    Returns a string. The declaration to which students must agree when
    downloading electronic documents. If not customized, a generic message
    will be used.
    """
