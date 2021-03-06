import random
import re

from collections                     import defaultdict
from conifer.libsystems              import marcxml as MX
from conifer.libsystems.evergreen.support import E1
from conifer.plumbing.genshi_support import get_request
from conifer.plumbing.hooksystem     import *
from datetime                        import datetime, timedelta, date
from django.conf                     import settings
from django.contrib.auth.models      import AnonymousUser, User
from django.db                       import models as m
from django.db.models                import Q
from django.utils                    import simplejson as json
from django.utils.translation        import ugettext as _
from genshi                          import Markup

#----------------------------------------------------------------------
#
# Load, but don't instantiate, the local integration module. This way, we can
# refer to static values in the module.

integration_class = None
OPENSRF_BARCODE           = "open-ils.search.asset.copy.fleshed2.find_by_barcode"

if hasattr(settings, 'INTEGRATION_CLASS'):
    modname, klassname = settings.INTEGRATION_CLASS.rsplit('.', 1) # e.g. 'foo.bar.baz.MyClass'
    mod = __import__(modname, fromlist=[''])
    integration_class = getattr(mod, klassname)

BIB_PART_MERGE = bool(getattr(settings, 'BIB_PART_MERGE', False))
PART_MERGE = bool(getattr(settings, 'PART_MERGE', True))

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
# methods. For now, let's put personal methods (e.g. my sites) on
# the User object (although UserProfile would be another logical
# candidate).


class UserExtensionMixin(object):

    class Meta:
        ordering = ['username']

    def sites(self, role=None):
        self.maybe_refresh_external_memberships()
        sites = Site.objects.filter(group__membership__user=self.id).distinct()
        if role:
            sites = sites.filter(group__membership__role=role)
        return sites

    def can_create_sites(self):
        return self.is_staff or \
            bool(callhook('can_create_sites', self))

    def get_list_name(self):
        return '%s, %s' % (self.last_name, self.first_name)

    # this is an override of User.get_profile. The original version will not
    # create a UserProfile which does not already exist.
    def get_profile(self):
        profile, just_created = UserProfile.objects.get_or_create(user=self)
        return profile

    @classmethod
    def active_instructors(cls):
        """Return a queryset of all active instructors."""
        # We are using the Django is_active flag to model activeness.
        return cls.objects.filter(membership__role='INSTR', is_active=True) \
            .order_by('-last_name','-first_name').distinct()


    # --------------------------------------------------
    # Membership in external groups

    EXT_MEMBERSHIP_CHECK_FREQUENCY = timedelta(seconds=3600)

    def maybe_refresh_external_memberships(self):
        profile = self.get_profile()
        last_checked = profile.external_memberships_checked
        if (not last_checked or last_checked <
            (datetime.now() - self.EXT_MEMBERSHIP_CHECK_FREQUENCY)):
            added, dropped = external_groups.reconcile_user_memberships(self)
            profile.external_memberships_checked = datetime.now()
            profile.save()
            return (added or dropped)

    def external_memberships(self):
        return callhook('external_memberships', self.username) or []

    def maybe_decorate(self):
        """
        If necessary, and if possible, fill in missing personal
        information about this user from an external diectory.
        """

        # can we look up users externally?
        if not gethook('external_person_lookup'):
            return

        # does this user need decorating?
        dectest = gethook('user_needs_decoration',
                          default=lambda user: user.last_name == '')
        if not dectest(self):
            return

        # can we find this user in the external directory?
        dir_entry = callhook('external_person_lookup', self.username)
        if dir_entry is None:
            return

        first_name = ""
        last_name = ""
        email = ""

        if dir_entry['given_name']:
            first_name = dir_entry['given_name']
        if dir_entry['surname']:
            last_name = dir_entry['surname']
        if dir_entry.get('email', self.email):
            email = dir_entry.get('email', self.email)

        self.first_name = first_name
        self.last_name  = last_name
        self.email      = email
        self.save()

        if 'patron_id' in dir_entry:
            # note, we overrode user.get_profile() to automatically create
            # missing profiles.
            self.get_profile().ils_userid = dir_entry['patron_id']
            profile.save()

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

    # when did we last check user's membership in externally-defined groups?
    external_memberships_checked = m.DateTimeField(blank=True, null=True)

    def __unicode__(self):
        return 'UserProfile(%s)' % self.user

    class Meta:
        ordering = ['user__username']


