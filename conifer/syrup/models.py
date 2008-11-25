from django.db import models as m
from django.contrib.auth.models import User
from django.contrib.auth.models import AnonymousUser
from datetime import datetime

#----------------------------------------------------------------------
# USERS

# Note, we're using the User class from django_auth. User-fields not
# given in User are stored in the UserProfile, below. See:
# http://www.b-list.org/weblog/2006/jun/06/django-tips-extending-user-model/

# We will also monkey-patch the User object so that certain methods
# can be made available on the User that are not part of the Django
# User model. Let's try this for a bit see how this works out.

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
    active = m.BooleanField(default=True)

    def __unicode__(self):
        return 'UserProfile(%s)' % self.user

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

    def __unicode__(self):
        return '%s--%s--%s' % (self.user, self.role, self.course)


#------------------------------------------------------------

class Item(m.Model):
    """
    A reserve item, physical or electronic, as it appears in a given
    course instance.
    """
    
    # Structure

    # Items comprise both items-proper, as well as headings. In the
    # database, all items are stored as a flat list; the sort_order
    
    course = m.ForeignKey(Course)
    ITEM_TYPE_CHOICES = (('ITEM', 'Item'),
                         ('HEADING', 'Heading'))
    item_type = m.CharField(max_length=7, choices=ITEM_TYPE_CHOICES,
                            default='ITEM')
    sort_order = m.IntegerField(default=0)
    # parent must be a heading. could use ForeignKey.limit_choices_to,
    # to enforce this in the admin ui.
    parent_heading = m.ForeignKey('Item') 

    # Metadata
    title = m.CharField(max_length=255,db_index=True) 
    author = m.CharField(max_length=255,db_index=True) 
    source = m.CharField(max_length=255,db_index=True) 
    volume_title = m.CharField(max_length=255,db_index=True) 
    content_notes = m.CharField(max_length=255)
    volume_edition = m.CharField(max_length=255) 
    content_notes = m.CharField(max_length=255) 
    volume_edition = m.CharField(max_length=255) 
    pages_times = m.CharField(max_length=255) 
    performer = m.CharField(max_length=255,db_index=True) 
    local_control_key = m.CharField(max_length=30) 
    creation_date = m.DateField(auto_now=False)
    last_modified = m.DateField(auto_now=False)

    url = m.URLField()
    mime_type = m.CharField(max_length=100,default='text/html')

    isbn = m.CharField(max_length=13,db_index=True) 
    issn = m.CharField(max_length=8,db_index=True) 
    oclc = m.CharField(max_length=9,db_index=True) 

    home_library = m.ForeignKey(LibraryUnit)

    # shouldn't the icon be derived from the MIME type?
    ###item_icon = m.CharField(max_length=64, choices=ICON_CHOICES) 
    ##item_group = m.CharField(max_length=25,default='0')
    ##private_user_id = m.IntegerField(null=True,blank=True)
    ##old_id = m.IntegerField(null=True,blank=True)

    # Physical Item properties

    call_number = m.CharField(max_length=30) # long enough?
    barcode = m.CharField(max_length=30)     # long enough?
    
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
                              choices=STATUS_CHOICES, 
                              default=None) # null if not physical item.

    activation_date = m.DateField(auto_now=False)
    expiration_date = m.DateField(auto_now=False)
    
    # requested_loan_period: why is this a text field?
    requested_loan_period = m.CharField(max_length=255,blank=True,default='')

    fileobj = m.FileField(upload_to='uploads/%Y/%m/%d', max_length=255,
                          null=True, default=None)

    date_created = m.DateTimeField(auto_now_add=True)
    last_modified = m.DateTimeField()
    
    def __unicode__(self):
        return self.title


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
