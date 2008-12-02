# genshi_namespace

# Toplevel definitions in this module will be available in when
# rendering a Genshi template.

from itertools import cycle

from conifer.syrup import models

def item_url(item, suffix=''):
    return '/syrup/course/%d/item/%d/%s' % (item.course_id, item.id, suffix)
