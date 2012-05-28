# use pyz3950 for z39.50 goodness

import warnings
import re
import sys
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

LOG = None              
GENERAL_TIMEOUT = 40
PRESENT_TIMEOUT = 60

def search(host, port, database, query, start=1, limit=10):

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
        # replace multiple 'unknown' characters with a single one.
        rec = re.sub(u'\ufffd+', u'\ufffd', rec)

        assert isinstance(rec, unicode) # this must be true.
        parsed.append(ET.fromstring(rec.encode('utf-8')))
    return parsed, len(res)


#------------------------------------------------------------
# some tests

if __name__ == '__main__':
    tests = [
        ('zed.concat.ca', 210, 'OSUL', 'chanson'),
        ]
    for host, port, db, query in tests:
        print (host, port, db, query)
        print len(search(host, port, db, query, limit=10))
