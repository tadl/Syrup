data = eval(file('TEACHERS').read())

class person(object):
    def __init__(self, lst):
        d = dict(lst)
        for k,v in d.items():
            if len(v) == 1 and not k=='uwinCourseTeach':
                d[k] = v[0]
        self.__dict__.update(d)
        
people = dict()
for row in data:
    p = person(row)
    people[p.uid] = p

from collections import defaultdict
import re

teaches = defaultdict(set)

for p in people.values():
    for crs in p.uwinCourseTeach:
        if crs.endswith('2011W'):
            teaches[crs[2:7]].add(p)

def who_teaches(code):
    if '-' in code:
        code = code.replace('-', '')
    return teaches[code]

# if __name__ == '__main__':
#     for line in open('flatlist'):
#         line, rest = line.split('[')
#         line = line.strip()
#         code = line[:6].replace('-','')
#         line = line.replace('(','').replace(')','')
#         profs = [x.strip() for x in line[7:].split(',') if x.strip()]
#         thisterm = set([p.sn for p in who_teaches(code)])

#         if profs == ['Sections']:   # as in, "All Sections"
#             profs = thisterm        # so pick 'em all

#         if not set(profs).issubset(thisterm):
#             print 'XX', line, list(thisterm)
#         else:
#             pp = [x for x in who_teaches(code) if x.sn in profs]
#             sections = []
#             for prof in pp:
#                 for sec in prof.uwinCourseTeach:
#                     if re.match(r'..%s-\d+-2011W' % code, sec):
#                         sections.append((prof.uid, sec))
#             if sections:
#                 print 'OK', line
#                 print '^^', sections, len(sections)
#             else:
#                 print 'XX', line, list(thisterm)


if __name__ == '__main__':
    print who_teaches('32-427')