#----------------------------------------------------------------------
# Lookup tables

class ServiceDesk(BaseModel):
    name        = m.CharField(max_length=100, unique=True)
    active      = m.BooleanField(default=True)
    external_id = m.CharField(max_length=256, blank=True, null=True)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']

    @classmethod
    def default(cls):
        return cls.objects.get(pk=Config.get('default.desk', 1))

class Term(BaseModel):
    code   = m.CharField(max_length=64, unique=True)
    name   = m.CharField(max_length=256)
    start  = m.DateField('Start (Y-M-D)')
    finish = m.DateField('Finish (Y-M-D)')

    class Meta:
        ordering = ['start', 'code']

    def __unicode__(self):
        return '%s: %s' % (self.code, self.name)

    def midpoint(self):
        return self.start + (self.finish-self.start) / 2

    @classmethod
    def timeframe_query(cls, N=0, extent=30):
        """
        Returns three lists: a list of terms that recently ended, a list of
        terms that are active, and a list of terms that are upcoming soon.
        """
        N = int(N)
        today = date.today()
        delta = timedelta(days=extent)
        before = today - delta
        after  = today + delta

        if N == 0:              # active
            return Q(start_term__start__lte=today, end_term__finish__gte=today)
        elif N == -1:           # recently finished
            return Q(end_term__finish__lt=today, end_term__finish__gte=before)
        elif N == -2:           # all past courses
            return Q(end_term__finish__lt=today)
        elif N ==  1:           # starting soon
            return Q(start_term__start__lte=after, start_term__start__gt=today)
        elif N ==  2:           # all future courses
            return Q(start_term__start__gt=today)
        elif N == 99:           # no filter at all
            return Q()
        else:
            raise Exception('unknown timeframe: %d' % N)
        
class Department(BaseModel):
    name   = m.CharField(max_length=256)
    active = m.BooleanField(default=True)
    service_desk = m.ForeignKey(ServiceDesk)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Course(BaseModel):
    """An abstract course (not a course offering.)"""
    code = m.CharField(max_length=64, unique=True)
    name = m.CharField(max_length=1024)
    department = m.ForeignKey(Department)
    coursenotes = m.TextField('Course Notes', blank=True, null=True)

    class Meta:
        ordering = ['code']

    def __unicode__(self):
        return '%s: %s' % (self.code, self.name)


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
    name  = m.CharField(max_length=256, unique=True)
    value = m.CharField(max_length=8192)

    @classmethod
    def get(cls, name, default=None, translator=lambda x: x):
        try:
            c = cls.objects.get(name=name)
            return translator(c.value)
        except cls.DoesNotExist:
            return default

#------------------------------------------------------------

