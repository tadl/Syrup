import genshi_namespace
from django.http import HttpResponse, HttpRequest
from genshi.template import TemplateLoader
from genshi.filters import Translator
from genshi.builder import tag
import genshi.output
from django.conf import settings
import gettext
from conifer.middleware.genshi_locals import get_request

#------------------------------------------------------------
# set up internationalization

# if settings.USE_I18N:
#     translations = gettext.GNUTranslations(
#         file('locale/%s/LC_MESSAGES/conifer-syrup.mo' % settings.LANGUAGE_CODE))
#     _ = translations.ugettext
# else:
#     _ = gettext.gettext

from django.utils import translation
_ = translation.ugettext

def template_loaded(template):
    if settings.USE_I18N:
        template.filters.insert(0, Translator(_))


dirs = ['templates']

loader = TemplateLoader(dirs, auto_reload=True, callback=template_loaded)

def template(tname):
    return loader.load(tname)
           

def _inject_django_things_into_namespace(request, ns):
    ns['_'] = _
    ns['request'] = request
    ns['user'] = getattr(request, 'user', None)
    ns.update(genshi_namespace.__dict__)

#------------------------------------------------------------
# main API

def render(tname, _django_type=HttpResponse, **kwargs):
    request = get_request()
    _inject_django_things_into_namespace(request, kwargs)
    return _django_type(template(tname).generate(**kwargs).render('xhtml'))

