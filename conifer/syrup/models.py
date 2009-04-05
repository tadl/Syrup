from django.db import models as m
from django.contrib.auth.models import User
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_backends
from datetime import datetime
from genshi import Markup
from django.utils.translation import ugettext as _
from conifer.custom import course_codes # fixme, not sure if conifer.custom is a good parent.
from conifer.custom import course_sections # fixme, not sure if conifer.custom is a good parent.
from conifer.custom import lib_integration
import re
import random

def highlight(text, phrase,
              highlighter='<strong class="highlight">\\1</strong>'):
    ''' This may be a lame way to do this, but will want to highlight matches somehow

        >>> highlight('The River is Wide', 'wide')
        'The River is <strong class="highlight">Wide</strong>'

    '''
    if not phrase or not text:
        return text
    highlight_re = re.compile('(%s)' % re.escape(phrase), re.I)
    if hasattr(text, '__html__'):
        return literal(highlight_re.sub(highlighter, text))
    else:
        return highlight_re.sub(highlighter, text)


#----------------------------------------------------------------------
# USERS

# Note, we're using the User class from django_auth. User-fields not
# given in User are stored in the UserProfile, below. See:
# http://www.b-list.org/weblog/2006/jun/06/django-tips-extending-user-model/

# We will also monkey-patch the User object so that certain methods
# can be made available on the User that are not part of the Django
# User model. Let's try this for a bit see how this works out.

# General methods that return sets of users (e.g. all instructors, all
# staff) -- let's put those on the UserProfile class, as class
# methods. For now, let's put personal methods (e.g. my courses) on
# the User object (although UserProfile would be another logical
# candidate).

class UserExtensionHack(object):
    def courses(self):
        return Course.objects.filter(member__user=self.id)

    @classmethod
    def active_instructors(cls):
        """Return a queryset of all active instructors."""
        # We are using the Django is_active flag to model activeness.
        return cls.objects.filter(member__role='INSTR', is_active=True) \
            .order_by('-last_name','-first_name')
    
for k,v in [(k,v) for k,v in UserExtensionHack.__dict__.items() \
                if not k.startswith('_')]:
    setattr(User, k, v)


class UserProfile(m.Model):
    user         = m.ForeignKey(User, unique=True)
    home_phone   = m.CharField(max_length=100, blank=True)
    home_address = m.TextField(blank=True)
    ils_userid   = m.CharField(_('Alternate userid in the ILS, if any'),
                               max_length=50, blank=True)

    # When we add email notices for new items, this is how we'll set
    # the preference, and how far back we'll need to look.
    wants_email_notices = m.BooleanField(default=False)
    last_email_notice   = m.DateTimeField(default=datetime.now,
                                          blank=True, null=True)

    def __unicode__(self):
        return 'UserProfile(%s)' % self.user

#----------------------------------------------------------------------
# Initializing an external user account

# For usernames that come from external authentication sources (LDAP,
# Evergreen, etc.) we need a general way to look up a user who may not
# yet have a Django account.  For example, you might want to add user
# 'xsmith' as the instructor for a course. If 'xsmith' is in LDAP but
# not yet in Django, it would be nice if a Django record were lazily
# created for him upon lookup. 

# That's what 'maybe_initialize_user' is for: participating backends
# provide a 'maybe_initialize_user' method which creates a new User
# record if one doesn't exist. Otherwise, 'maybe_initialize_user' is
# equivalent to 'User.objects.get(username=username)'.

_backends_that_can_initialize_users = [
    be for be in get_backends() if hasattr(be, 'maybe_initialize_user')]

def maybe_initialize_user(username):
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        for be in _backends_that_can_initialize_users:
            user = be.maybe_initialize_user(username, look_local=False)
            if user:
                return user

#----------------------------------------------------------------------
# LIBRARIES, SERVICE DESKS

class LibraryUnit(m.Model):
    name = m.CharField(max_length=100)
    nickname = m.CharField(max_length=15,blank=True,default='')
    url = m.URLField()
    contact_email = m.EmailField()

    def __unicode__(self):
        return self.name

