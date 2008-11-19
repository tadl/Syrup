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

class AnonymousUserExtensionHack(object):
    def unmoderated_courses():
        return Course.objects.filter(moderated=False)

for k,v in [(k,v) for k,v in AnonymousUserExtensionHack.__dict__.items() \
                if not k.startswith('_')]:
    setattr(AnonymousUser, k, v)

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
    name = m.TextField(db_index=True)
    active       = m.BooleanField(default=True)

    def __unicode__(self):
        return self.name

class Course(m.Model):
    """An offering of a course."""
    # some courses may be ad-hoc and have no code?
    code = m.CharField(max_length=64, blank=True, null=True)
    term = m.ForeignKey(Term)
    title = m.CharField(max_length=1024)
    # Enrol-codes are used for SIS integration.
    enrol_codes  = m.CharField('Registrar keys for class lists, pipe-separated',
                               max_length=4098, 
                               blank=True, null=True)
    active       = m.BooleanField(default=True)
    moderated    = m.BooleanField(default=False)

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

class NewsItem(m.Model):
    subject = m.CharField(max_length=200)
    body = m.TextField()
    published = m.DateTimeField(default=datetime.now, blank=True, null=True)
    encoding = m.CharField(max_length=10,
                           choices = (('plain', 'plain'),
                                      ('html', 'html'),
                                      ('markdown', 'markdown')),
                           default = 'html')
