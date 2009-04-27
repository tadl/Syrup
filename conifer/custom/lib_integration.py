# Our integration-point with back-end library systems.

# This is a work in progress. I'm trying to separate out the actual
# protocol handlers (in libsystems) from the configuration decicions
# (in settings.py), and use this as sort of a merge-point between
# those two decisions. 

# TODO: write some documentation about the lib_integration interface.

# Our example configuration: 
# Z39.50 for catalogue search, 
# SIP for patron and item_info, and for item checkout and checkin,
# OpenSRF for extended item info.


# define a @caching decorator to exploit the Django cache. Fixme, move
# this somewhere else.
from django.core.cache import cache
import cPickle 
def caching(prefix, timeout=60):
    def g(func):
        def f(*args):
            # wtf! Django encodes string-values as
            # unicode-strings. That's bad, like stupid-bad! I'm
            # putting explicit utf8-conversions here to make debugging
            # easier if this code dies.
            key = ','.join([prefix] + map(str, args))
            v = cache.get(key)
            if v:
                return cPickle.loads(v.encode('utf-8'))
            else:
                v = func(*args)
                if v:
                    cache.set(key, unicode(cPickle.dumps(v), 'utf-8'), timeout)
                    return v
        return f
    return g


from django.conf import settings
#LIBINT = settings.LIBRARY_INTEGRATION # more on this later.


from conifer.libsystems.evergreen import item_status as I
from conifer.libsystems.sip.sipclient import SIP
from conifer.libsystems.z3950 import yaz_search
from conifer.libsystems.z3950.marcxml import marcxml_to_dictionary


@caching('patroninfo', timeout=300)
@SIP
def patron_info(conn, barcode):
    return conn.patron_info(barcode)

@caching('itemstatus', timeout=300)
@SIP
def item_status(conn, barcode):
    return conn.item_info(barcode)

@SIP
def checkout(conn, patron_barcode, item_barcode):
    return conn.checkout(patron_barcode, item_barcode, '')

@SIP
def checkin(conn, item_barcode):
    return conn.checkin(item_barcode, institution='', location='')


@caching('bcbi', timeout=3600)
def barcode_to_bib_id(barcode):
    return I.barcode_to_bib_id(barcode)

@caching('bccp', timeout=3600)
def barcode_to_copy(barcode):
    return I.barcode_to_copy(barcode)

@caching('bimx', timeout=3600)
def bib_id_to_marcxml(bib_id):
    return I.bib_id_to_marcxml(bib_id)


def cat_search(query, start=1, limit=10):
    # this is a total hack for conifer. If the query is a Conifer
    # title-detail URL, then return just that one item.
    if query.startswith('http://concat'):
        results = marcxml_to_dictionary(I.url_to_marcxml(query), multiples=True)
    else:
        cat_host, cat_db = ('concat.ca:2210', 'conifer')
        results = yaz_search.search(cat_host, cat_db, query, start, limit)
    return results
