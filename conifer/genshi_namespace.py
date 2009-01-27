# genshi_namespace

# Toplevel definitions in this module will be available in when
# rendering a Genshi template.

from itertools import cycle
from conifer.syrup import models

# Root-relative URLs Django has its own way of doing this, by doing
# reverse lookups in urlpatterns. Is there a benefit to their
# approach?

def item_url(item, suffix=''):
    if item.item_type == 'ELEC' and suffix == '':
        return item_download_url(item)
    if item.item_type == 'URL' and suffix == '':
        return item.url
    else:
        return '/syrup/course/%d/item/%d/%s' % (item.course_id, item.id, suffix)

def item_download_url(item):
    assert item.item_type == 'ELEC'
    return '/syrup/course/%d/item/%d/dl/%s' % (
        item.course_id, item.id, item.fileobj.name.split('/')[-1])

def course_url(course, suffix=''):
    return '/syrup/course/%d/%s' % (course.id, suffix)

def instructor_url(instructor, suffix=''):
    return '/syrup/instructor/%d/%s' % (instructor.id, suffix)

def department_url(department, suffix=''):
    return '/syrup/department/%d/%s' % (department.id, suffix)
