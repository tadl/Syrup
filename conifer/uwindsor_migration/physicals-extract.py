#!/usr/bin/env python-django

from syrup.models import *
import people
import re
from pprint import pprint
from integration.uwindsor import cat_search
from marc_import import marc_import

class bucket(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def __repr__(self):
        return repr(self.__dict__)

urllist = []

urlpat = re.compile(r'\d+. (\d+-\d+) (.*?) +==> (.*)')
for line in file('urllist'):
    course, title, url = urlpat.match(line).groups()
    urllist.append(bucket(course=course, title=title, url=url))

textlist = []
textpat_multi1 = re.compile(r'(\d+-\d+) (.*) \((.*)\) *$')
textpat_multi2 = re.compile(r'(\d+-\d+) (.*) (\w+/\w+) *$')
textpat_single1 = re.compile(r'(\d\d-\d\d\d),? (.*) +(\S+), \S\. *$')
textpat_single2 = re.compile(r'(\d\d-\d\d\d),? (.*) +(\S+) *$')

def ensure_user(username):
    user, created = User.objects.get_or_create(username=username)
    user.maybe_decorate()
    return user

termcode = '2011W'
term = Term.objects.get(code=termcode)

def get_site(coursecode, userids):
    profs = [ensure_user(p) for p in userids]
    primary = profs[0]
    course = Course.objects.get(code__contains=coursecode)
    site, created = Site.objects.get_or_create(
        owner = primary,
        start_term = term,
        course = course,
        defaults = dict(service_desk = ServiceDesk.default(),
                        end_term = term))
    return site

count = 0
for line in file('list-as-text'):
    line = line.strip()
    m = textpat_multi1.match(line)
    if m:
        code, title, profs = m.groups()
        profs = [x.strip() for x in profs.split(',') if x.strip()]
    else:
        m = textpat_multi2.match(line)
        if m:
            code, title, profs = m.groups()
            profs = profs.split('/')
        else:
            m = textpat_single1.match(line)
            if m:
                code, title, profs = m.groups()
                profs = [profs.strip()]
            else:
                m = textpat_single2.match(line)
                if m:
                    code, title, profs = m.groups()
                    profs = [profs.strip()]
                else:
                    continue    # screw it at this point.
    if title.endswith('All Sections'):
        title = title.replace(' All Sections', '')
    if title.endswith('All'):
        title = title.replace(' All', '')
    _tmp =  [u for u in urllist if u.course.strip() == code.strip() and u.title.strip() == title.strip()]
    _urls = [u.url for u in _tmp]
    if len(_urls) > 1:
        url = _urls[0]
        urllist.remove(_tmp[0])
    elif len(_urls) == 0:
        continue
    else:
        url = _urls[0]
    if profs == ['Sections']:
        persons = set([p for p in people.who_teaches(code)])
    else:
        persons = set([p for p in people.who_teaches(code)
                       if p.sn in profs])
    if not persons:
        #print ('SKIP', code, title, profs, url)
        continue
    else:
        # this one we can actually use!
        print ('OK', code, title, profs, url)
        sections = []
        for prof in persons:
            for sec in prof.uwinCourseTeach:
                if re.match(r'..%s-\d+-2011W' % code.replace('-',''), sec):
                    sections.append((prof.uid, sec))
        print sections
        site = get_site(code, [p.uid for p in persons])
        # set up the access control lists
        for uid, sec in sections:
            Group.objects.get_or_create(site=site, external_id=sec)
        # let's lookup the items.

        site.item_set.filter(item_type='PHYS').delete()

        items, n = cat_search(url)
        for item in items:
            marc_import(site, item, url)
        
        count+=1
        # if count > 5:
        #     break
