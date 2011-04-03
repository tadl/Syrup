from django.conf.urls.defaults import *
from django.conf import settings
import django
import os

# I know it's not recommended, but this lets us serve django-admin's
# media through Django.

ADMIN_MEDIA_ROOT = os.path.join(os.path.dirname(django.__file__), 'contrib/admin/media/')

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^conifer/', include('conifer.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    (r'^djadmin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^djadmin/(.*)', admin.site.root),
    (r'^djmedia/(.*)', 'django.views.static.serve',
        {'document_root': ADMIN_MEDIA_ROOT}),
    (r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}),
    (r'^accounts/(?P<path>.*)$', 'conifer.syrup.views.auth_handler'),

#    (r'^syrup/setlang', 'conifer.syrup.views.setlang'),
    (r'^i18n/', include('django.conf.urls.i18n')),
    (r'', include('conifer.syrup.urls')),

)

if not settings.DEBUG:
    handler500 = 'conifer.syrup.views.custom_500_handler'
    handler404b = 'conifer.syrup.views.custom_400_handler'


if settings.SAKAI_LINKTOOL_AUTHENTICATION:
    urlpatterns += patterns(
        'conifer.integration.sakai_linktool.app',
        (r'^linktool-welcome/$', 'linktool_welcome'),
        (r'^linktool-welcome/new_site$', 'linktool_new_site'),
        (r'^linktool-welcome/copy_old$', 'linktool_copy_old'),
        (r'^linktool-welcome/associate$', 'linktool_associate'),
        )

if settings.CAS_AUTHENTICATION:
    urlpatterns += patterns(
        'django_cas.views',
    (r'^%s$' % settings.LOGIN_URL[1:],  'login'),
    (r'^%s$' % settings.LOGOUT_URL[1:], 'logout'))
