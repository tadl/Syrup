from django.db import models as m
from django.contrib.auth.models import User
from django.contrib.auth.models import AnonymousUser
from datetime import datetime
from genshi import Markup
from django.utils.translation import ugettext as _
import re
import random
from django.utils import simplejson
from conifer.middleware import genshi_locals
# campus and library integration
from conifer.integration._hooksystem import *
from django.conf import settings
campus = settings.CAMPUS_INTEGRATION
# TODO: fixme, not sure if conifer.custom is a good parent.
from conifer.custom import lib_integration

#----------------------------------------------------------------------

class BaseModel(m.Model):
    class Meta:
        abstract = True

    created = m.DateTimeField(auto_now_add=True)
    last_modified = m.DateTimeField(auto_now=True)

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

class UserExtensionMixin(object):
    def reading_lists(self):
        return ReadingList.objects.filter(group__membership__user=self.id)

    def can_create_reading_lists(self):
        return self.is_staff or \
            bool(callhook('can_create_reading_lists', self))

    @classmethod
    def active_instructors(cls):
        """Return a queryset of all active instructors."""
        # We are using the Django is_active flag to model activeness.
        return cls.objects.filter(membership__role='INSTR', is_active=True) \
            .order_by('-last_name','-first_name').distinct()



for k,v in [(k,v) for k,v in UserExtensionMixin.__dict__.items() \
                if not k.startswith('_')]:
    setattr(User, k, v)

#------------------------------------------------------------

class UserProfile(BaseModel):
    user         = m.ForeignKey(User)
    ils_userid   = m.CharField(_('ILS patron ID'),
                               max_length=50, blank=True, null=True)

    # When we add email notices for new items, this is how we'll set
    # the preference, and how far back we'll need to look.

    wants_email_notices = m.BooleanField(default=False)
    last_email_notice   = m.DateTimeField(
        default=datetime.now, blank=True, null=True)

    def __unicode__(self):
        return 'UserProfile(%s)' % self.user


#----------------------------------------------------------------------
# Lookup tables

class ServiceDesk(BaseModel):
    name        = m.CharField(max_length=100)
    active      = m.BooleanField(default=True)
    external_id = m.CharField(max_length=256, blank=True, null=True)

    def __unicode__(self):
        return self.name

class Term(BaseModel):
    code   = m.CharField(max_length=64)
    name   = m.CharField(max_length=256)
    start  = m.DateField('Start (Y-M-D)')
    finish = m.DateField('Finish (Y-M-D)')

    def __unicode__(self):
        return self.code or self.name

class Department(BaseModel):
    name   = m.CharField(max_length=256)
    active = m.BooleanField(default=True)
    service_desk = m.ForeignKey(ServiceDesk)

    def __unicode__(self):
        return self.name

class Course(BaseModel):
    """An abstract course (not a course offering.)"""
    code = m.CharField(max_length=64)
    name = m.CharField(max_length=1024)
    department = m.ForeignKey(Department)

    def __unicode__(self):
        return self.name

class Z3950Target(m.Model):
    name     = m.CharField(max_length=100)
    host     = m.CharField(max_length=50)
    database = m.CharField(max_length=50)
    port     = m.IntegerField(default=210)
    syntax   = m.CharField(max_length=10, default='USMARC')
    active   = m.BooleanField(default=True)

    def __unicode__(self):
        return self.name

class Config(m.Model):
    name  = m.CharField(max_length=256)
    value = m.CharField(max_length=8192)

    @classmethod
    def get(cls, name, default=None, translator=lambda x: x):
        try:
            c = cls.objects.get(name=name)
            return translator(c.value)
        except cls.DoesNotExist:
            return default

#------------------------------------------------------------

