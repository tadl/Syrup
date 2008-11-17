from django.conf.urls.defaults import *

urlpatterns = patterns('conifer.syrup.views',
    (r'^$', 'index'),
    (r'^course/(?P<course_id>\d+)/$', 'course_index'),
)