class ServiceDesk(m.Model):
    library = m.ForeignKey(LibraryUnit)
    abbreviation = m.CharField(max_length=8,db_index=True)
    name = m.CharField(max_length=100)
    active = m.BooleanField(default=True)

    def __unicode__(self):
        return self.name

#----------------------------------------------------------------------
# TERMS, COURSES, MEMBERSHIP

class Term(m.Model):
    code   = m.CharField(max_length=16, blank=True, null=True, unique=True)
    name   = m.CharField(max_length=255)
    start  = m.DateField()
    finish = m.DateField()

    def __unicode__(self):
        return self.code or self.name

class Department(m.Model):
    abbreviation = m.CharField(max_length=8,db_index=True)
    name   = m.CharField(max_length=255)
    active = m.BooleanField(default=True)

    def __unicode__(self):
        return self.name

class Course(m.Model):
    """An offering of a course."""
    # some courses may be ad-hoc and have no code.
    code = m.CharField(max_length=64, blank=True, null=True)
    department = m.ForeignKey(Department)
    term = m.ForeignKey(Term)
    title = m.CharField(max_length=1024)
    access = m.CharField(max_length=5,
                         choices = [
                                 ('ANON', _('World-accessible')),
                                 ('LOGIN', _('Accessible to all logged-in users')),
                                 ('STUDT', _('Accessible to course students (by section)')),
                                 ('INVIT', _('Accessible to course students (by invitation code)')),
                                 ('CLOSE', _('Accessible only to course owners'))],
                         default='CLOSE')

    # For sites that use a passkey as an invitation (INVIT access).
    passkey = m.CharField(db_index=True, blank=True, null=True, max_length=255)

    # For sites that have registration-lists from an external system
    # (STUDT access).
    enrol_codes  = m.CharField(_('Registrar keys for class lists'),
                               max_length=4098, 
                               blank=True, null=True)


    def save(self, force_insert=False, force_update=False):
        # We need to override save() to ensure unique passkey
        # values. Django (and some backend databases) will not allow
        # multiple NULL values in a unique column.
        if self.passkey:
            try:
                already = Course.objects.exclude(pk=self.id).get(passkey=self.passkey)
            except Course.DoesNotExist:
                super(Course, self).save(force_insert, force_update)
        else:
            super(Course, self).save(force_insert, force_update)

    def __unicode__(self):
        return self.code or self.title

    def list_display(self):
        if self.code:
            return '%s: %s [%s]' % (self.term, self.title, self.code)
        else:
            return '%s: %s' % (self.term, self.title)

    def items(self):
        return self.item_set.all()

    def headings(self):
        """A list of all items which are headings."""
        #fixme, not sure 'title' is the best ordering.
        return self.item_set.filter(item_type='HEADING').order_by('title')

    def item_tree(self, subtree=None):
        """
        Return a list, representing a tree of the course items, in
        display order.  Every element of the list is an (Item, [Item])
        tuple, where the second element is a list of sub-elements (if
        a heading) or None (if an item).

        You can provide a 'subtree', an item which is the top node in
        a subtree of the item-tree. If subtree is provided, then
        return either a single (Item, [Item]) pair, where Item is the
        subtree element, or None if there is no match.
        """
        items = self.items()
        # make a node-lookup table
        dct = {}                
        for item in items:
            dct.setdefault(item.parent_heading, []).append(item)
        for lst in dct.values():
            lst.sort(key=lambda item: item.sort_order) # sort in place
        # walk the tree
        out = []
        def walk(parent, accum):
            here = dct.get(parent, [])
            for item in here:
                sub = []
                walk(item, sub)
                accum.append((item, sub))
        walk(subtree, out)
        return out

    def can_edit(self, user):
        if user.is_anonymous():
            return False
        try:
            mbr = Member.objects.get(course=self, user=user)
        except Member.DoesNotExist:
            return False
        return mbr.role in (u'INSTR', u'PROXY')

    def course_url(self, suffix=''):
        return '/syrup/course/%d/%s' % (self.id, suffix)

    def generate_new_passkey(self):
        # todo: have a pluggable passkey algorithm.
        def algorithm():
            # four numbers, separated by dashes, e.g. "342-58-928-21".
            return '-'.join([str(random.randint(1,999)) for x in range(4)])
        while True:
            key = algorithm()
            try:
                crs = Course.objects.get(passkey=key)
            except Course.DoesNotExist:
                self.passkey = key
                break

    def sections(self):
        delim = course_sections.sections_tuple_delimiter
        if not delim:
            return []
        else:
            def inner():
                parts = self.enrol_codes.split(delim)
                while len(parts) > 2:
                    yield tuple(parts[:3])
                    del parts[:3]
            return set(inner())

    def add_sections(self, *sections):
        assert all(len(s)==3 for s in sections), repr(sections)
        current = self.sections()
        sections = set(sections).union(current)
        self.enrol_codes = _merge_sections(sections)

    def drop_sections(self, *sections):
        assert all(len(s)==3 for s in sections), repr(sections)
        current = self.sections()
        sections = current - set(sections)
        self.enrol_codes = _merge_sections(sections)

    def get_students(self):
        return User.objects.filter(member__course__exact=self, member__role__exact='STUDT') \
            .order_by('last_name', 'first_name')
    
    def get_instructors(self):
        return User.objects.filter(member__course__exact=self, member__role__exact='INSTR') \
            .order_by('last_name', 'first_name')

