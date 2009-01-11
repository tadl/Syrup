# genshi_namespace

# Toplevel definitions in this module will be available in when
# rendering a Genshi template.

from itertools import cycle
from conifer.syrup import models

# Root-relative URLs Django has its own way of doing this, by doing
# reverse lookups in urlpatterns. Is there a benefit to their
# approach?

def item_url(item, suffix=''):
    return '/syrup/course/%d/item/%d/%s' % (item.course_id, item.id, suffix)

def course_url(course, suffix=''):
    return '/syrup/course/%d/%s' % (course.id, suffix)