class Site(BaseModel):
    """A a list of materials for one (or more) course offering(s)."""
    course       = m.ForeignKey(Course)
    start_term   = m.ForeignKey(Term, related_name='start_term')
    end_term     = m.ForeignKey(Term, related_name='end_term')
    owner        = m.ForeignKey(User)
    service_desk = m.ForeignKey(ServiceDesk)

    ACCESS_CHOICES = [
        ('ANON',  _('World-accessible')),
        ('LOGIN', _('Accessible to all logged-in users')),
        ('RESTR', _('Accessible to all logged-in users, but only course-site members can read electronic documents.')),
        ('MEMBR', _('Accessible to course-site members')),
        ('CLOSE', _('Accessible only to course-site owners'))]

    ACCESS_DEFAULT = getattr(integration_class, 'SITE_DEFAULT_ACCESS_LEVEL', 'ANON')
    assert ACCESS_DEFAULT in [x[0] for x in ACCESS_CHOICES]

    access = m.CharField(max_length=5,
                         default=ACCESS_DEFAULT,
                         choices=ACCESS_CHOICES)

    sitenotes = m.TextField('Course Site Notes', blank=True, null=True)

    @property
    def term(self):
        """
        Returns the start term (typically the term thought of as 'the' term of
        the site).

        Whenever possible, use the explicit 'start_term' attribute rather than
        the 'term' property.
        """
        return self.start_term

    class Meta:
        unique_together = (('course', 'start_term', 'owner'))
        ordering = ['course__code', 'owner__last_name', '-start_term__start']

    def save(self, *args, **kwargs):
        # Assert that the term-order is logical.
        assert self.start_term.start <= self.end_term.start, \
            'The end-term cannot begin before the start-term.'
        # Ensure there is always an internal Group.
        super(Site, self).save(*args, **kwargs)
        internal, just_created = Group.objects.get_or_create(
            site=self, external_id=None)
        # ..and that the owner is an instructor in the site.
        Membership.objects.get_or_create(group    = internal,
                                         user     = self.owner,
                                         defaults = {'role':'INSTR'})

    def __unicode__(self):
        return u'%s: %s (%s, %s)' % (
            self.course.code, self.course.name,
            self.owner.last_name or self.owner.username,
            self.term.name)

    def list_display(self):
            return '%s [%s, %s]' % (self.course.name, self.course.code,
                                    self.term.name)

    def items(self):
        return self.item_set.all()

    def headings(self):
        """A list of all items which are headings."""
        return self.item_set.filter(item_type='HEADING').order_by('title')

    def item_tree_merge(self, edit_status=False):
        return self.item_tree(None,edit_status)

    def item_tree(self, subtree=None, edit_status=False):
        """
        Return a list, representing a tree of the site items, in
        display order.  Every element of the list is an (Item, [Item])
        tuple, where the second element is a list of sub-elements (if
        a heading) or None (if an item).

        You can provide a 'subtree', an item which is the top node in
        a subtree of the item-tree. If subtree is provided, then
        return either a single (Item, [Item]) pair, where Item is the
        subtree element, or None if there is no match.
        """

        # TODO: internationalize the stopwords list.
        STOPWORDS = set(['a', 'an', 'that', 'there', 'the', 'this'])

        RE_PUNCTUATION = re.compile("""[,'".:;]""")

        def sort_title(item):
            """First cut of a stop words routine."""
            text = item.lower()
            text = RE_PUNCTUATION.sub('', text) # remove common punctuation
            words = [t for t in text.split() if t not in STOPWORDS]
            return  " ".join(words)

        items = self.items()

        # make a node-lookup table
        dct = {}
        for item in items:
            dct.setdefault(item.parent_heading, []).append(item)
        for lst in dct.values():
            # TODO: what's the sort order? - art weighing in on normalized title
            lst.sort(key=lambda item: (item.item_type=='HEADING',
                                       sort_title(item.title))) # sort in place

        #has barcode already been dealt with
        def is_collected(poss,barcodes):
            for bc in barcodes:
                if poss.barcode in bc:
                    return True
            return False

        #only concerned about duplicate physical items
        def is_dup_candidate(poss):
            if len(poss.bib_id) > 0:
                if poss.item_type == 'PHYS':
                    if poss.barcode is not None:
                        return True
            return False

        def get_label(bc):
            partlabel = None
            copyinfo = E1(OPENSRF_BARCODE, bc)
            parts = copyinfo.get("parts")
            if parts:
                part = parts[0]
                if part:
                   partlabel = part['label']
            return partlabel

        #def parts_match(bc1,bc2,labels):
        def parts_match(bc1,bc2):
            label1 = get_label(bc1)
            if label1 is not None:
                label2 = get_label(bc2)
                if label1 == label2:
                    #add label to labels
                    return True
            return False

        #collect barcodes for titles with same bib id
        def deal_with_dups(item,items,edit_status,barcodes):
            dup_barcodes = []
            dup_ids = []
            push_thru = True

            if item.item_type == 'HEADING':
                return push_thru, dup_barcodes, dup_ids
            if (not BIB_PART_MERGE and not PART_MERGE) or edit_status:
                return push_thru, dup_barcodes, dup_ids
            if not is_dup_candidate(item):
                return push_thru, dup_barcodes, dup_ids
 
            if is_collected(item,barcodes):
                return False, dup_barcodes, dup_ids
                
            for display_item in items:
                 if is_dup_candidate(display_item):
                     if display_item.barcode != item.barcode:
                         if display_item.bib_id == item.bib_id and display_item.barcode not in dup_barcodes:
                             #if BIB_PART_MERGE or (PART_MERGE and parts_match(item.barcode,display_item.barcode,part_labels)):
                             if BIB_PART_MERGE or (PART_MERGE and parts_match(item.barcode,display_item.barcode)):
                                 dup_barcodes.append(display_item.barcode)
                                 dup_ids.append(display_item.id)

       
            #if added, make sure original is there
            if len(dup_barcodes) > 0 and not item.barcode in dup_barcodes:
                dup_barcodes.append(item.barcode)
                dup_ids.append(item.id)

            #sort out based on part_labels
            return push_thru, dup_barcodes, dup_ids

        # walk the tree - if bib or part merge flag, collect ids & barcodes for 
        # same bib or part, and only pass one instance onwards
        out = []
        def walk(parent, accum):
            out_barcodes = []
            out_ids = []
            here = dct.get(parent, [])
            for item in here:
                sub = []
                walk(item, sub)
                push_thru, bib_barcodes, syrup_ids = deal_with_dups(item,items,edit_status,out_barcodes)

                if len(bib_barcodes) > 0 and bib_barcodes not in accum:
                    if bib_barcodes not in out_barcodes:
                        out_barcodes.append(bib_barcodes)
                        out_ids.append(syrup_ids)
                if push_thru and bib_barcodes not in accum:
                    accum.append((item, sub, out_barcodes, out_ids))
        walk(subtree, out)
        # print "returning", out
        return out

    def site_url(self, suffix=''):
        # I'm not fond of this being here. I think I'll leave this and
        # item_url non-implemented, and monkey-patch them in views.py.
        req = get_request()
        script = req.META['SCRIPT_NAME']
        return req.build_absolute_uri('%s/site/%d/%s' % (script, self.id, suffix))

    def generate_new_passkey(self):
        # todo: have a pluggable passkey algorithm.
        def algorithm():
            # four numbers, separated by dashes, e.g. "342-58-928-21".
            return '-'.join([str(random.randint(1,999)) for x in range(4)])
        while True:
            key = algorithm()
            try:
                crs = Site.objects.get(passkey=key)
            except Site.DoesNotExist:
                self.passkey = key
                break

    #--------------------------------------------------
    # membership-related functions

    def members(self):
        return Membership.objects.filter(group__site=self)

    def get_students(self):
        return self.members().filter(role='STUDT').order_by(
            'user__last_name', 'user__first_name')

    def get_instructors(self):
        return self.members().filter(role='INSTR').order_by(
            'user__last_name', 'user__first_name')

    def can_edit(self, user):
        """
        Return True if the user has permission to edit this
        site. Staff, site owners and site instructors all have editing
        permissions.
        """
        if user.is_anonymous():
            return False
        if (user.id == self.owner_id) or user.is_staff:
            return True
        memberships = self.members().filter(user=user)
        return any(mbr.role in (u'INSTR', u'ASSIST') for mbr in memberships)

    def is_joinable_by(self, user):
        """Return True if the user could feasibly register into this
        site: she's not already in it, and the site allows open
        registration."""
        return self.access in ('ANON', 'LOGIN') \
            and not self.is_member(user)

    def is_member(self, user):
        assert user
        return user.is_authenticated() and (
            user.id == self.owner_id \
                or bool(self.members().filter(user=user)))

    def is_open_to(self, user):
        level = self.access
        if level == 'ANON' or user.is_staff:
            return True
        if not user.is_authenticated():
            return False
        if level in ('LOGIN', 'RESTR'):
            return True
        memberships = self.members().filter(user=user)
        if not memberships:
            return False
        if level == 'CLOSE':
            return any(mbr.role == u'INSTR' for mbr in memberships)
        elif level == u'MEMBR':
            return True
        else:
            raise Exception('Cannot determine access level '
                            'for user %s in site %s' % (user, self))

    def allows_downloads_to(self, user):
        """
        Return True if this site allows this user to download
        electronic documents. For 'restricted' sites, we allow any
        logged-in user to visit, but only members can download
        documents.
        """
        level = self.access
        if level == 'RESTR':
            return user.is_staff or self.is_member(user)
        else:
            return self.is_open_to(user)

    @classmethod
    def taught_by(cls, user):
        """Return a set of Sites for which this user is an Instructor."""
        return cls.objects.filter(group__membership__user=user,
                                  group__membership__role='INSTR') \
                                  .distinct().select_related()

    #--------------------------------------------------

    @classmethod
    def filter_for_user(cls, user):
        """
        Given a user object, return an appropriate Q filter that would
        filter only Sites that the user has permission to view.
        """
        if user.is_anonymous():
            return Q(access='ANON')
        elif user.is_staff:
            return Q()
        else:
            return (Q(access__in=('RESTR','LOGIN','ANON')) \
                        | Q(group__membership__user=user))

