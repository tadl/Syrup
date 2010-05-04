from default import *

#----------------------------------------------------------------------
# Course Codes

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


#----------------------------------------------------------------------
# Course Sections

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


