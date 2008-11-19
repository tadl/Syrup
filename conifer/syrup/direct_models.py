# fairly straight mapping of Reserves Direct tables
# a couple of additions as noted below

from django.db import models

class User(models.Model):
    username = models.CharField(max_length=200,db_index=True)
    first_name = models.CharField(max_length=255,db_index=True)
    last_name = models.CharField(max_length=255,db_index=True)
    email = models.EmailField()
    dflt_permission_level = models.IntegerField(default=0)
    last_login = models.DateTimeField(auto_now=False,null=True,blank=True)
    old_id = models.IntegerField(null=True,blank=True)
    old_user_id = models.IntegerField(null=True,blank=True)

    def __unicode__(self):
        return self.username

class LibraryUnit(models.Model):
    name = models.CharField(max_length=100)
    nickname = models.CharField(max_length=15,blank=True,default='')
    ils_prefix = models.CharField(max_length=10,blank=True,default='')
    reserve_desk = models.CharField(max_length=50,blank=True,default='')
    url = models.URLField()
    contact_email = models.EmailField()
    #not sure i understand this, guessing that this is a related library for material type
    copyright_library_id = models.IntegerField(null=True,blank=True)
    monograph_library_id = models.IntegerField(null=True,blank=True)
    multimedia_library_id = models.IntegerField(null=True,blank=True)

    def __unicode__(self):
        return self.name

class Item(models.Model):
    title = models.CharField(max_length=255,db_index=True) 
    author = models.CharField(max_length=255,db_index=True) 
    source = models.CharField(max_length=255,db_index=True) 
    volume_title = models.CharField(max_length=255,db_index=True) 
    content_notes = models.CharField(max_length=255)
    volume_edition = models.CharField(max_length=255) 
    content_notes = models.CharField(max_length=255) 
    volume_edition = models.CharField(max_length=255) 
    pages_times = models.CharField(max_length=255) 
    performer = models.CharField(max_length=255,db_index=True) 
    local_control_key = models.CharField(max_length=30) 
    creation_date = models.DateField(auto_now=False)
    last_modified = models.DateField(auto_now=False)
    url = models.URLField()
    mime_type = models.CharField(max_length=100,default='text/html')
    home_library = models.ForeignKey(LibraryUnit,related_name='home_library')
    private_user_id = models.IntegerField(null=True,blank=True)
    item_group = models.CharField(max_length=25,default='0')
    ITEM_TYPE_CHOICES = (
        ('ITEM', 'Item'),
        ('HEADING', 'Heading')
    )
    item_type = models.CharField(max_length=7, 
        choices=ITEM_TYPE_CHOICES,
        default='ITEM'
    )
    item_icon = models.CharField(max_length=255) 
    ISBN = models.CharField(max_length=13,db_index=True) 
    ISSN = models.CharField(max_length=8,db_index=True) 
    OCLC = models.CharField(max_length=9,db_index=True) 
    old_id = models.IntegerField(null=True,blank=True)

    def __unicode__(self):
        return self.title


class Department(models.Model):
    library = models.ForeignKey(LibraryUnit)
    abbreviatopn = models.CharField(max_length=8,db_index=True) 
    name = models.TextField(db_index=True)
    status = models.IntegerField(null=True,blank=True)

    def __unicode__(self):
        return self.name

class Course(models.Model):
    department = models.ForeignKey(Department)
    course_number = models.CharField(max_length=50,db_index=True) 
    course_name = models.TextField()
    uniform_title = models.TextField(db_index=True)
    old_id = models.IntegerField(null=True,blank=True,db_index=True)
    dept_abv = models.CharField(max_length=50,blank=True,default='')
    old_course_number = models.CharField(max_length=50,blank=True,default='')

    def __unicode__(self):
        return self.course_name

