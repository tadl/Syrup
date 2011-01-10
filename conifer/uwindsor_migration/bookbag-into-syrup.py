#!/usr/bin/env python

import re
from urllib2 import *
from pprint import pprint

linkpage = 'http://web4.uwindsor.ca/units/leddy/leddy.nsf/CourseReserves!OpenForm'

html = urlopen(linkpage).read()

urlpat = re.compile(r'<a href="(http://windsor.concat.ca/opac/extras/feed/bookbag/html-full/\d+)">')
titlepat = re.compile(r'<title>(.*?)</title>')

bad = set()
done = set()

for url in urlpat.findall(html):
    if url in done:
        continue
    try:
        html = urlopen(url).read()
    except:
        bad.add(url); done.add(url)
        continue

    title = titlepat.search(html).group(1)
    print title
    key = re.search(r'\d\d-\d\d\d', title).group(0)
    done.add(url)

    raise SystemExit
