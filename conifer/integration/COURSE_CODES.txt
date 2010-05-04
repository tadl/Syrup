# Validation and lookup of course codes.

# This modules specifies an "course-code interface" and a null
# implementation of that interface. If your local system has rules for
# valid course codes, and a mechanism for looking up details of these
# codes, you can implement the interface according to your local
# rules.


# ------------------------------------------------------------
# Overview and definitions

# A course code identifies a specific course offering. Course codes
# map 1:N onto formal course titles: by looking up a code, we can
# derive a formal title (in theory, though it may not be possible for
# external reasons).

# A course code is insufficient to specify a class list: we need a
# course section for that. A section ties a course code and term to an
# instructor(s) and a list of students.

# Course codes may have cross-listings, i.e., other codes which refer
# to the same course, but which appear under a different department
# for various academic purposes. In our system, we make no attempt to
# subordinate cross-listings to a "primary" course code.


#------------------------------------------------------------
# Notes on the interface
#
# The `course_code_is_valid` function will be used ONLY if
# course_code_list() returns None (it is a null implementation). If a
# course-list is available, the system will use a membership test for
# course-code validity.
#
# `course_code_lookup_title` will be used ONLY if `course_code_list`
# is implemented.
#
#
# "types" of the interface members
#
# course_code_is_valid       (string) --> boolean.
# course_code_example        : a string constant.
# course_code_list           () --> list of strings
# course_code_lookup_title   (string) --> string, or None.
# course_code_cross_listings (string) --> list of strings
#
# For each member, you MUST provide either a valid implementation, or
# set the member to None. See the null implementation below.

#------------------------------------------------------------
# Implementations

# ------------------------------------------------------------ 
# Here is a 'null implementation' of the course-code interface. No
# validation is done, nor are lookups.
#
#    course_code_is_valid       = None  # anything is OK;
#    course_code_example        = None  # no examples;
#    course_code_lookup_title   = None  # no codes to list;
#    course_code_cross_listings = None  # no cross lists.

# ------------------------------------------------------------
# This one specifies a valid course-code format using a regular
# expression, and offers some example codes, but does not have a
# lookup system.
#
#    import re
#
#    def course_code_is_valid(course_code):
#        pattern = re.compile(r'^\d{2}-\d{3}$')
#        return bool(pattern.match(course_code))
#
#    course_code_example        = '55-203; 99-105'
#
#    course_code_list           = None
#    course_code_lookup_title   = None
#    course_code_cross_listings = None



# ------------------------------------------------------------
# This is a complete implementation, based on a hard-coded list of
# course codes and titles, and two cross-listed course codes.
#
#    _codes = [('ENG100', 'Introduction to English'),
#              ('ART108', 'English: An Introduction'),
#              ('FRE238', 'Modern French Literature'),
#              ('WEB203', 'Advanced Web Design'),]
#
#    _crosslists = set(['ENG100', 'ART108'])
#
#    course_code_is_valid = None
#    course_code_example = 'ENG100; FRE238'
#
#    def course_code_list():
#        return [a for (a,b) in _codes]
#
#    def course_code_lookup_title(course_code):
#        return dict(_codes).get(course_code)
#
#    def course_code_cross_listings(course_code):
#        if course_code in _crosslists:
#            return list(_crosslists - set([course_code]))


# ------------------------------------------------------------
# Provide your own implementation below.


#_codes = [('ENG100', 'Introduction to English'),
#          ('ART108', 'English: An Introduction'),
#          ('FRE238', 'Modern French Literature'),
#          ('LIB201', 'Intro to Library Science'),
#          ('WEB203', 'Advanced Web Design'),]

_codes = [('ART99-100', 'Art History'),
          ('BIOL55-350', 'Molecular Cell Biology'),
          ('CRIM48-567', 'Current Issues in Criminology'),
          ('ENGL26-280', 'Contemporary Literary Theory'),
          ('ENGL26-420', 'Word and Image: The Contemporary Graphic Novel'),
          ('SOCWK47-457', 'Advanced Social Work Research'),]

_crosslists = set(['ENGL26-280', 'ENGL26-420'])


course_code_is_valid = None

course_code_example = 'BIOL55-350; SOCWK47-457'

def course_code_list():
    return [a for (a,b) in _codes]

def course_code_lookup_title(course_code):
    return dict(_codes).get(course_code)

def course_code_cross_listings(course_code):
    if course_code in _crosslists:
        return list(_crosslists - set([course_code]))

