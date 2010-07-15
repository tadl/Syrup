from _common import *
from django.utils.translation import ugettext as _

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
