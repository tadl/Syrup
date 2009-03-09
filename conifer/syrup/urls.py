from django.conf.urls.defaults import *

# I'm not ready to break items out into their own urls.py, but I do
# want to cut down on the common boilerplate in the urlpatterns below.

ITEM_PREFIX = r'^course/(?P<course_id>\d+)/item/(?P<item_id>\d+)/'
GENERIC_REGEX = r'((?P<obj_id>\d+)/)?(?P<action>.+)?$'

urlpatterns = patterns('conifer.syrup.views',
    (r'^$', 'welcome'),                       
    (r'^course/$', 'my_courses'),
    (r'^course/new/$', 'add_new_course'),
    (r'^course/new/ajax_title$', 'add_new_course_ajax_title'),
    (r'^course/invitation/$', 'course_invitation'),
    (r'^browse/$', 'browse_courses'),
    (r'^browse/(?P<browse_option>.*)/$', 'browse_courses'),
    (r'^prefs/$', 'user_prefs'),
    (r'^z3950test/$', 'z3950_test'),
    (r'^opencourse/$', 'open_courses'),
    (r'^search/$', 'search'),
    (r'^instructors/$', 'instructors'),
    (r'^course/(?P<course_id>\d+)/$', 'course_detail'),
    (r'^instructor/(?P<instructor_id>.*)/$', 'instructor_detail'),
    (r'^department/(?P<department_id>.*)/$', 'department_detail'),
    (r'^course/(?P<course_id>\d+)/search/$', 'course_search'),
    (r'^course/(?P<course_id>\d+)/edit/$', 'edit_course'),
    (r'^course/(?P<course_id>\d+)/edit/delete/$', 'delete_course'),
    (r'^course/(?P<course_id>\d+)/edit/permission/$', 'edit_course_permissions'),
    (ITEM_PREFIX + r'$', 'item_detail'),
    (ITEM_PREFIX + r'dl/(?P<filename>.*)$', 'item_download'),
    (ITEM_PREFIX + r'meta$', 'item_metadata'),
    (ITEM_PREFIX + r'edit/$', 'item_edit'),
    (ITEM_PREFIX + r'add/$', 'item_add'), # for adding sub-things
    (r'^admin/$', 'admin_index'),
    (r'^admin/terms/' + GENERIC_REGEX, 'admin_terms'),
    (r'^admin/depts/' + GENERIC_REGEX, 'admin_depts'),
    (r'^admin/news/' + GENERIC_REGEX, 'admin_news'),

#     (r'^admin/terms/(?P<term_id>\d+)/$', 'admin_term_edit'),
#     (r'^admin/terms/(?P<term_id>\d+)/delete$', 'admin_term_delete'),
#     (r'^admin/terms/$', 'admin_term'),
)
