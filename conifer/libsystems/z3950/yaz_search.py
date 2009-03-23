# z39.50 search using yaz-client. 
# dependencies: yaz-client, pexpect

# I found that pyz3950.zoom seemed wonky when testing against conifer
# z3950, so I whipped up this expect-based version instead.

import warnings
import re
from xml.etree import ElementTree
import pexpect
import marctools
loc_to_unicode = marctools.locToUTF8().replace

LOG = None              #  for pexpect debugging, try LOG = sys.stderr
YAZ_CLIENT = 'yaz-client'
GENERAL_TIMEOUT = 3
PRESENT_TIMEOUT = 30


def search(host, database, query, start=1, limit=None):

    server = pexpect.spawn('yaz-client', timeout=GENERAL_TIMEOUT, logfile=LOG)
    for line in ('open %s' % host, 'base %s' % database, 'format xml'):
        server.sendline(line)
        server.expect('Z>')

    # send the query
    # note, we're using prefix queries for the moment.
    server.sendline('find %s' % query)
    server.expect(r'Number of hits: (\d+).*')
    numhits = int(server.match.group(1)) 
    if start > numhits:
        warnings.warn('asked z3950 to start at %d, but only %d results.' % (start, numhits))
        return []

    # how many to present? At most 10 for now.
    to_show = min(numhits-1, 10)    # minus 1 for dwarf ??
    if limit:
        to_show = min(to_show, limit)
    server.expect('Z>')
    server.sendline('show %s + %d' % (start, to_show))
    err = server.expect_list([re.compile(r'Records: (\d+)'), 
                              re.compile('Target closed connection')])
    if err:
        warnings.warn('error during z3950 conversation.')
        server.close()
        return []

    raw_records = []
    for x in range(to_show):
        server.expect(r'Record type: XML', timeout=PRESENT_TIMEOUT)
        server.expect('<record .*</record>')
        raw_records.append(server.match.group(0))

    server.expect('nextResultSetPosition')
    server.expect('Z>')
    server.sendline('quit')
    server.close()

    parsed = []
    for rec in raw_records:
        dct = {}
        parsed.append(dct)
        tree = ElementTree.fromstring(rec)
        for df in tree.findall('{http://www.loc.gov/MARC21/slim}datafield'):
            t = df.attrib['tag']
            for sf in df.findall('{http://www.loc.gov/MARC21/slim}subfield'):
                c = sf.attrib['code']
                v = sf.text
                dct[t+c] = loc_to_unicode(v)

    return parsed

#------------------------------------------------------------
# some tests

if __name__ == '__main__':
    print loc_to_unicode('A\\XCC\\X81n')
    tests = [
        ('dwarf.cs.uoguelph.ca:2210', 'conifer', '@and "Musson" "Evil"'),
        ('dwarf.cs.uoguelph.ca:2210', 'conifer', '@and "Denis" "Gravel"'),
        ('z3950.loc.gov:7090', 'VOYAGER', '@attr 1=4 @attr 4=1 "dylan"')]
    for host, db, query in tests:
        print (host, db, query)
        print search(host, db, query, limit=1)