#------------------------------------------------------------
# User membership in sites

class Group(BaseModel):
    """
    A group of users associated with a Site. A Site will
    have one internal group, but may have zero or more external
    groups.

    Each Site will have exactly one Group with a NULL
    external_id, intended for internal memberships. It may have zero
    or more Groups with non-NULL external_ids, representing various
    external user-groups that should have access to this Site.

    A consequence of this design is that a user may appear in a
    Site more than once, with different roles.

    Note, a Site may be open-access, but still have members
    with 'student' access. In this case memberships won't imply
    authorization, but can be used for personalization (e.g. to show a
    list of "my sites").
    """

    # TODO: add constraints to ensure that each Site has
    # exactly one Group with external_id=NULL, and that (site,
    # external_id) is unique forall external_id != NULL.

    # TODO: On second thought, for now make it:
    # external_id is unique forall external_id != NULL.
    # That is, only one Site may use a given external group.

    site = m.ForeignKey(Site)
    external_id = m.CharField(null=True, blank=True,
                              db_index=True,
                              max_length=2048)

    def __unicode__(self):
        return u"Group('%s', '%s')" % (self.site,
                                       self.external_id or '(internal)')
    class Meta:
        ordering = ['site__course__code', 'site__course__name', 'external_id']


class Membership(BaseModel):

    class Meta:
        unique_together = (('group', 'user'))
        ordering = ['user__username',
                    'group__site__course__code', 'group__site__course__name', 'group__external_id']

    user = m.ForeignKey(User)
    group = m.ForeignKey(Group)

    ROLE_CHOICES = (
        ('INSTR', _('Instructor')),
        ('ASSIST', _('Assistant/Support')),
        ('STUDT', _('Student')))

    role = m.CharField(
        choices = ROLE_CHOICES,
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
    Site instance. If an item appears on multiple sites, it will have
    multiple Item records associated with it.
    """

    # Structure

    # Items comprise both items proper, as well as headings. In the
    # database, all items are stored as a flat list; the sort_order
    # dictates the sequencing of items within their parent group.

    site = m.ForeignKey(Site)

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
    # deferenced after the active timeframe of the Site.

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
    suppress_item = m.BooleanField(default=False)
    marcxml = m.TextField('MARCXML', blank=True, null=True)

    # Fundamental metadata. These attributes may be populated from
    # MARCXML or DC attributes. Even if these attributes exist in the
    # metadata record, we copy them here so that we can efficiently
    # display search-results in lists.

    title     = m.CharField(max_length=8192, db_index=True)

    # Author(s) in Surname, given. Surname, given. format, for display. Note,
    # for electronic reserves, we're going to use a semicolon as a separator
    # between multiple authors.
    author    = m.CharField(max_length=8192, db_index=True,
                            null=True, blank=True)

    # publisher: "Place: Publisher", as in a bibliography, for display.
    publisher = m.CharField(max_length=8192, null=True, blank=True)
    published = m.CharField(max_length=64, null=True, blank=True)

    # source title: e.g., title of journal
    source_title = m.CharField(max_length=8192, null=True, blank=True, db_index=True)
    volume       = m.CharField(max_length=64, null=True, blank=True)
    issue        = m.CharField(max_length=64, null=True, blank=True)
    pages        = m.CharField(max_length=64, null=True, blank=True)
    # isbn or issn (not validated)
    isbn         = m.CharField(max_length=17, null=True, blank=True)
    #barcode
    barcode      = m.CharField(max_length=14, null=True, blank=True)
    # These are defined in integration class
    CALLNO_PREFIX_CHOICES = getattr(integration_class, 'PREFIX_CHOICES',
                                       [(-1, '')])

    orig_prefix = m.IntegerField(choices=CALLNO_PREFIX_CHOICES,
                                default=CALLNO_PREFIX_CHOICES[0][0], blank=False)

    #orig_callno: this is a copy of the call number associated with the barcode
    orig_callno  = m.CharField(max_length=64, null=True, blank=True)

    # These are defined in integration class
    CALLNO_SUFFIX_CHOICES = getattr(integration_class, 'SUFFIX_CHOICES',
                                       [(-1, '')])

    orig_suffix = m.IntegerField(choices=CALLNO_SUFFIX_CHOICES,
                                default=CALLNO_SUFFIX_CHOICES[0][0], blank=False)

    # Options for evergreen updates
    EVERGREEN_UPDATE_CHOICES = getattr(integration_class, 'UPDATE_CHOICES',
                                       [('', 'n/a')])

    evergreen_update = m.CharField(max_length=4, blank=True,
                                   choices=EVERGREEN_UPDATE_CHOICES,
                                   default=EVERGREEN_UPDATE_CHOICES[0][0])

    # As per discussion with Art Rhyno and Joan Dalton, Leddy Library.
    COPYRIGHT_STATUS_CHOICES = [
        ('UK', 'unknown'),
        ('FD', 'fair dealing'),
        ('PG', 'permission granted'),
        ('LC', 'licensed content'),
        ]

    copyright_status = m.CharField(max_length=2,
                                   choices=COPYRIGHT_STATUS_CHOICES,
                                   default='UK')

    # These are defined in integration class
    CIRC_MODIFIER_CHOICES = getattr(integration_class, 'MODIFIER_CHOICES',
                                       [('', 'n/a')])

    circ_modifier = m.CharField(max_length=50,
                                choices=CIRC_MODIFIER_CHOICES,
                                default=CIRC_MODIFIER_CHOICES[0][0], blank=True)

    # These are defined in integration class
    CIRC_DESK_CHOICES = getattr(integration_class, 'DESK_CHOICES',
                                       [('', 'n/a')])

    circ_desk = m.CharField(max_length=5,
                            choices=CIRC_DESK_CHOICES,
                            default=CIRC_DESK_CHOICES[0][0], blank=True)

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
    url = m.URLField(blank=True, null=True, max_length=2048)

    # for items of type ELEC (attached electronic document)
    fileobj = m.FileField(upload_to='uploads', max_length=255,
                          blank=True, null=True, default=None)
    fileobj_origname = m.CharField(max_length=2048, blank=True, null=True)
    fileobj_mimetype = m.CharField(max_length=128, blank=True, null=True)

    itemnotes = m.TextField('Item Notes', blank=True, null=True)


    class Meta:
        ordering = ['title', 'author', 'published']

    def save(self, *args, **kwargs):
        # extract the bib ID from the MARC record if possible (and necessary)
        if self.marcxml and not self.bib_id:
            maybe_bib = callhook('marc_to_bib_id', self.marcxml)
            if maybe_bib:
                self.bib_id = maybe_bib
        # proxify the item's URL if necessary
        self.url = callhook('proxify_url', self.url) or self.url
        super(Item, self).save(*args, **kwargs)

    #--------------------------------------------------
    # MARC

    _marc_dict_cache = None

    def marc_as_dict(self):
        # cache a copy of the dict expansion, since it's semi-expensive to
        # generate, and is sometimes used more than once on the same page.
        if self._marc_dict_cache is None:
            if not self.marcxml:
                self._marc_dict_cache = {}
            else:
                self._marc_dict_cache = MX.record_to_dictionary(self.marcxml)
        return self._marc_dict_cache

    def marc_dc_subset(self):
        return json.dumps(self.marc_as_dict())

    #--------------------------------------------------
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
        return self.item_type in ('URL',)

    def copyright_status_ok(self):
        return not (self.item_type == u'ELEC' and self.copyright_status == u'UK')

    def item_download_url(self):
        if self.item_type != 'ELEC':
            return None
        else:
            req = get_request()
            script = req.META['SCRIPT_NAME']
            return req.build_absolute_uri(
                '%s/site/%d/item/%d/dl/%s' % (
                    script,
                    self.site_id, self.id,
                    self.fileobj.name.split('/')[-1]))

    def item_url(self, suffix='', force_local=False):
        if self.item_type == 'URL' and suffix == '' and not force_local:
            return self.url
        else:
            req = get_request()
            script = req.META['SCRIPT_NAME']
            return req.build_absolute_uri('%s/site/%d/item/%d/%s' % (
                    script,
                    self.site_id, self.id, suffix))

    def parent_url(self, suffix=''):
        if self.parent_heading:
            return self.parent_heading.item_url() + suffix
        else:
            return self.site.site_url()

    def needs_declaration_from(self, user):
        """Does this user need to make a declaration before downloading this
        item?"""
        if self.item_type == 'ELEC':
            return not bool(
                Declaration.objects.filter(
                    item=self, user=user))
        return False

    def describe_physical_item_status(self):
        """Return a (bool,str) tuple: whether the item is available,
        and a friendly description of the physical item's status"""
        stat = callhook('item_status', self)
        if not stat:
            return (False, 'Status information not available.')
        else:
            cpname, lib, desk, avail, callno, dueid, dueinfo, circmod, allcalls, alldues = stat
            return (avail > 0,
                    '%d of %d %s available at reserves desk; %d total copies in library system' % 
                    (avail, desk, cpname, lib))

    _video_type_re = re.compile(r'tag="007">v(.)')
    _video_types = {'c':'videocartridge',
                    'd':'videodisc',
                    'f':'videocassette',
                    'r':'videoreel',
                    'z':'video, other format'}

    def video_type(self):
        if not self.marcxml:
            return None
        m = self._video_type_re.search(self.marcxml)
        if m:
            vtype = m.group(1)
            return self._video_types.get(vtype, 'video, unknown format')

    def call_number(self):
        dct = self.marc_as_dict()
        if dct:
            try:
                if '092a' in dct:   # for ZPR's?. FIXME, is this legit?
                    return dct['092a']
                if '090a' in dct:   # for films. FIXME, is this legit?
                    return dct['090a']
                cn = ('%s %s' % (dct.get('050a', ''),
                                 dct.get('050b', ''))).strip()
                if len(cn) < 2:
                        cn = ('%s %s' % (dct.get('092a', ''),
                                 dct.get('092b', ''))).strip()
                return cn
            except:
                return None

    # TODO: stuff I'm not sure about yet. I don't think it belongs here.

    def title_hl(self, terms):
        hl_title = self.title
        for term in terms:
            hl_title = highlight(hl_title,term)

        return hl_title

    def author_hl(self, terms):
        hl_author = self.author

        for term in terms:
            hl_author = highlight(hl_author,term)

        return hl_author


    @classmethod
    def filter_for_user(cls, user):
        """
        Given a user object, return an appropriate Q filter that would
        filter only Items that the user has permission to view.
        """
        if user.is_anonymous():
            return Q(site__access='ANON')
        elif user.is_staff:
            return Q()
        else:
            return (Q(site__access__in=('RESTR','LOGIN','ANON')) \
                        | Q(site__group__membership__user=user))

#------------------------------------------------------------

class Declaration(BaseModel):
    """
    These are declarations of intent to use for personal research and study.
    We now require these before users can download electronic documents. Note,
    it only makes sense to add Declarations for items of type ELEC (uploaded
    electronic documents).
    """
    item = m.ForeignKey(Item)
    user = m.ForeignKey(User)

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

#----------------------------------------------------------------------
# Activate the local integration module. We loaded the module at the top of
# models.py, now we instantiate it.

    
if integration_class:
    initialize_hooks(integration_class())

#-----------------------------------------------------------------------------
# this can't be imported until Membership is defined...

import external_groups
