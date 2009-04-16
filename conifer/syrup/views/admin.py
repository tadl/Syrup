from _common import *
from django.utils.translation import ugettext as _

#-----------------------------------------------------------------------------
# Administrative options

@admin_only
def admin_index(request):
    return g.render('admin/index.xhtml')


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
        all   = models.Department.objects.order_by('abbreviation').all
        cols  = ['abbreviation', 'name']
        links = [0,1]

    clean_abbreviation = strip_and_nonblank('abbreviation')
    clean_name = strip_and_nonblank('name')

admin_depts = generic_handler(DeptForm, decorator=admin_only)

###
# graham - zap this if it messes anything up :-)
###
class TargetForm(ModelForm):
    class Meta:
        model = models.Target

    class Index:
        title = _('Targets')
        all   = models.Target.objects.order_by('name').all
        cols  = ['name', 'host']
        links = [0,1]

    clean_name = strip_and_nonblank('name')
    clean_host = strip_and_nonblank('host')

admin_targets = generic_handler(TargetForm, decorator=admin_only)
###


class NewsForm(ModelForm):
    class Meta:
        model = models.NewsItem

    class Index:
        title = _('News Items')
        all   = models.NewsItem.objects.order_by('-id').all
        cols  = ['id', 'subject', 'published']
        links = [0, 1]

    clean_subject = strip_and_nonblank('subject')
    clean_body = strip_and_nonblank('body')

admin_news = generic_handler(NewsForm, decorator=admin_only)