def _merge_sections(secs):
    delim = course_sections.sections_tuple_delimiter
    return delim.join(delim.join(sec) for sec in secs)

def section_decode_safe(secstring):
    if not secstring:
        return None
    return tuple(secstring.decode('base64').split(course_sections.sections_tuple_delimiter))

def section_encode_safe(section):
    return course_sections.sections_tuple_delimiter.join(section).encode('base64').strip()

class Member(m.Model):
    class Meta:
        unique_together = (('course', 'user'))

    course = m.ForeignKey(Course)
    user = m.ForeignKey(User)
    role = m.CharField(
        choices = (
                ('INSTR', _('Instructor')),
                ('PROXY', _('Proxy Instructor')),
                ('STUDT', _('Student'))),
        default = 'STUDT',
        max_length = 5)

    # a user is 'provided' if s/he was added automatically due to
    # membership in an external registration system. The notion is
    # that these students can be automatically removed by add/drop
    # processors.
    provided = m.BooleanField(default=False)

    def instr_name_hl(self, terms):
        hl_instr = self.user.last_name
        for term in terms:
            hl_instr = highlight(hl_instr,term)

        return hl_instr

    def instr_name(self):
        return self.user.last_name

    def __unicode__(self):
        return '%s--%s--%s' % (self.user, self.role, self.course)


#------------------------------------------------------------
# ITEMS