class CourseNoDept(models.Model):
    course_number = models.CharField(max_length=50) 
    course_name = models.TextField()
    uniform_title = models.BooleanField(default=True)
    old_id = models.IntegerField(null=True,blank=True,db_index=True)
    dept_abv = models.CharField(max_length=50,blank=True,default='')
    old_course_number = models.CharField(max_length=50,blank=True,default='')

    def __unicode__(self):
        return self.course_number

class CourseInstance(models.Model):
    primary_course_alias_id = models.IntegerField(null=True,blank=True)
    term = models.CharField(max_length=12,blank=True,default='')
    year = models.IntegerField(default=0)
    activation_date = models.DateTimeField(auto_now=False,db_index=True)
    expiration_date = models.DateTimeField(auto_now=False,db_index=True)
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'InActive'),
        ('INPROGRESS', 'In Progress'),
        ('AUTOFEED', 'AutoFeed'),
        ('CANCELLED', 'Cancelled')
    )
    status = models.CharField(max_length=10, 
        blank=True,
        choices=STATUS_CHOICES, 
        default=''
    )
    ENROLLMENT_CHOICES = (
        ('OPEN', 'Open'),
        ('MODERATED', 'Moderated'),
        ('CLOSED', 'Closed')
    )
    enrollment = models.CharField(max_length=9, 
        choices=ENROLLMENT_CHOICES, 
        default='OPEN'
    )
    reviewed_date = models.DateTimeField(auto_now=False)
    #what number does this refer to, maybe institutional?
    reviewed_by = models.IntegerField(null=True,blank=True)

class CourseAliasIdent(models.Model):
    course = models.ForeignKey(Course)
    course_name = models.CharField(max_length=200,db_index=True)
    course_instance_id = models.IntegerField(null=True,blank=True)
    course_name = models.TextField()
    section = models.CharField(max_length=25) 
    registrar_key = models.CharField(max_length=255) 

    def __unicode__(self):
        return self.course_name

class PermissionsLevel(models.Model):
    label = models.CharField(max_length=25)

    def __unicode__(self):
        return self.label

class AccessLevel(models.Model):
    user = models.ForeignKey(User)
    course_alias = models.ForeignKey(CourseAliasIdent)
    permissions_level = models.IntegerField(default=0, db_index=True)
    ENROLLMENT_STATUS_CHOICES = (
        ('AUTOFEED', 'AutoFeed'),
        ('APPROVED', 'Approved'),
        ('PENDING', 'Pending'),
        ('DENIED', 'Denied')
    )
    enrollment_status = models.CharField(max_length=8, 
        choices=ENROLLMENT_STATUS_CHOICES, 
        default='PENDING'
    )
    autofeed_run_indicator = models.CharField(max_length=20)

class CircRule(models.Model):
    circ_rule = models.CharField(max_length=50,blank=True,default='')
    alt_circ_rule = models.CharField(max_length=50,blank=True,default='')
    default_selected = models.BooleanField(default=False)

    def __unicode__(self):
        return self.circ_rule

class ElectronicItemAudit(models.Model):
    item_id = models.IntegerField(default=0)
    date_added = models.DateField(auto_now_add=True)
    date_reviewed = models.DateField(auto_now=False)
    added_by = models.IntegerField(null=True,blank=True)
    reviewed_by = models.IntegerField(null=True,blank=True)

class Reserve(models.Model):
    course_instance = models.ForeignKey(CourseInstance)
    item = models.ForeignKey(Item)
    activation_date = models.DateField(auto_now=False)
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'InActive'),
        ('INPROCESS', 'In Process')
    )
    status = models.CharField(max_length=9, 
        blank=True,
        choices=STATUS_CHOICES, 
        default=''
    )
    expiration = models.DateField(auto_now=False)
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField()
    requested_loan_period = models.CharField(max_length=255,blank=True,default='')
    parent_id = models.IntegerField(null=True,blank=True)

class HiddenReading(models.Model):
    user = models.ForeignKey(User)
    reserve = models.ForeignKey(Reserve)

