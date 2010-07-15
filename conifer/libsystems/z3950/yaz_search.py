# z39.50 search using yaz-client. 
# dependencies: yaz-client, pexpect

# I found that pyz3950.zoom seemed wonky when testing against conifer
# z3950, so I whipped up this expect-based version instead.

import warnings
import re
import pexpect
import sys
from ..marcxml import marcxml_to_dictionary

LOG = None              #  for pexpect debugging, try LOG = sys.stderr
YAZ_CLIENT = 'yaz-client'
GENERAL_TIMEOUT = 40
PRESENT_TIMEOUT = 60

def search(host, database, query, start=1, limit=10):

    # first, let's look at our query. I'm assuming @prefix queries for
    # now, so we need to put queries in that form if they aren't
    # yet. I'm also assuming query is a conjunction (terms are
    # AND'ed) if a '@' query isn't provided.
    if not query.startswith('@'):
        words = [w for w in query.split(' ') if w.strip()]
        tmp   = (['@and'] * (len(words) - 1)) + words
        query = ' '.join(tmp)
    query = query.encode('utf-8') # is this okay? Is it enough??

    server = pexpect.spawn('yaz-client', timeout=GENERAL_TIMEOUT, logfile=LOG)
    #server.expect('Z>')
    for line in ('charset UTF-8',
                 'open %s' % host, 
                 'base %s' % database, 
                 'format xml'):
        server.sendline(line)
        server.expect('Z>')

    # send the query
    # note, we're using prefix queries for the moment.
    server.sendline('find %s' % query)
    server.expect(r'Number of hits: (\d+).*')
    numhits = int(server.match.group(1)) 
    if start > numhits:
        warnings.warn('asked z3950 to start at %d, but only %d results.' % (start, numhits))
        return [], 0

    # how many to present? At most 10 for now.
    to_show = min(numhits-1, limit)
    if limit:
        to_show = min(to_show, limit)
    server.expect('Z>')
    server.sendline('show %s + %d' % (start, to_show))
    err = server.expect_list([re.compile(r'Records: (\d+)'), 
                              re.compile('Target closed connection')])
    if err:
        warnings.warn('error during z3950 conversation.')
        server.close()
        return [], 0

    raw_records = []
    err = None
    server.expect('.*Record type: XML')
    server.expect('nextResultSetPosition')
    pat = re.compile('<record .*?</record>', re.M)
    raw = server.before.replace('\n','')
    raw_records = pat.findall(raw)
    server.expect('Z>')
    server.sendline('quit')
    server.close()

    parsed = []
    for rec in raw_records:
        try:
            rec = _marc_utf8_pattern.sub(_decode_marc_utf8, rec)
            dct = marcxml_to_dictionary(rec)
        except 'x':
            raise rec
        parsed.append(dct)
    return parsed, numhits


# decoding MARC \X.. UTF-8 patterns.

_marc_utf8_pattern = re.compile(r'\\X([0-9A-F]{2})')

def _decode_marc_utf8(regex_match):
    return chr(int(regex_match.group(1), 16))


#------------------------------------------------------------
# some tests

if __name__ == '__main__':
    tests = [
        ('zed.concat.ca:210', 'OSUL', 'chanson'),
        ]
    for host, db, query in tests:
        print (host, db, query)
        print len(search(host, db, query, limit=33))
