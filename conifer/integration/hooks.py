from conifer.integration._hooksystem import *
from datetime import date

#----------------------------------------------------------------------
# Your hooks go here.

# @hook
# def can_create_sites(user):
#     ...

#TODO: this is for testing purposes only! Remove.

@hook
def department_course_catalogue():
    """
    Return a list of rows representing all known, active courses and
    the departments to which they belong. Each row should be a tuple
    in the form: ('Department name', 'course-code', 'Course name').
    """
    return [
        ('Arts','01-01-209','Ethics in the Professions'),
        ('Social Work','02-47-204','Issues & Perspectives in Social Welfare'),
        ('Social Work','02-47-211','Prof Comm in Gen. Social Work Practice'),
        ('Social Work','02-47-336','Theory and Practice Social Work I'),
        ('Social Work','02-47-361','Field Practice I - A'),
        ('Social Work','02-47-362','Field Practice I - B'),
        ('Social Work','02-47-370','Mothering and Motherhood'),
        ('Social Work','02-47-456','Social Work and Health'),
        ]

@hook
def term_catalogue():
    """
    Return a list of rows representing all known terms. Each row
    should be a tuple in the form: ('term-code', 'term-name',
    'start-date', 'end-date'), where the dates are instances of the
    datetime.date class.
    """
    return [
        ('2011S', '2011 Summer', date(2011,5,1), date(2011,9,1)),
        ('2011F', '2011 Fall', date(2011,9,1), date(2011,12,31)),
        ]
