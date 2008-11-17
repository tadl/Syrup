from django.http import HttpResponse, HttpRequest
from genshi.template import TemplateLoader
from genshi.filters import Translator
from genshi.builder import tag
import genshi.output
from django.conf import settings
from conifer.syrup import models # fixme, tight binding
import gettext
from conifer.middleware.genshi_locals import get_request

translations = gettext.GNUTranslations(file('locale/%s/LC_MESSAGES/conifer-syrup.mo' % settings.LANGUAGE_CODE))

_ = translations.ugettext

def template_loaded(template):
    template.filters.insert(0, Translator(translations.ugettext))

dirs = ['templates']

loader = TemplateLoader(dirs, auto_reload=True, callback=template_loaded)

def template(tname):
    return loader.load(tname)
           
def render(tname, **kwargs):
    request = get_request()
    _inject_django_things_into_namespace(request, kwargs)
    return HttpResponse(template(tname).generate(**kwargs).render('xhtml'))

def _inject_django_things_into_namespace(request, ns):
    ns['_'] = _
    ns['models'] = models
    ns['request'] = request
    ns['user'] = getattr(request, 'user', None)