class Item(m.Model):
    """
    A reserve item, physical or electronic, as it appears in a given
    course instance.
    """
    
    # Structure

    # Items comprise both items-proper, as well as headings. In the
    # database, all items are stored as a flat list; the sort_order
    # dictates the sequencing of items within their parent group.
    
    course = m.ForeignKey(Course)
    ITEM_TYPE_CHOICES = (
        ('ELEC', _('Attached Electronic Document')), # PDF, Doc, etc.
        ('PHYS', _('Physical Book or Document')),
        ('URL',  _('URL')),
        ('HEADING', _('Heading')))
    item_type = m.CharField(max_length=7, choices=ITEM_TYPE_CHOICES)
    sort_order = m.IntegerField(default=0)

    # parent must be a heading. could use ForeignKey.limit_choices_to,
    # to enforce this in the admin ui.
    parent_heading = m.ForeignKey('Item', blank=True, null=True)

    # the display title may not be the same as the dc:title.
    title = m.CharField(max_length=255,db_index=True) 

    # ditto the URL: this is for display items that are links.
    url = m.URLField(blank=True, null=True)

    # for items of type ELEC (attached electronic document)
    fileobj = m.FileField(upload_to='uploads/%Y/%m/%d', max_length=255,
                          blank=True, null=True, default=None)

    fileobj_mimetype = m.CharField(max_length=128, blank=True, null=True, default=None)

    # basic timestamps
    date_created = m.DateTimeField(auto_now_add=True)
    last_modified = m.DateTimeField(auto_now=True)


    # stuff I'm not sure about yet. I don't think it belongs here.

    STATUS_CHOICE = (('INPROCESS', _('In Process')), # physical, pending
                     ('ACTIVE', _('Active')),        # available
                     ('INACTIVE', _('Inactive')))    # no longer on rsrv.
    phys_status = m.CharField(max_length=9, 
                              null=True, blank=True,
                              choices=STATUS_CHOICE, 
                              default=None) # null if not physical item.

    activation_date = m.DateField(auto_now=False, blank=True, null=True)
    expiration_date = m.DateField(auto_now=False, blank=True, null=True)
    
    # requested_loan_period: why is this a text field?
    requested_loan_period = m.CharField(max_length=255,blank=True,default='', null=True)


    def title_hl(self, terms):
        hl_title = self.title
        for term in terms:
            hl_title = highlight(hl_title,term)

        return hl_title

    def author(self):
        creators = self.metadata_set.filter(name='dc:creator')
        return creators and creators[0].value or None

    def barcode(self):
        bc = self.metadata_set.filter(name='syrup:barcode')
        return bc and bc[0].value or None

    def smallint(self):
        bc = self.barcode()
        phys = PhysicalObject.by_barcode(bc)
        return phys and phys.smallint or None

    @classmethod
    def with_smallint(cls, smallint):
        phys = PhysicalObject.by_smallint(smallint)
        barcode = phys and phys.barcode or None
        if not barcode:
            return cls.objects.filter(pk=-1) # empty set
        else:
            return cls.with_barcode(barcode)
        
    @classmethod
    def with_barcode(cls, barcode):
        return cls.objects.filter(metadata__name='syrup:barcode', 
                                  metadata__value=barcode)

    def author_hl(self, terms):
        hl_author = self.author()

        for term in terms:
            hl_author = highlight(hl_author,term)

        return hl_author

    
    def __unicode__(self):
        return self.title

    def hierarchy(self):
        """Return a list of items; the first is the topmost ancestor
        of this item in the heading hierarchy; the last is the current
        item.
        """
        if self.parent_heading is None:
            return [self]
        else:
            return self.parent_heading.hierarchy() + [self]

    def children(self):
        return Item.objects.filter(parent_heading=self)

    def needs_meta_link(self):
        """Should an 'About' link be displayed for this item?"""

        return self.item_type in ('ELEC', 'URL', 'PHYS')

    def item_url(self, suffix='', force_local_url=False):
        if self.item_type == 'ELEC' and suffix == '':
            return '/syrup/course/%d/item/%d/dl/%s' % (
                self.course_id, self.id, 
                self.fileobj.name.split('/')[-1])
        if self.item_type == 'URL' and suffix == '' and not force_local_url:
            return self.url
        else:
            return '/syrup/course/%d/item/%d/%s' % (
                self.course_id, self.id, suffix)
    
    def parent_url(self, suffix=''):
        if self.parent_heading:
            return self.parent_heading.item_url()
        else:
            return self.course.course_url()

    def describe_physical_item_status(self):
        """Return a (bool,str) tuple: whether the item is available,
        and a friendly description of the physical item's status"""
        if self.item_type != 'PHYS':
            return False, _('(Not a physical item)')
        
        #fixme: just having barcode in item-metadata doesn't mean 'in Reserves'
        bc = self.barcode()
        if not bc:
            return False, _('On order')
        else:
            status = lib_integration.item_status(bc)
            return status['available'], _(status['status'])

metadata_attributes = {
    'dc:contributor': _('Contributor'),
    'dc:coverage': _('Coverage'),
    'dc:creator': _('Creator'),
    'dc:date': _('Date'),
    'dc:description': _('Description'),
    'dc:format': _('Format'),
    'dc:identifier': _('Identifier'),
    'dc:language': _('Language'),
    'dc:publisher': _('Publisher'),
    'dc:relation': _('Relation'),
    'dc:rights': _('Rights'),
    'dc:source': _('Source'),
    'dc:subject': _('Subject'),
    'dc:title': _('Title'),
    'dc:type': _('Type'),
    'syrup:barcode': _('Barcode'),
    'syrup:marc': _('MARC'),    # MARC in JSON format.
    'syrup:enumeration': _('Enumeration'),
    'syrup:chronology': _('Chronology')}


