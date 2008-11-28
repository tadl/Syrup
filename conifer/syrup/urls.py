from django.conf.urls.defaults import *

urlpatterns = patterns('conifer.syrup.views',
    (r'^$', 'welcome'),                       
    (r'^course/$', 'my_courses'),
    (r'^opencourse/$', 'open_courses'),
    (r'^join/$', 'join_course'),
    (r'^search/$', 'search'),
    (r'^instructors/$', 'instructors'),
    (r'^course/(?P<course_id>\d+)/$', 'course_detail'),
    (r'^course/(?P<course_id>\d+)/item/(?P<item_id>\d+)/$', 'item_detail'),
    (r'^course/(?P<course_id>\d+)/item/(?P<item_id>\d+)/meta$', 'item_metadata'),
)