class IlsRequest(models.Model):
    date_added = models.DateField(auto_now_add=True)
    #whoa, need to do homework on this
    ils_request_id = models.CharField(max_length=16,db_index=True) 
    ils_control_key = models.CharField(max_length=16,db_index=True) 
    user_net_id = models.CharField(max_length=16,db_index=True) 
    user_ils_id = models.CharField(max_length=16,db_index=True) 
    ils_course = models.CharField(max_length=150,db_index=True) 
    requested_loan_period = models.CharField(max_length=16) 

    def __unicode__(self):
        return self.ils_request_id

class InstLoadPeriod(models.Model):
    loan_period = models.CharField(max_length=255,blank=True,default='')

    def __unicode__(self):
        return self.loan_period

class InstLoadPeriodLibraryUnit(models.Model):
    library = models.ForeignKey(LibraryUnit)
    loan_period = models.ForeignKey(InstLoadPeriod)
    default= models.BooleanField(default=False)

class InstructorAttribute(models.Model):
    user = models.ForeignKey(User)
    ils_user_id = models.CharField(max_length=50) 
    ils_name = models.CharField(max_length=75) 
    organizational_status = models.CharField(max_length=25) 

class ItemUploadLog(models.Model):
    user = models.ForeignKey(User)
    course_instance = models.ForeignKey(CourseInstance)
    item = models.ForeignKey(Item)
    timestamp_uploaded = models.DateTimeField()
    filesize = models.CharField(max_length=10,blank=True,default='')
    ipaddr = models.IPAddressField()

class NewsItem(models.Model):
    news_text = models.TextField()
    font_class = models.CharField(max_length=50,blank=True,default='')
    PERMISSIONS_LEVEL_CHOICES = (
        ('0', '0 - '),
        ('1', '1 - '),
        ('2', '2 - '),
        ('3', '3 - '),
        ('4', '4 - '),
        ('5', '5 - ')
    )
    permissions_level = models.CharField(max_length=1, 
        choices=PERMISSIONS_LEVEL_CHOICES,
        blank=True,
        default=''
    )

    def __unicode__(self):
        return self.news_text

class NotTrained(models.Model):
    user = models.ForeignKey(User)
    permission_level = models.IntegerField(default=0)

class Note(models.Model):
    type = models.CharField(max_length=25,blank=True,default='')
    target_id = models.IntegerField(default=0)
    note = models.TextField() 
    target = models.CharField(max_length=50,blank=True,default='')

    def __unicode__(self):
        return self.note
    
class PhysicalCopyItem(models.Model):
    reserve = models.ForeignKey(Reserve)
    item = models.ForeignKey(Item)
    status = models.CharField(max_length=30,blank=True,default='')
    call_number = models.TextField() 
    owning_library = models.CharField(max_length=15,default='0')
    item_type = models.CharField(max_length=30) 
    owner_user_id = models.IntegerField(null=True,blank=True)

class ProxyIdent(models.Model):
    name = models.CharField(max_length=50,blank=True,default='')
    prefix = models.CharField(max_length=255,blank=True,default='')

    def __unicode__(self):
        return self.name

class ProxiedHost(models.Model):
    proxy = models.ForeignKey(ProxyIdent)
    domain = models.CharField(max_length=255,blank=True,default='')
    partial_match = models.BooleanField(default=False)

class Request(models.Model):
    reserve = models.ForeignKey(Reserve)
    item = models.ForeignKey(Item)
    user = models.ForeignKey(User)
    date_requested = models.DateField()
    date_processed = models.DateField(auto_now=False)
    date_desired = models.DateField(auto_now=False)
    priority = models.IntegerField(null=True,blank=True)
    course_instance = models.ForeignKey(CourseInstance)

