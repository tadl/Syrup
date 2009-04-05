# z39.50 search using yaz-client. 
# dependencies: yaz-client, pexpect

# I found that pyz3950.zoom seemed wonky when testing against conifer
# z3950, so I whipped up this expect-based version instead.

import warnings
import re
import pexpect
import sys
from marcxml import marcxml_to_dictionary

LOG = sys.stderr #None              #  for pexpect debugging, try LOG = sys.stderr
YAZ_CLIENT = 'yaz-client'
GENERAL_TIMEOUT = 20
PRESENT_TIMEOUT = 30

def search(host, database, query, start=1, limit=None):

    server = pexpect.spawn('yaz-client', timeout=GENERAL_TIMEOUT, logfile=LOG)
    #server.expect('Z>')
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
    err = None
    server.expect('nextResultSetPosition')
    pat = re.compile('<record .*?</record>', re.M)
    raw_records = pat.findall(server.before)
    server.expect('Z>')
    server.sendline('quit')
    server.close()

    parsed = []
    for rec in raw_records:
        try:
            dct = marcxml_to_dictionary(rec)
        except:
            raise rec
        parsed.append(dct)
    return parsed


#------------------------------------------------------------
# some tests

if __name__ == '__main__':
    tests = [
        ('dwarf.cs.uoguelph.ca:2210', 'conifer', '@and "Musson" "Evil"'),
        ('dwarf.cs.uoguelph.ca:2210', 'conifer', '@and "Denis" "Gravel"'),
        ('z3950.loc.gov:7090', 'VOYAGER', '@attr 1=4 @attr 4=1 "dylan"')]
    for host, db, query in tests:
        print (host, db, query)
        print search(host, db, query, limit=1)