class ReadingList(BaseModel):
    """A a list of materials for one (or more) course offering(s)."""
    # some courses may be ad-hoc and have no code.
    # TODO: constrain there is at least one course and one term (deferred).
    courses = m.ManyToManyField(Course)
    terms = m.ManyToManyField(Term)
    owner = m.ForeignKey(User)
    service_desk = m.ForeignKey(ServiceDesk)

    access = m.CharField(max_length=5,
                         default='CLOSE',
                         choices = [
            ('ANON', _('World-accessible')),
            ('LOGIN', _('Accessible to all logged-in users')),
            ('STUDT', _('Accessible to course students (by section)')),
            ('INVIT', _('Accessible to course students (by invitation code)')),
            ('CLOSE', _('Accessible only to course owners'))])

    # For sites that use a passkey as an invitation (INVIT access).
    # Note: only set this value using 'generate_new_passkey'.
    # TODO: for postgres, add UNIQUE constraint on 'passkey'.
    passkey = m.CharField(db_index=True, blank=True, null=True, max_length=256)

    def __unicode__(self):
        cc = '%s' % (', '.join([c.code for c in self.courses]))
        tt = '(%s)' % (', '.join([t.code for t in self.terms]))
        oo = '(%s)' % self.owner.last_name
        return u'%s %s %s' % (cc, tt, oo)

    def list_display(self):
        if self.code:
            return '%s: %s [%s]' % (self.term, self.title, self.code)
        else:
            return '%s: %s' % (self.term, self.title)

    def items(self):
        return self.item_set.all()

    def headings(self):
        """A list of all items which are headings."""
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

    def course_url(self, suffix=''):
        # I'm not fond of this being here. I think I'll leave this and
        # item_url non-implemented, and monkey-patch them in views.py.
        req = genshi_locals.get_request()
        prefix = req.META['SCRIPT_NAME']
        return '%s/course/%d/%s' % (prefix, self.id, suffix)

    def generate_new_passkey(self):
        # todo: have a pluggable passkey algorithm.
        def algorithm():
            # four numbers, separated by dashes, e.g. "342-58-928-21".
            return '-'.join([str(random.randint(1,999)) for x in range(4)])
        while True:
            key = algorithm()
            try:
                crs = ReadingList.objects.get(passkey=key)
            except ReadingList.DoesNotExist:
                self.passkey = key
                break

    #--------------------------------------------------
    # membership-related functions

    def members(self):
        return Membership.objects.filter(group__reading_list=self)

    def get_students(self):
        return self.memberships(role='STUDT').order_by(
            'user__last_name', 'user__first_name')

    def get_instructors(self):
        return self.memberships(role='INSTR').order_by(
            'user__last_name', 'user__first_name')

    def can_edit(self, user):
        if user.is_anonymous():
            return False
        if user.id == self.owner_id:
            return True
        try:
            mbr = self.members.get(user=user)
        except Member.DoesNotExist:
            return False
        return mbr.role in (u'INSTR', u'ASSIST')

    def is_joinable_by(self, user):
        """Return True if the user could feasibly register into this
        course: she's not already in it, and the course allows open
        registration."""
        return user.is_authenticated() \
            and self.access in ('ANON', 'LOGIN') \
            and not user.id == self.owner_id \
            and not self.members.filter(user=user).exists()


#------------------------------------------------------------
# User membership in reading lists

class Group(BaseModel):
    """
    A group of users associated with a ReadingList. A ReadingList will
    have one internal group, but may have zero or more external
    groups.

    Each ReadingList will have exactly one Group with a NULL
    external_id, intended for internal memberships. It may have zero
    or more Groups with non-NULL external_ids, representing various
    external user-groups that should have access to this ReadingList.

    A consequence of this design is that a user may appear in a
    ReadingList more than once, with different roles.

    Note, a ReadingList may be open-access, but still have members
    with 'student' access. In this case memberships won't imply
    authorization, but can be used for personalization (e.g. to show a
    list of "my reading lists").
    """

    # TODO: add constraints to ensure that each ReadingList has
    # exactly one Group with external_id=NULL, and that (readinglist,
    # external_id) is unique forall external_id != NULL.

    reading_list = m.ForeignKey(ReadingList)
    external_id = m.CharField(null=True, blank=True,
                              db_index=True,
                              max_length=2048)

    def __unicode__(self):
        return u"Group('%s', '%s')" % (self.reading_list,
                                       self.external_id or '(internal)')

class Membership(BaseModel):

    class Meta:
        unique_together = (('group', 'user'))

    user = m.ForeignKey(User)
    group = m.ForeignKey(Group)

    role = m.CharField(
        choices = (
            ('INSTR', _('Instructor')),
            ('ASSIST', _('Assistant/Support')),
            ('STUDT', _('Student'))),
        default = 'STUDT',
        max_length = 6)


    def __unicode__(self):
        return '%s; %s; %s' % (self.user, self.role, self.group)

    # TODO: these belong elsewhere.

    def instr_name_hl(self, terms):
        hl_instr = self.user.last_name
        for term in terms:
            hl_instr = highlight(hl_instr,term)

        return hl_instr

    def instr_name(self):
        return self.user.last_name


#------------------------------------------------------------
# ITEMS

