import os
from django.http import HttpResponse, HttpRequest
from genshi.template import TemplateLoader
from genshi.template import NewTextTemplate
from genshi.builder import tag
import genshi.output
from django.conf import settings
from warnings import warn

try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

#---------------------------------------------------------------------------
# Middleware

_THREAD_LOCALS = local()

class GenshiMiddleware(object):

    def process_request(self, request):
        _THREAD_LOCALS.request = request

def get_request():
    return getattr(_THREAD_LOCALS, 'request')


#---------------------------------------------------------------------------
# Templating support

class TemplateSet(object):

    def __init__(self, basedir, namespace_module=None):
        self.basedir = basedir
        if isinstance(basedir, list):
            self.dirs = basedir
        else:
            self.dirs = [self.basedir]
        self.loader = TemplateLoader(self.dirs,
                                     auto_reload=True,
                                     callback=self.template_loaded)
        if hasattr(namespace_module, '__dict__'):
            self.namespace_module = namespace_module.__dict__
        else:
            self.namespace_module = namespace_module


    def file(self, name):
        fn = os.path.join(self.basedir, name)
        assert os.path.dirname(fn) == self.basedir
        return file(fn)

    def template_loaded(self, template):
        pass

    def template(self, tname):
        return self.loader.load(tname)

    def text_template(self, tname):
        return self.loader.load(tname, cls=NewTextTemplate)

    #------------------------------------------------------------

    def _inject_django_things_into_namespace(self, request, ns):
        ns['request'] = request
        ns['user'] = getattr(request, 'user', None)
        ns['ROOT'] = request and request.META['SCRIPT_NAME']
        if not 'errors' in ns:
            ns['errors'] = None
        if self.namespace_module is not None:
            ns.update(self.namespace_module)

    def render(self, tname, **kwargs):
        request = get_request()
        self._inject_django_things_into_namespace(request, kwargs)
        return HttpResponse(self.template(tname).generate(**kwargs).render('xhtml'))

    def render_xml(self, tname, **kwargs):
        request = get_request()
        self._inject_django_things_into_namespace(request, kwargs)
        content_type = kwargs.get('content_type', 'application/xml')
        return HttpResponse(self.template(tname).generate(**kwargs).render('xml'),
                            content_type=content_type)

    def plaintext(self, tname, **kwargs):
        request = get_request()
        content_type = kwargs.get('content_type', 'text/plain')
        self._inject_django_things_into_namespace(request, kwargs)
        txt = self.text_template(tname).generate(**kwargs).render('text')
        return txt
