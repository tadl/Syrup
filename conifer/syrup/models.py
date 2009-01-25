from django.db import models as m
from django.contrib.auth.models import User
from django.contrib.auth.models import AnonymousUser
from datetime import datetime
import re

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

for k,v in [(k,v) for k,v in UserExtensionHack.__dict__.items() \
                if not k.startswith('_')]:
    setattr(User, k, v)


class UserProfile(m.Model):
    user         = m.ForeignKey(User, unique=True)
    home_phone   = m.CharField(max_length=100, blank=True)
    home_address = m.TextField(blank=True)
    ils_userid   = m.TextField("Alternate userid in the ILS, if any",
                               max_length=50, blank=True)
    access_level = m.CharField(max_length=5, blank=True, null=True,
                               default=None,
                               choices=(('CUST', 'custodian'),
                                        ('STAFF', 'staff'),
                                        ('ADMIN', 'system administrator')))
    instructor = m.BooleanField(default=False)
    proxy = m.BooleanField(default=False)
    # n.b. Django's User has an active flag, maybe we should use that?
    active = m.BooleanField(default=True) 

    def __unicode__(self):
        return 'UserProfile(%s)' % self.user

    @classmethod
    def active_instructors(cls):
        """Return a queryset of all active instructors."""
        return cls.objects.filter(instructor=True) \
            .select_related('user').filter(user__is_active=True) \
            .order_by('-user__last_name','-user__first_name')

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
    code   = m.CharField(max_length=16, blank=True, null=True)
    name   = m.CharField(max_length=255)
    start  = m.DateField()
    finish = m.DateField()

    def __unicode__(self):
        return self.code or self.name

class Department(m.Model):
    abbreviation = m.CharField(max_length=8,db_index=True)
    name   = m.CharField(max_length=255)
    active       = m.BooleanField(default=True)

    def __unicode__(self):
        return self.name

class Course(m.Model):
    """An offering of a course."""
    # some courses may be ad-hoc and have no code?
    code = m.CharField(max_length=64, blank=True, null=True)
    department = m.ForeignKey(Department)
    term = m.ForeignKey(Term)
    title = m.CharField(max_length=1024)
    active       = m.BooleanField(default=True)
    moderated    = m.BooleanField('This is a moderated (non-public) course',
                                  default=False)

    # Enrol-codes are used for SIS integration (graham's idea-in-progress)
    enrol_codes  = m.CharField('Registrar keys for class lists, pipe-separated',
                               max_length=4098, 
                               blank=True, null=True)
    def __unicode__(self):
        return self.code or self.title

    def items(self):
        return self.item_set.all()

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

class Member(m.Model):
    course = m.ForeignKey(Course)
    user = m.ForeignKey(User)
    role = m.CharField(
        choices = (
                ('INSTR', 'Instructor'),
                ('PROXY', 'Proxy Instructor'),
                ('STUDT', 'Student')),
        default = 'STUDT',
        max_length = 5)

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
        ('ELEC', 'Attached Electronic Document'), # PDF, Doc, etc.
        ('PHYS', 'Physical Book or Document'),
        ('URL',  'URL'),
        ('HEADING', 'Heading'))
    item_type = m.CharField(max_length=7, choices=ITEM_TYPE_CHOICES)
    sort_order = m.IntegerField(default=0)
    # parent must be a heading. could use ForeignKey.limit_choices_to,
    # to enforce this in the admin ui.
    parent_heading = m.ForeignKey('Item', blank=True, null=True)

    # Metadata.

    # TODO: Are all these relevant to all item types? If not, which
    # ones should be 'required' for which item-types? We cannot
    # enforce these requirements through model constraints, unless we
    # break Item up into multiple tables. But there are other ways we
    # can specify the constraints.
    title = m.CharField(max_length=255,db_index=True) 
    author = m.CharField(max_length=255,db_index=True) 
    source = m.CharField(max_length=255,db_index=True, blank=True, null=True) 
    volume_title = m.CharField(max_length=255,db_index=True, blank=True, null=True) 
    content_notes = m.CharField(max_length=255, blank=True, null=True)
    volume_edition = m.CharField(max_length=255, blank=True, null=True) 
    content_notes = m.CharField(max_length=255, blank=True, null=True) 
    volume_edition = m.CharField(max_length=255, blank=True, null=True) 
    pages_times = m.CharField(max_length=255, blank=True, null=True) 
    performer = m.CharField(max_length=255,db_index=True, blank=True, null=True) 
    year = m.CharField(max_length=10,db_index=True, blank=True, null=True) 

    local_control_key = m.CharField(max_length=30, blank=True, null=True) 

    url = m.URLField(blank=True, null=True)
    mime_type = m.CharField(max_length=100,default='text/html')

    isbn = m.CharField(max_length=13,db_index=True, blank=True, null=True) 
    issn = m.CharField(max_length=8,db_index=True, blank=True, null=True) 
    oclc = m.CharField(max_length=9,db_index=True, blank=True, null=True) 

    home_library = m.ForeignKey(LibraryUnit, blank=True, null=True)

    # shouldn't the icon be derived from the MIME type?
    ###item_icon = m.CharField(max_length=64, choices=ICON_CHOICES) 
    ##item_group = m.CharField(max_length=25,default='0')
    ##private_user_id = m.IntegerField(null=True,blank=True)
    ##old_id = m.IntegerField(null=True,blank=True)

    # Physical Item properties

    call_number = m.CharField(max_length=30, blank=True, null=True) # long enough?
    barcode = m.CharField(max_length=30, blank=True, null=True)     # long enough?
    
#     # owning_library:is this supposed to be a code? 
#     owning_library = m.CharField(max_length=15,default='0')
#     item_type = m.CharField(max_length=30)
#     # who is the owner?
#     owner_user_id = m.IntegerField(null=True,blank=True)

    STATUS_CHOICE = (('INPROCESS', 'In Process'), # physical, pending
                     ('ACTIVE', 'Active'),        # available
                     ('INACTIVE', 'InActive'))    # no longer on rsrv.
    phys_status = m.CharField(max_length=9, 
                              null=True,
                              choices=STATUS_CHOICE, 
                              default=None) # null if not physical item.

    activation_date = m.DateField(auto_now=False)
    expiration_date = m.DateField(auto_now=False, blank=True, null=True)
    
    # requested_loan_period: why is this a text field?
    requested_loan_period = m.CharField(max_length=255,blank=True,default='', null=True)

    # for items of type ELEC (attached electronic document)
    fileobj = m.FileField(upload_to='uploads/%Y/%m/%d', max_length=255,
                          blank=True, null=True, default=None)

    fileobj_mimetype = m.CharField(max_length=128, blank=True, null=True, default=None)


    date_created = m.DateTimeField(auto_now_add=True)
    last_modified = m.DateTimeField()

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

    def needs_meta_link(self):
        """Should an 'About' link be displayed for this item?"""

        return self.item_type == 'URL'

#------------------------------------------------------------

class NewsItem(m.Model):
    subject = m.CharField(max_length=200)
    body = m.TextField()
    published = m.DateTimeField(default=datetime.now, blank=True, null=True)
    encoding = m.CharField(max_length=10,
                           choices = (('plain', 'plain'),
                                      ('html', 'html'),
                                      ('markdown', 'markdown')),
                           default = 'html')