class Item(BaseModel):
    """
    A reserve item, physical or electronic, as it appears in a given
    ReadingList instance. If an item appears on multiple reading
    lists, it will have multiple Item records associated with it.
    """

    # Structure

    # Items comprise both items proper, as well as headings. In the
    # database, all items are stored as a flat list; the sort_order
    # dictates the sequencing of items within their parent group.

    reading_list = m.ForeignKey(ReadingList)

    ITEM_TYPE_CHOICES = (
        ('ELEC', _('Attached Electronic Document')), # PDF, Doc, etc.
        ('PHYS', _('Physical Book or Document')),
        ('URL',  _('URL')),
        ('HEADING', _('Heading')))

    item_type = m.CharField(max_length=7, choices=ITEM_TYPE_CHOICES)

    # TODO: If we want support for ephemeral physical objects, we
    # might need to add a catalogue model for tracking local
    # Ephemerals, and add an EPHEM item-type to refer to them. The
    # contract would be that an ephmeral ID could be reused over time,
    # and so it might resolve to the wrong item (or no item at all) if
    # deferenced after the active timeframe of the ReadingList.

    #--------------------------------------------------
    # ILS integration

    # Ultimately every physical Item needs a bib_id so that we can
    # process ILS requests. During creation, the bib_id may be absent;
    # we may only have a MARCXML record (e.g. if the item was
    # discovered in an external catalogue.) Even that may not be true:
    # we may only know a few DC attributes (title, creator) if the
    # Item was manually entered.

    # Remember that electronic (ELEC and URL) items may also have
    # bib_id's and MARC records.

    bib_id = m.CharField('Bib Record ID', max_length=256, blank=True, null=True)
    marcxml = m.TextField('MARCXML', blank=True, null=True)

    # Fundamental metadata. These attributes may be populated from
    # MARCXML or DC attributes. Even if these attributes exist in the
    # metadata record, we copy them here so that we can efficiently
    # display search-results in lists.

    title     = m.CharField(max_length=8192, db_index=True)

    # Author(s) in Surname, given. Surname, given. format, for display.
    author    = m.CharField(max_length=8192, db_index=True,
                            null=True, blank=True)

    # publisher: "Place: Publisher", as in a bibliography, for display.
    publisher = m.CharField(max_length=8192, null=True, blank=True)
    published = m.DateField(null=True, blank=True)

    ITEMTYPE_CHOICES = [
        # From http://www.oclc.org/bibformats/en/fixedfield/type.shtm.
        # It is hoped that this can be harvested from the 006 field in
        # the MARC record.
        (None, 'Unknown/not specified'),
        ('a', 'Text'),
        ('c', 'Notated music'),
        ('d', 'Manuscript notated music'),
        ('e', 'Cartographic material'),
        ('f', 'Manuscript cartographic material'),
        ('g', 'Projected medium'),
        ('i', 'Sound recording: non-musical'),
        ('j', 'Sound recording: musical'),
        ('k', 'Two-dimensional graphic'),
        ('m', 'Electronic resource'),
        ('o', 'Kit'),
        ('p', 'Mixed materials'),
        ('r', 'Three-dimensional object'),
        ('t', 'Manuscript'),
        ]
    itemtype  = m.CharField('Type', max_length=1, db_index=True,
                            null=True, blank=True,
                            choices=ITEMTYPE_CHOICES)

    # parent must be a heading. could use ForeignKey.limit_choices_to,
    # to enforce this in the admin ui.
    parent_heading = m.ForeignKey('Item', blank=True, null=True)

    #--------------------------------------------------
    # Electronic items

    # For items of type URL
    url = m.URLField(blank=True, null=True)

    # for items of type ELEC (attached electronic document)
    fileobj = m.FileField(upload_to='uploads/%Y/%m/%d', max_length=255,
                          blank=True, null=True, default=None)
    fileobj_mimetype = m.CharField(max_length=128, blank=True, null=True)


    def __unicode__(self):
        return self.title


    def hierarchy(self):
        """
        Return a list of items: the first is the topmost ancestor of
        this item in the heading hierarchy; the last is the current
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
        # I'm not fond of this being here. I think I'll leave this and
        # course_url non-implemented, and monkey-patch them in views.py.
        req = genshi_locals.get_request()
        prefix = req.META['SCRIPT_NAME']
        if self.item_type == 'ELEC' and suffix == '':
            return '%s/course/%d/item/%d/dl/%s' % (
                prefix, self.course_id, self.id,
                self.fileobj.name.split('/')[-1])
        if self.item_type == 'URL' and suffix == '' and not force_local_url:
            return self.url
        else:
            return '%s/course/%d/item/%d/%s' % (
                prefix, self.course_id, self.id, suffix)

    def parent_url(self, suffix=''):
        if self.parent_heading:
            return self.parent_heading.item_url()
        else:
            return self.course.course_url()

    def describe_physical_item_status(self):
        """Return a (bool,str) tuple: whether the item is available,
        and a friendly description of the physical item's status"""
        # TODO: this needs to be reimplemented, based on copy detail
        # lookup in the ILS. It also may not belong here!
        raise NotImplementedError

    # TODO: stuff I'm not sure about yet. I don't think it belongs here.

    def title_hl(self, terms):
        hl_title = self.title
        for term in terms:
            hl_title = highlight(hl_title,term)

        return hl_title

    def author_hl(self, terms):
        hl_author = self.author()

        for term in terms:
            hl_author = highlight(hl_author,term)

        return hl_author


#------------------------------------------------------------
# TODO: move this to a utility module.

def highlight(text, phrase,
              highlighter='<strong class="highlight">\\1</strong>'):
    """
    >>> highlight('The River is Wide', 'wide')
    'The River is <strong class="highlight">Wide</strong>'
    """
    if not phrase or not text:
        return text
    highlight_re = re.compile('(%s)' % re.escape(phrase), re.I)
    if hasattr(text, '__html__'):
        return literal(highlight_re.sub(highlighter, text))
    else:
        return highlight_re.sub(highlighter, text)
