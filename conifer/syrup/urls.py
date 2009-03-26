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
    (r'^browse/$', 'browse'),
    (r'^browse/(?P<browse_option>.*)/$', 'browse'),
    (r'^prefs/$', 'user_prefs'),
    (r'^z3950test/$', 'z3950_test'),
    (r'^graham_z3950test/$', 'graham_z3950_test'),
    #MARK: propose we kill open_courses, we have browse.
    (r'^opencourse/$', 'open_courses'),
    (r'^search/$', 'search'),
    (r'^zsearch/$', 'zsearch'),
    #MARK: propose we kill instructors, we have browse
    (r'^instructors/$', 'instructors'),
    #MARK: propose we kill departments, we have browse
    (r'^departments/$', 'departments'),
    (r'^course/(?P<course_id>\d+)/$', 'course_detail'),
    (r'^instructor/(?P<instructor_id>.*)/$', 'instructor_detail'),
    (r'^department/(?P<department_id>.*)/$', 'department_detail'),
    (r'^course/(?P<course_id>\d+)/search/$', 'course_search'),
    (r'^course/(?P<course_id>\d+)/edit/$', 'edit_course'),
    (r'^course/(?P<course_id>\d+)/edit/delete/$', 'delete_course'),
    (r'^course/(?P<course_id>\d+)/edit/permission/$', 'edit_course_permissions'),
    (r'^course/(?P<course_id>\d+)/feeds/(?P<feed_type>.*)$', 'course_feeds'),
    (ITEM_PREFIX + r'$', 'item_detail'),
    (ITEM_PREFIX + r'dl/(?P<filename>.*)$', 'item_download'),
    (ITEM_PREFIX + r'meta$', 'item_metadata'),
    (ITEM_PREFIX + r'edit/$', 'item_edit'),
    (ITEM_PREFIX + r'add/$', 'item_add'), # for adding sub-things
    (ITEM_PREFIX + r'add/cat_search/$', 'item_add_cat_search'),
    (r'^admin/$', 'admin_index'),
    (r'^admin/terms/' + GENERIC_REGEX, 'admin_terms'),
    (r'^admin/depts/' + GENERIC_REGEX, 'admin_depts'),
    (r'^admin/news/' + GENERIC_REGEX, 'admin_news'),
    (r'^admin/targets/' + GENERIC_REGEX, 'admin_targets'),
    (r'^course/(?P<course_id>\d+)/reseq$', 'course_reseq'),
    (ITEM_PREFIX + r'reseq', 'item_heading_reseq'),
    (ITEM_PREFIX + r'relocate/', 'item_relocate'), # move to new subheading
#     (r'^admin/terms/(?P<term_id>\d+)/$', 'admin_term_edit'),
#     (r'^admin/terms/(?P<term_id>\d+)/delete$', 'admin_term_delete'),
#     (r'^admin/terms/$', 'admin_term'),
)
