#!/usr/bin/env python-django

from conifer.syrup.models import *

from django.core.files import File
import shutil
import re
import hashlib
import os, sys
from os.path import *
from metadata import Metadata
from pprint import pprint
from django.conf import settings

upload_dir = Item._meta.get_field('fileobj').upload_to

known_profs = dict([
        ("Burgess","aburgess"),
        ("Fitzgerald","afitz"),
        ("Burr","burrc"),
        ("Jacobs","djacobs"),
        ("Gannage","gannage"),
        ("Huffaker","huffaker"),
        ("Carter","icarter"),
        ("Lewis","lewis3"),
        ("Parr","parr1"),
        ("McKay","pmckay"),
        ("Phipps","pphipps"),
        ("Samson","psamson"),
        ("Dienesch","rdienesc"),
        ("Orsini","sorsini"),
        ("Yun","yshhsy"),])

def ensure_user(username):
    user, created = User.objects.get_or_create(username=username)
    user.maybe_decorate()
    return user

def site_for_item(item):
    termcode, prof = item.term, item.instructor
    termcode = termcode.split(' ')[-1] + termcode[0] # Winter 2011 -> 2011W
    coursecode = re.search('\d\d-\d\d\d', item.course).group(0)
    profs = [ensure_user(known_profs[p.strip()])
             for p in prof.split(',')]
    primary = profs[0]
    course = Course.objects.get(code__contains=coursecode)
    term = Term.objects.get(code=termcode)
    site, created = Site.objects.get_or_create(
        owner = primary,
        start_term = term,
        course = course,
        defaults = dict(service_desk = ServiceDesk.default(),
                        end_term = term))
    return site
    
DATA = 'data/'
COURSES = os.listdir(DATA)


for course in COURSES:
    items = list(Metadata.find_all(join(DATA, course)))
    if not items:
        continue
    _item = items[0]

    site = site_for_item(_item)
    print site

    Item.objects.filter(site=site).delete() # fixme, just for testing.

    for m in items:
        d = m.data.copy()

        if 'author2' in d:
            d['author'] = '%s;%s' % (d['author'], d['author2'])

        for key in ['_path', 'author2', 'course', 'datafile', 'filename', 'instructor', 
                    'localid', 'term', 'type']:
            if key in d:
                del d[key]
        
        if m.type == 'url':
            assert 'url' in d, ('No URL', m.data)
            Item.objects.create(site=site, item_type='URL', **d)

        elif m.type == 'file':
            if m.mimetype is None:
                pprint(m.data)
                raise Exception('stop: a bad file?')

            with open(m.datafile) as f:
                digest = hashlib.md5(f.read()).hexdigest()
            dest = digest
            i = Item.objects.create(site=site, item_type='ELEC',
                                    fileobj_mimetype = m.mimetype,
                                    fileobj_origname = m.filename,
                                    copyright_status='AV',
                                    **d)

            fullpath = os.path.join(settings.MEDIA_ROOT, upload_dir, dest)
            if os.path.isfile(fullpath):
                i.fileobj.name = os.path.join(upload_dir, dest)
            else:
                with open(m.datafile) as f:
                    i.fileobj.save(dest, File(f), save=False)
            i.save()