metadata_attribute_choices = metadata_attributes.items()
metadata_attribute_choices.sort(key=lambda (a,b): b)
class Metadata(m.Model):
    """Metadata for items."""

    item = m.ForeignKey(Item)
    #fixme, arbitrary sizes.
    name = m.CharField('Attribute', max_length=128, choices=metadata_attribute_choices)
    value = m.CharField(max_length=8192) # on postgres it doesn't matter how big.

#------------------------------------------------------------
# News items

try:
    import markdown
    def do_markdown(txt):
        return markdown.markdown(txt)
except ImportError:
    def do_markdown(txt):
        return _('(Markdown not installed).')

class NewsItem(m.Model):
    subject = m.CharField(max_length=200)
    body = m.TextField()
    published = m.DateTimeField(default=datetime.now, blank=True, null=True)
    encoding = m.CharField(max_length=10,
                           choices = (('plain', _('plain text')),
                                      ('html', _('HTML')),
                                      ('markdown', _('Markdown'))),
                           default = 'plain')

    def __unicode__(self):
        return u'%s (%s)' % (self.subject, self.published)

    def generated_body(self):
        if self.encoding == 'plain':
            return self.body
        elif self.encoding == 'html':
            return Markup(self.body)
        elif self.encoding == 'markdown':
            return Markup(do_markdown(self.body))

#----------------------------------------------------------------------
# Z39.50 Support

class Target(m.Model):
    name = m.CharField(max_length=100)
    host = m.CharField(max_length=50)
    db = m.CharField(max_length=50)
    port = m.IntegerField(default=210)
    syntax = m.CharField(max_length=10,default='USMARC')
    active = m.BooleanField(default=True)

    def __unicode__(self):
        return self.name

#----------------------------------------------------------------------
# SIP checkout

class CheckInOut(m.Model):
    """A log of checkout-to-patron and item-return events."""
    
    is_checkout = m.BooleanField()       # in or out?
    is_successful = m.BooleanField()     # did the transaction work?
    staff  = m.ForeignKey(User)          # who processed the request?
    patron = m.CharField(max_length=100) # barcode
    patron_descrip = m.CharField(max_length=512) # ILS descrip
    item   = m.CharField(max_length=100, null=True) # item barcode
    item_descrip = m.CharField(max_length=512, null=True)
    outcome = m.CharField(max_length=1024, null=True) # text msg from ILS about transaction
    processed = m.DateTimeField(auto_now_add=True)
    

class PhysicalObject(m.Model):
    """A record of a physical object entering and leaving the Reserves area."""
    barcode     = m.CharField(max_length=100) # item barcode
    receiver = m.ForeignKey(User, related_name='receiver') # who received the item?
    received    = m.DateTimeField(auto_now_add=True)
    departer = m.ForeignKey(User, blank=True, null=True, related_name='departer') # who sent it away?
    departed    = m.DateTimeField(blank=True, null=True)
    # an optional small-integer used as a human-shareable barcode by some institutions.
    smallint    = m.IntegerField(blank=True, null=True)


    def save(self, force_insert=False, force_update=False):
        # Must ensure that barcode is unique for non-departed items. Same with smallint
        try:
            unique_thing = 'barcode'
            already = PhysicalObject.objects.exclude(pk=self.id).get(departed=None)
            unique_thing = 'smallint'
            if self.smallint:
                already = PhysicalObject.objects.exclude(pk=self.id).get(smallint=self.smallint)
        except PhysicalObject.DoesNotExist:
            super(PhysicalObject, self).save(force_insert, force_update)
        else:
            raise AssertionError, '%s is not unique in active PhysicalObject collection.' % unique_thing

    @classmethod
    def by_smallint(cls, smallint):
        """Find object by smallint, searching *only* the non-departed items."""
        assert smallint
        res = cls.objects.filter(departed=None, smallint=smallint)
        return res and res[0] or None

    @classmethod
    def by_barcode(cls, barcode):
        """Find object by barcode, searching *only* the non-departed items."""
        res = cls.objects.filter(departed=None, barcode=barcode)
        return res and res[0] or None