class Report(models.Model):
    title = models.CharField(max_length=255)
    PARAM_GROUP_CHOICES = (
        ('TERM', 'Term'),
        ('DEPARTMENT', 'Department'),
        ('CLASS', 'Class'),
        ('TERM_LIB', 'Term Lib'),
        ('TERM_DATES', 'Term Dates')
    )
    param_group = models.CharField(max_length=10, 
        blank=True,
        choices=PARAM_GROUP_CHOICES, 
        default=''
    )
    sql = models.TextField() 
    parameters = models.CharField(max_length=255) 
    min_permissions = models.IntegerField(default=4)
    sort_order = models.IntegerField(default=0)
    cached = models.BooleanField(default=True)
    cached_refresh_delay = models.IntegerField(default=6)

    def __unicode__(self):
        return self.title

class ReportCache(models.Model):
    report = models.ForeignKey(Report)
    params_cache = models.TextField() 
    reports_cache = models.TextField() 
    last_modified = models.DateTimeField() 

class Skin(models.Model):
    skin_name = models.CharField(max_length=25,blank=True,default='')
    skin_stylesheet = models.TextField() 
    default_selected = models.BooleanField(default=False)

    def __unicode__(self):
        return self.skin_name

class SpecialUser(models.Model):
    user = models.ForeignKey(User)
    password = models.CharField(max_length=75,blank=True,default='')
    expiration = models.DateField(null=True,blank=True)

class SpecialUserAudit(models.Model):
    user = models.ForeignKey(User)
    creator = models.ForeignKey(User,related_name='creator')
    date_created = models.DateTimeField(auto_now_add=True)
    email_sent_to = models.CharField(max_length=255)

class StaffLibraryUnit(models.Model):
    user = models.ForeignKey(User)
    library = models.ForeignKey(LibraryUnit)
    permission_level = models.IntegerField(default=0)

class Term(models.Model):
    sort_order = models.IntegerField(default=0)
    term_name = models.CharField(max_length=100,default='')
    term_year = models.CharField(max_length=4,default='')
    begin_date = models.DateField(auto_now=False)
    end_date = models.DateField(auto_now=False)

    def __unicode__(self):
        return self.term_name

class UserViewLog(models.Model):
    user = models.ForeignKey(User)
    reserve = models.ForeignKey(Reserve)
    timestamp_viewed = models.DateTimeField()

class MimeType(models.Model):
    mime_type = models.CharField(max_length=100,default='')
    helper_app_url = models.TextField() 
    helper_app_name = models.TextField() 
    helper_app_icon = models.TextField() 
    file_extensions = models.CharField(max_length=255,blank=True,default='')

    def __unicode__(self):
        return self.mime_type

class HelpCategoryItem(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()

    def __unicode__(self):
        return self.title
    
class HelpArticle(models.Model):
    title = models.CharField(max_length=100)
    date_created = models.DateField(auto_now_add=True)
    body = models.TextField() 
    date_modified = models.DateField()

    def __unicode__(self):
        return self.title

class HelpArticleTag(models.Model):
    help_article = models.ForeignKey(HelpArticle)
    user = models.ForeignKey(User)
    tag = models.CharField(max_length=50)

class HelpCatToRole(models.Model):
    permission_level = models.IntegerField(default=0)
    can_view = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)

    def __unicode__(self):
        return self.permission_level

class HelpArticleToRole(models.Model):
    help_article = models.ForeignKey(HelpArticle)
    permission_level = models.IntegerField(default=0)
    can_view = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)

class HelpArticleToArticle(models.Model):
    help_article1 = models.ForeignKey(HelpArticle,related_name='help_article1')
    help_article2 = models.ForeignKey(HelpArticle,related_name='help_article2')
    RELATION_2TO1_CHOICES = (
        ('CHILD', 'Child'),
        ('SIBLING', 'Sibling')
    )
    relation_2to1 = models.CharField(max_length=7, 
        blank=True,
        choices=RELATION_2TO1_CHOICES,
        default=''
    )
