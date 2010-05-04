# Operations on course-section identifiers

# A course section is an instance of a course offered in a term. 

# A section is specified by a 'section-id', a 3-tuple (course-code,
# term, section-code), where section-code is usually a short
# identifier (e.g., "1" representing "section 1 in this term"). Note
# that multiple sections of the same course are possible in a given
# term.

# Within the reserves system, a course-site can be associated with
# zero or more sections, granting access to students in those
# sections. We need two representations of a section-id.

# The section_tuple_delimiter must be a string which will never appear
# in a course-code, term, or section-code in your database. It may be
# a nonprintable character (e.g. NUL or CR). It is used to delimit
# parts of the tuples in a course's database record.

#------------------------------------------------------------
# Notes on the interface
#
# 'sections_taught_by(username)' returns a set of sections for which
# username is an instructor. It is acceptable if 'sections_taught_by'
# only returns current and future sections: historical information is
# not required by the reserves system.
#
# It is expected that the reserves system will be able to resolve any
# usernames into user records. If there are students on a section-list
# which do not resolve into user accounts, they will probably be
# ignored and will not get access to their course sites. So if you're
# updating your users and sections in a batch-run, you might want to
# update your users first.
#
#------------------------------------------------------------
# Implementations

# The reserves system will work with a null-implementation of the
# course-section interface, but tasks related to course-sections will
# be unavailable. 

# ------------------------------------------------------------ 
# The null implementation:
#
#    sections_tuple_delimiter   = None
#    sections_taught_by         = None
#    students_in                = None
#    instructors_in             = None
#    sections_for_code_and_term = None

# ------------------------------------------------------------ 
#
# The minimal non-null implementation. At the least you must provide
# sections_tuple_delimiter and students_in. Lookups for instructors
# may be skipped. Note that sections passed to students_in are
# (term, course-code, section-code) tuples (string, string, string).
#
#    sections_tuple_delimiter   = '|'
#
#    def students_in(*sections):
#        ...
#        return set_of_usernames
#
#    instructors_in             = None
#    sections_for_code_and_term = None

# ------------------------------------------------------------
# A complete implementation, with a static database.

#    sections_tuple_delimiter = '|'
#    
#    _db = [
#        ('fred', ('2009W', 'ENG203', '1'), 'jim joe jack ellen ed'),
#        ('fred', ('2009W', 'ENG327', '1'), 'ed paul bill'),
#        ('bill', ('2009S', 'BIO323', '1'), 'alan june jack'),
#        ('bill', ('2009S', 'BIO323', '2'), 'emmet'),
#    ]
#    
#    def sections_taught_by(username):
#        return set([s[1] for s in _db if s[0] == username])
#    
#    def students_in(*sections):
#        def inner():
#            for instr, sec, studs in _db:
#                if sec in sections:
#                    for s in studs.split(' '):
#                        yield s
#        return set(inner())
#    
#    def instructors_in(*sections):
#        def inner():
#            for instr, sec, studs in _db:
#                if sec in sections:
#                    yield instr
#        return set(inner())
#    
#    def sections_for_code_and_term(code, term):
#        return [(t, c, s) for (instr, (t, c, s), ss) in _db \
#                    if c == code and t == term]
#


# ------------------------------------------------------------
# Provide your own implementation below.

sections_tuple_delimiter   = None
sections_taught_by         = None
students_in                = None
instructors_in             = None
sections_for_code_and_term = None



# ------------------------------------------------------------
# a temporary implementation, while I write up the UI.

sections_tuple_delimiter = '|'

# For any of the students to actually appear in a course site, they
# must also exist as Django users (or be in an authentication backend
# that supports 'maybe_initialize_user'; see auth_evergreen.py).

_db = [
    #(instructor, (term, code, sec-code), 'student1 student2 ... studentN'),
    ('fred', ('2009W', 'ENG203', '1'), 'jim joe jack ellen ed'),
    ('fred', ('2009W', 'ENG327', '1'), 'ed paul bill'),
    ('art',  ('2009W', 'LIB201', '1'), 'graham bill ed'),
    ('graham', ('2009S', 'ART108', '1'), 'alan june jack'),
    ('graham', ('2009S', 'ART108', '2'), 'emmet'),
    ('graham', ('2009S', 'ART108', '3'), 'freda hugo bill'),
]

def sections_taught_by(username):
    return set([s[1] for s in _db if s[0] == username])

def students_in(*sections):
    def inner():
        for instr, sec, studs in _db:
            if sec in sections:
                for s in studs.split(' '):
                    yield s
    return set(inner())

def instructors_in(*sections):
    def inner():
        for instr, sec, studs in _db:
            if sec in sections:
                yield instr
    return set(inner())

def sections_for_code_and_term(code, term):
    return [(t, c, s) for (instr, (t, c, s), ss) in _db \
                if c == code and t == term]
