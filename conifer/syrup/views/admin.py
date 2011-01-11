from _common  import *
from datetime import date

#-----------------------------------------------------------------------------
# Administrative options

@admin_only
def admin_index(request):
    return g.render('admin/index.xhtml')


class CourseForm(ModelForm):
    class Meta:
        model = models.Course

    class Index:
        title = _('Courses')
        all   = models.Course.objects.order_by('code', 'name').all
        cols  = ['code', 'name', 'department']
        links = [0, 1]

    clean_name = strip_and_nonblank('code')
    clean_name = strip_and_nonblank('name')

admin_courses = generic_handler(CourseForm, decorator=admin_only)


class ServiceDeskForm(ModelForm):
    class Meta:
        model = models.ServiceDesk

    class Index:
        title = _('ServiceDesks')
        all   = models.ServiceDesk.objects.order_by('name').all
        cols  = ['name']
        links = [0]

    clean_name = strip_and_nonblank('name')
    clean_code = strip_and_nonblank('external_id')

admin_desks = generic_handler(ServiceDeskForm, decorator=admin_only)

class TermForm(ModelForm):
    class Meta:
        model = models.Term

    class Index:
        title = _('Terms')
        all   = models.Term.objects.order_by('start', 'code').all
        cols  = ['code', 'name', 'start', 'finish']
        links = [0,1]

    clean_name = strip_and_nonblank('name')
    clean_code = strip_and_nonblank('code')

    def clean(self):
        cd = self.cleaned_data
        s, f = cd.get('start'), cd.get('finish')
        if (s and f) and s >= f:
            raise ValidationError, _('start must precede finish')
        return cd

admin_terms = generic_handler(TermForm, decorator=admin_only)


class DeptForm(ModelForm):
    class Meta:
        model = models.Department

    class Index:
        title = _('Departments')
        all   = models.Department.objects.order_by('name').all
        cols  = ['name', 'service_desk']
        links = [0]

    clean_abbreviation = strip_and_nonblank('abbreviation')
    clean_name = strip_and_nonblank('name')

admin_depts = generic_handler(DeptForm, decorator=admin_only)


class TargetForm(ModelForm):
    class Meta:
        model = models.Z3950Target

    class Index:
        title = _('Targets')
        all   = models.Z3950Target.objects.order_by('name').all
        cols  = ['name', 'host', 'database']
        links = [0]

    clean_name = strip_and_nonblank('name')
    clean_host = strip_and_nonblank('host')

admin_targets = generic_handler(TargetForm, decorator=admin_only)


class ConfigForm(ModelForm):
    class Meta:
        model = models.Config

    class Index:
        title = _('Configs')
        all   = models.Config.objects.order_by('name').all
        cols  = ['name', 'value']
        links = [0]

    clean_name = strip_and_nonblank('name')
    clean_host = strip_and_nonblank('value')

admin_configs = generic_handler(ConfigForm, decorator=admin_only)

def admin_update_depts_courses(request):
    HOOKNAME = 'department_course_catalogue'
    catalogue = callhook(HOOKNAME)

    # we can only assign them to the default service desk.
    defaultdesk = models.Config.get('default.desk', 1, int)
    desk = models.ServiceDesk.objects.get(pk=defaultdesk)

    if catalogue is None:
        return HttpResponse(
            'Sorry, cannot perform this operation at this time: '
            'hook %r not found.' % HOOKNAME)
    else:
        for deptname, ccode, cname in catalogue:
            if not (deptname.strip() and ccode.strip() and cname.strip()):
                continue
            dept, x = models.Department.objects.get_or_create(
                name=deptname, defaults={'service_desk': desk})
            models.Course.objects.get_or_create(
                code=ccode, defaults={'department': dept, 'name': cname})
        return simple_message('Courses and departments updated.', '')

def admin_update_terms(request):
    HOOKNAME = 'term_catalogue'
    catalogue = callhook(HOOKNAME)
    if catalogue is None:
        return HttpResponse(
            'Sorry, cannot perform this operation at this time: '
            'hook %r not found.' % HOOKNAME)
    else:
        for tcode, tname, start, finish in catalogue:
            tcode = tcode.strip(); tname = tname.strip()
            if not (tcode and tname and isinstance(start, date) \
                        and isinstance(finish, date)):
                raise Exception(('bad-row', tcode, tname, start, finish))
            models.Term.objects.get_or_create(
                code = tcode, 
                defaults = dict(name=tname, start=start, finish=finish))
        return simple_message('Terms updated.', '')

@admin_only
def admin_staff_add(request):
    if request.method != 'POST':
        return g.render('admin/staff_add.xhtml', **locals())
    else:
        userid = request.POST.get('userid','').strip()
        message_continue = True

        try:
            user = User.objects.get(username=userid)
        except User.DoesNotExist:
            user = User.objects.create(username=userid)
            user.maybe_decorate()

        user.is_staff = True
        user.is_superuser = True # TODO: are we sure they should be superuser?
        user.save()

        if not userid:
            message = 'No user selected.'
            message_continue = False
        else:
            message = 'Staff user added: %s [%s].' % (user.get_full_name(), user.username)

        return g.render('admin/staff_add.xhtml', **locals())

@admin_only
def admin_su(request):
    if request.method != 'POST':
        return g.render('admin/su.xhtml')
    else:
        userid = request.POST['userid'].lower().strip()
        user, created = User.objects.get_or_create(username=userid)
        user.maybe_decorate()
        if created and not user.last_name:
            user.delete()
            return g.render('admin/su.xhtml')
        elif user.is_active:
            request.session['_auth_user_id'] = user.id
        return HttpResponseRedirect('../../')

