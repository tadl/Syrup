from django.conf.urls.defaults import *

# I'm not ready to break items out into their own urls.py, but I do
# want to cut down on the common boilerplate in the urlpatterns below.

ITEM_PREFIX = r'^site/(?P<site_id>\d+)/item/(?P<item_id>\d+)/'
GENERIC_REGEX = r'((?P<obj_id>\d+)/)?(?P<action>.+)?$'

urlpatterns = patterns('conifer.syrup.views',
    (r'^$', 'welcome'),                       
    (r'^site/$', 'my_sites'),
    (r'^site/new/$', 'add_new_site'),
    (r'^site/invitation/$', 'site_invitation'),
    (r'^browse/$', 'browse'),
    (r'^browse/(?P<browse_option>.*)/$', 'browse'),
    (r'^prefs/$', 'user_prefs'),
    (r'^z3950test/$', 'z3950_test'),
    #MARK: propose we kill open_sites, we have browse.
    (r'^opensite/$', 'open_sites'),
    (r'^search/$', 'search'),
    (r'^zsearch/$', 'zsearch'),
    #MARK: propose we kill instructors, we have browse
    (r'^instructors/$', 'instructors'),
    (r'^instructors/search/(?P<instructor>.*)$', 'instructor_search'),
    #MARK: propose we kill departments, we have browse
    (r'^departments/$', 'departments'),
    (r'^site/(?P<site_id>\d+)/$', 'site_detail'),
    (r'^instructor/(?P<instructor_id>.*)/$', 'instructor_detail'),
    (r'^department/(?P<department_id>.*)/$', 'department_detail'),
    (r'^site/(?P<site_id>\d+)/search/$', 'site_search'),
    (r'^site/(?P<site_id>\d+)/edit/$', 'edit_site'),
    (r'^site/(?P<site_id>\d+)/edit/delete/$', 'delete_site'),
    (r'^site/(?P<site_id>\d+)/edit/permission/$', 'edit_site_permissions'),
    (r'^site/(?P<site_id>\d+)/edit/permission/delete_group/$', 'edit_site_permissions_delete_group'),
    (r'^site/(?P<site_id>\d+)/feeds/(?P<feed_type>.*)$', 'site_feeds'),
    (r'^site/(?P<site_id>\d+)/join/$', 'site_join'),
    (r'^site/.*fuzzy_user_lookup$', 'site_fuzzy_user_lookup'),
    (ITEM_PREFIX + r'$', 'item_detail'),
    (ITEM_PREFIX + r'dl/(?P<filename>.*)$', 'item_download'),
    (ITEM_PREFIX + r'meta$', 'item_metadata'),
    (ITEM_PREFIX + r'askfor$', 'item_declaration'),
    (ITEM_PREFIX + r'edit/$', 'item_edit'),
    (ITEM_PREFIX + r'delete/$', 'item_delete'),
    (ITEM_PREFIX + r'add/$', 'item_add'), # for adding sub-things
    (ITEM_PREFIX + r'add/cat_search/$', 'item_add_cat_search'),

    (r'^admin/$', 'admin_index'),
    (r'^admin/terms/' + GENERIC_REGEX, 'admin_terms'),
    (r'^admin/desks/' + GENERIC_REGEX, 'admin_desks'),
    (r'^admin/courses/' + GENERIC_REGEX, 'admin_courses'),
    (r'^admin/depts/' + GENERIC_REGEX, 'admin_depts'),
    (r'^admin/config/' + GENERIC_REGEX, 'admin_configs'),
    (r'^admin/targets/' + GENERIC_REGEX, 'admin_targets'),
    (r'^admin/update_depts_courses/$', 'admin_update_depts_courses'),
    (r'^admin/update_terms/$', 'admin_update_terms'),

    # (r'^phys/$', 'phys_index'),
    # (r'^phys/checkout/$', 'phys_checkout'),
    # (r'^phys/mark_arrived/$', 'phys_mark_arrived'),
    # (r'^phys/mark_arrived/match/$', 'phys_mark_arrived_match'),
    # (r'^phys/circlist/$', 'phys_circlist'),

    (r'^site/(?P<site_id>\d+)/reseq$', 'site_reseq'),
    (ITEM_PREFIX + r'reseq', 'item_heading_reseq'),
    (ITEM_PREFIX + r'relocate/', 'item_relocate'), # move to new subheading
#     (r'^admin/terms/(?P<term_id>\d+)/$', 'admin_term_edit'),
#     (r'^admin/terms/(?P<term_id>\d+)/delete$', 'admin_term_delete'),
#     (r'^admin/terms/$', 'admin_term'),
    (r'^unapi/$', 'unapi'),
)
