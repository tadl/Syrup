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
def caching(prefix, timeout=60):
    def g(func):
        def f(*args):
            v = cache.get((prefix, args))
            if v:
                return v
            else:
                v = func(*args)
                if v:
                    cache.set((prefix, args), v, timeout)
                    return v
        return f
    return g


from django.conf import settings
#LIBINT = settings.LIBRARY_INTEGRATION # more on this later.


from conifer.libsystems.evergreen import item_status as I
from conifer.libsystems.sip.sipclient import SIP


@SIP
def patron_info(conn, barcode):
    return conn.patron_info(barcode)

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
