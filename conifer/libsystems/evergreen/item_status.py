import warnings
from support import ER, E1
from pprint import pprint

# Proposing this as an interface method. Given a bib ID, return a dict
# giving the item's bibid, barcode, availability (boolean),
# holdability (boolean), and location (a string description). If the
# bib ID is invalid, return None.

def lookup_availability(bib_id):
    rec = E1('open-ils.search.asset.copy.fleshed2.retrieve', bib_id)
    if 'stacktrace' in rec:
        warnings.warn(repr(('no such bib id', bib_id, repr(rec))))
        return None
    resp = {
        'bibid':     bib_id,
        'barcode':   rec['barcode'],
        'available': rec['status']['name'] == 'Available',
        'holdable':  rec['status']['holdable'] == 't',
        'location':  rec['location']['name']}
    return resp


if __name__ == '__main__':
    DYLAN = 1321798
    print lookup_availability(DYLAN)
