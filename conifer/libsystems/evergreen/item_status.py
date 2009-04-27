from support import ER, E1
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
    # this is a hack. Given a opac Title Details url, return marcxml.
    if url.startswith('http://concat.ca'):
        if 'feed/bookbag' in url:
            #eg http://concat.ca/opac/extras/feed/bookbag/marcxml-full/60
            #http://concat.ca/opac/extras/feed/bookbag/html-full/60
            marc_url = re.sub(r'(.*/bookbag/)(.*?)(/.*)', r'\1marcxml-full\3', url)
            xml = urllib2.urlopen(marc_url).read()
        else:
            m = re.match(r'.*r=(\d+).*', url)
            item_id = m and m.group(1) or None
            if item_id:
                marc_url = ("http://concat.ca/opac/extras"
                            "/supercat/retrieve/marcxml/record/" + item_id)
            xml = urllib2.urlopen(marc_url).read()
        return xml

if __name__ == '__main__':
#     from pprint import pprint
#     print bib_id_to_marcxml(barcode_to_bib_id(31862016799294))
    print url_to_marcxml('http://concat.ca/opac/en-US/skin/default/xml/rdetail.xml?r=1082665&t=dylan%20thomas%20ralph&tp=keyword&d=0&hc=14&rt=keyword')
