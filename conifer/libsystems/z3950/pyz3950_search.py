# z39.50 search using yaz-client. 
# dependencies: yaz-client, pexpect

# I found that pyz3950.zoom seemed wonky when testing against conifer
# z3950, so I whipped up this expect-based version instead.

import warnings
import re
import sys
from marcxml import marcxml_to_dictionary
from xml.etree import ElementTree as ET

try:

    import profile
    import lex
    import yacc
except ImportError:

    sys.modules['profile'] = sys # just get something called 'profile';
                                     # it's not actually used.
    import ply.lex
    import ply.yacc             # pyz3950 thinks these are toplevel modules.
    sys.modules['lex'] = ply.lex
    sys.modules['yacc'] = ply.yacc

# for Z39.50 support, not sure whether this is the way to go yet but
# as generic as it gets
from PyZ3950 import zoom, zmarc


LOG = None              #  for pexpect debugging, try LOG = sys.stderr
GENERAL_TIMEOUT = 40
PRESENT_TIMEOUT = 60

def search(host, port, database, query, start=1, limit=10):


    query = query.encode('utf-8') # is this okay? Is it enough??

    conn = zoom.Connection(host, port)
    conn.databaseName = database
    conn.preferredRecordSyntax = 'XML'
    
    query = zoom.Query ('CCL', str(query))
    res = conn.search (query)
    collector = []
    #if we were dealing with marc8 results, would probably need this
    #m = zmarc.MARC8_to_Unicode ()

    # how many to present? At most 10 for now.
    to_show = min(len(res)-(start - 1), limit)
    if limit:
        to_show = min(to_show, limit)


    #this seems to an efficient way of snagging the records
    #would be good to cache the result set for iterative display
    for r in range(start - 1,(start-1) + to_show):
        #would need to translate marc8 records, evergreen doesn't need this
        #collector.append(m.translate(r.data))
        collector.append(str(res.__getitem__(r)).replace('\n',''))
    conn.close ()


    raw = "" . join(collector)

    raw_records = []
    err = None

    pat = re.compile('<record .*?</record>', re.M)
    raw_records = pat.findall(raw)

    parsed = []
    for rec in raw_records:
        # TODO: fix this ascii/replace, once our z3950/marc encoding
        # issues are sorted out.
        rec = unicode(rec, 'ascii', 'replace')

        assert isinstance(rec, unicode) # this must be true.
        parsed.append(ET.fromstring(rec.encode('utf-8')))
    return parsed, len(res)


#------------------------------------------------------------
# some tests

if __name__ == '__main__':
    tests = [
        ('zed.concat.ca:210', 'OSUL', 'chanson'),
        ]
    for host, db, query in tests:
        print (host, db, query)
        print len(search(host, db, query, limit=33))
