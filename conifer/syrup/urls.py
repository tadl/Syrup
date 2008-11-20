from django.conf.urls.defaults import *

urlpatterns = patterns('conifer.syrup.views',
    (r'^$', 'welcome'),                       
    (r'^course/$', 'my_courses'),
    (r'^opencourse/$', 'open_courses'),
    (r'^course/(?P<course_id>\d+)/$', 'course_detail'),
)
