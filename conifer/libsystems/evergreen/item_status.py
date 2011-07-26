import support
from support import ER, E1
from django.conf import settings
import re
import urllib2

def barcode_to_bib_id(barcode):
    bib_id = (E1('open-ils.search.bib_id.by_barcode', barcode))
    if isinstance(bib_id, basestring): # it would be a dict if barcode not found.
        return bib_id
    else:
        return None

def bib_id_to_marcxml(bib_id):
    return E1('open-ils.supercat.record.marcxml.retrieve', bib_id)

def url_to_marcxml(url):
    EVERGREEN_SERVER = getattr(settings, 'EVERGREEN_SERVER', '')

    # OPAC_URL: the base URL for the OPAC's Web interface.
    # default: http://your-eg-server/
    # local_settings variable: EVERGREEN_OPAC_URL

    if hasattr(settings, 'EVERGREEN_OPAC_URL'):
        OPAC_URL = settings.EVERGREEN_OPAC_URL
    else:
        assert EVERGREEN_SERVER
        OPAC_URL = 'http://%s/' % EVERGREEN_SERVER

    # this is a hack. Given a opac Title Details url, return marcxml.
    if url.startswith(OPAC_URL):
        if 'feed/bookbag' in url:
            #eg http://concat.ca/opac/extras/feed/bookbag/marcxml-full/60
            marc_url = re.sub(r'(.*/bookbag/)(.*?)(/.*)', r'\1marcxml-full\3', url)
            xml = unicode(urllib2.urlopen(marc_url).read(), 'utf-8')
        else:
            m = re.match(r'.*r=(\d+).*', url)
            item_id = m and m.group(1) or None
            if item_id:
                marc_url = ("%s/opac/extras/unapi?"
                            "id=tag:concat.ca,9999:biblio-record_entry/" # FIMXE, concat.ca reference!
                            "%s/-&format=marcxml-full" % (OPAC_URL, item_id))
            xml = unicode(urllib2.urlopen(marc_url).read(), 'utf-8')
        return xml

if __name__ == '__main__':
    support.initialize(settings)
