from django.conf.urls.defaults import *

# I'm not ready to break items out into their own urls.py, but I do
# want to cut down on the common boilerplate in the urlpatterns below.

ITEM_PREFIX = r'^course/(?P<course_id>\d+)/item/(?P<item_id>\d+)/'


urlpatterns = patterns('conifer.syrup.views',
    (r'^$', 'welcome'),                       
    (r'^course/$', 'my_courses'),
    (r'^browse/$', 'browse_courses'),
    (r'^browse/(?P<browse_option>.*)/$', 'browse_courses'),
    (r'^join/$', 'join_course'),
    (r'^opencourse/$', 'open_courses'),
    (r'^search/$', 'search'),
    (r'^instructors/$', 'instructors'),
    (r'^course/(?P<course_id>\d+)/$', 'course_detail'),
    (ITEM_PREFIX + r'$', 'item_detail'),
    (ITEM_PREFIX + r'dl/(?P<filename>.*)$', 'item_download'),
    (ITEM_PREFIX + r'meta/$', 'item_metadata'),
    (ITEM_PREFIX + r'edit/$', 'item_edit'),
    (ITEM_PREFIX + r'add/$', 'item_add'), # for adding sub-things
)
