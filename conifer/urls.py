from django.conf.urls.defaults import *
from django.conf import settings
import django
import os

# I know it's not recommended, but this lets us mount django-admin's
# media through Django, through mod_python.

ADMIN_MEDIA_ROOT = os.path.join(os.path.dirname(django.__file__), 'contrib/admin/media/')

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^conifer/', include('conifer.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    (r'^syrup/djadmin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^syrup/djadmin/(.*)', admin.site.root),
    (r'^syrup/djmedia/(.*)', 'django.views.static.serve',
        {'document_root': ADMIN_MEDIA_ROOT}),
    (r'^syrup/static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}),
    (r'^syrup/accounts/(?P<path>.*)$', 'conifer.syrup.views.auth_handler'),

#    (r'^syrup/setlang', 'conifer.syrup.views.setlang'),
    (r'^syrup/i18n/', include('django.conf.urls.i18n')),
    (r'^syrup/', include('conifer.syrup.urls')),

)

if not settings.DEBUG:
    handler500 = 'conifer.syrup.views.custom_500_handler'
    handler404b = 'conifer.syrup.views.custom_400_handler'
