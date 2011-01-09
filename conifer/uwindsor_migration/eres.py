#!/usr/bin/env python

# This script scrapes ERES and saves raw content to the 'data' directory.

from subprocess import *
import os
import re
import sys

import warnings
warnings.filterwarnings('ignore') # to avoid some twill import noise.

from twill.commands import *
from twill import get_browser

try:
    username = os.environ['ERESUSER']
    password = os.environ['ERESPASS']
except:
    print
    print 'Example usage:'
    print ' ERESUSER=xxxx ERESPASS=xxx %s <coursecode>' % sys.argv[0]
    print
    print 'Course codes are like CRIM48-567, as they appear in the ERES interface.'
    print
    print 'Fancier usage: '
    print ' export ERESUSER=xxx; export ERESPASS=xxx'
    print ' export CODES="coursecode1 coursecode2 coursecode3 ..."'
    print ' for code in $CODES; do %s $code; done' % sys.argv[0]
    raise SystemExit

browser = get_browser()

redirect_output('/dev/null')
go('http://ereserves.uwindsor.ca/eres/login.aspx')

fv(1, 3, username)
fv(1, 4, password)
submit(5)

go('http://ereserves.uwindsor.ca/eres/courses.aspx')

COURSE = sys.argv[1]

follow(COURSE)

PATH = 'data/%s' % COURSE

try:
    os.makedirs(PATH)
except:
    pass

submit(3)                       # 'accept' on the License page

follow('Documents')
BASE = url('.*').rsplit('/', 1)[0]

filename = '%s/items.html' % PATH
save_html(filename)
html = open(filename).read()

save_cookies('%s/c' % PATH)
log = open('%s/log' % PATH, 'w')

itemlinkpat = re.compile(r"documentview.aspx\?cid=(\d+)&associd=(\d+)")
done = set()

n = 0
for (cid, aid) in itemlinkpat.findall(html):
    if (cid, aid) in done:
        continue

    itemurl = "%s/documentview.aspx?cid=%s&associd=%s" % (BASE, cid, aid)
    print n, itemurl
    go(itemurl)

    filename = '%s/item%03d.html' % (PATH, n)
    save_html(filename)
    html = open(filename).read()

    linkpat = re.compile(r"""onClick="javascript:popall\('(.*)'.*?">Click here for more information</a>""")
    m = linkpat.search(html)
    if m:
        print >> log, (n, 'link', m.groups())
    else:
        filepat = re.compile(r"""onClick="javascript:pop\('(download.aspx\?docID=(\d+)&shortname=(.*?))'""")
        m = filepat.search(html)
        if m:
            print >> log, (n, 'file', m.groups())
            urlpath, itemid, origfile = m.groups()
            binary_url = '%s/%s' % (BASE, urlpath)
            cookie = browser.cj[0]
            destfile = '%s/data%03d' % (PATH, n)
            cmd = 'curl -s -b "%s=%s" "%s" > %s' % (cookie.name, cookie.value, binary_url, destfile)
            os.system(cmd)
    back()
    done.add((cid, aid))
    n += 1

log.close()
